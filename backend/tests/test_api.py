import io
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal
from app.models import Fact, EvidenceRelation, Case,Document,DocumentBlock,Statement
from app.schemas import Extraction, AtomicFact, Verification
from app.services.pipeline import analyze_case
from app.services.source_locator import locate

@pytest.fixture
def client():
    with TestClient(app) as c: yield c

def pdf_bytes(text):
    with fitz.open() as pdf:
        pdf.new_page().insert_text((40,40),'Synthetic fixture - not a real case')
        pdf.new_page().insert_text((40,40),text)
        return pdf.tobytes()

class DeterministicLLM:
    """Only for pipeline integrity tests, never shipped as an AI fallback."""
    model='test-double'
    def structured(self,prompt,schema):
        if schema is Verification: return Verification(relation_type='CONTRADICTS',explanation='同一进入事件，肯定与否定。',confidence=.9)
        text=prompt.split('当前块（仅此可引用）：\n')[-1]
        if 'Zhang entered Hotel' not in text and 'Zhang did not enter Hotel' not in text: return Extraction(persons=[],facts=[])
        return Extraction(persons=[],facts=[AtomicFact(subject='张某',predicate='进入',object_text='',object_person='',recipient='',
            location='Hotel',time_text='2026年3月17日21时',amount_text='',polarity='denied' if 'did not' in text else 'affirmed',
            source_person='张某',source_type='self_report',quote=text.strip(),confidence=.9)])

def test_full_chain_review_and_run_preservation(client):
    case=client.post('/api/cases',json={'name':'端到端案件'}).json(); cid=case['id']
    result=client.post(f'/api/cases/{cid}/documents',files=[('files',('a.pdf',pdf_bytes('Zhang entered Hotel.'),'application/pdf')),('files',('b.pdf',pdf_bytes('Zhang did not enter Hotel.'),'application/pdf'))])
    assert result.status_code==201 and len(result.json()['documents'])==2
    analyze_case(cid,DeterministicLLM())
    c=client.get('/api/cases/'+cid).json(); assert c['analysis_status']=='COMPLETED'
    relations=client.get(f'/api/cases/{cid}/relations').json(); assert len(relations)==1
    r=relations[0]; assert r['relation_type']=='CONTRADICTS'
    for f in (r['fact_a'],r['fact_b']):
        assert f['page_number']==2 and f['quote'] and f['document_id']
        assert client.get('/api/documents/'+f['document_id']+'/file').content.startswith(b'%PDF')
        blocks=client.get('/api/documents/'+f['document_id']+'/blocks').json()
        assert any(b['page_number']==2 and f['quote'] in b['text'] for b in blocks)
    for status in ['CONFIRMED','DISMISSED','UNCERTAIN']:
        saved=client.post('/api/relations/'+r['id']+'/review',json={'review_status':status,'note':'核对第2页'}).json()
        assert saved['review_status']==status
    people=client.get(f'/api/cases/{cid}/persons').json()
    assert client.patch(f'/api/cases/{cid}/target-person',json={'person_id':people[0]['id']}).status_code==200
    class Broken:
        model='test-error'
        def structured(self,*args): raise ValueError('Malformed JSON')
    analyze_case(cid,Broken())
    after=client.get('/api/cases/'+cid).json()
    assert after['analysis_status']=='FAILED' and after['active_run_id']==c['active_run_id']
    again=client.get(f'/api/cases/{cid}/relations').json()
    assert again[0]['review']['review_status']=='UNCERTAIN'
    with SessionLocal() as db:
        f=db.get(Fact,r['fact_a']['id']); f.quote='forged quotation'
        with pytest.raises(ValueError): locate(db,f)
        db.rollback()

def test_upload_errors_and_cross_case(client):
    cid=client.post('/api/cases',json={'name':'上传验证'}).json()['id']
    r=client.post(f'/api/cases/{cid}/documents',files=[('files',('../bad.pdf',b'not-pdf','application/pdf'))]).json()
    assert not r['documents'] and r['errors']
    assert client.post(f'/api/cases/{cid}/analyze').status_code==422
    other=client.post('/api/cases',json={'name':'隔离案件'}).json()['id']
    p=client.post(f'/api/cases/{other}/persons',json={'canonical_name':'李某'}).json()
    assert client.patch(f'/api/cases/{cid}/target-person',json={'person_id':p['id']}).status_code==422
    assert client.get('/api/cases/missing/facts').status_code==404
    assert client.post('/api/cases',json={'name':'   '}).status_code==422

def test_alias_conflicts_and_origin(client):
    cid=client.post('/api/cases',json={'name':'别名核验'}).json()['id']
    p=client.post(f'/api/cases/{cid}/persons',json={'canonical_name':'张伟','aliases':['小张']}).json()
    assert client.post(f'/api/cases/{cid}/persons',json={'canonical_name':'小张'}).status_code==409
    assert client.patch('/api/persons/'+p['id'],json={'canonical_name':'张伟','aliases':['张总']}).status_code==200
    assert client.post('/api/cases',json={'name':'x'},headers={'Origin':'https://example.com'}).status_code==403
    assert client.get('/api/cases',headers={'Host':'evil.example'}).status_code==400

def test_busy_case_mutation_blocked(client):
    cid=client.post('/api/cases',json={'name':'忙碌锁定'}).json()['id']
    with SessionLocal() as db:
        c=db.get(Case,cid); c.analysis_status='EXTRACTING'; db.commit()
    assert client.post(f'/api/cases/{cid}/persons',json={'canonical_name':'张某'}).status_code==409

def test_manual_entity_merge(client):
    cid=client.post('/api/cases',json={'name':'人工人物合并'}).json()['id']
    a=client.post(f'/api/cases/{cid}/persons',json={'canonical_name':'张伟','role':'defendant'}).json()
    b=client.post(f'/api/cases/{cid}/persons',json={'canonical_name':'张某'}).json()
    client.patch(f'/api/cases/{cid}/target-person',json={'person_id':b['id']})
    assert client.post('/api/persons/'+b['id']+'/merge',json={'target_person_id':a['id'],'confirmed_same_person':False}).status_code==422
    result=client.post('/api/persons/'+b['id']+'/merge',json={'target_person_id':a['id'],'confirmed_same_person':True})
    assert result.status_code==200 and '张某' in result.json()['person']['aliases']
    assert client.get('/api/cases/'+cid).json()['target_person_id']==a['id']
    assert len(client.get(f'/api/cases/{cid}/persons').json())==1

def test_multiblock_source_is_exact_and_has_union_bbox(client):
    cid=client.post('/api/cases',json={'name':'跨块引文'}).json()['id']
    with SessionLocal() as db:
        doc=Document(case_id=cid,filename='test.pdf',original_path='unused',total_pages=2);db.add(doc);db.flush()
        a=DocumentBlock(document_id=doc.id,page_number=2,block_index=0,text='张某交付了红色',bbox=[40,40,200,56])
        b=DocumentBlock(document_id=doc.id,page_number=2,block_index=1,text='手提袋。',bbox=[40,65,100,81])
        db.add_all([a,b]);db.flush()
        s=Statement(document_id=doc.id,page_number=2,raw_text=a.text+'\n'+b.text,block_ids=[a.id,b.id],run_id='test');db.add(s);db.flush()
        f=Fact(case_id=cid,statement_id=s.id,run_id='test',predicate='交付',polarity='affirmed',document_id=doc.id,page_number=2,quote=a.text+'\n'+b.text,confidence=.9)
        db.add(f);db.flush()
        located=locate(db,f)
        assert located['bbox']==[40,40,200,81] and located['block_ids']==[a.id,b.id]
        b.page_number=1;db.flush()
        with pytest.raises(ValueError): locate(db,f)
        db.rollback()
