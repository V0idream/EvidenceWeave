import json
from types import SimpleNamespace as NS
import pymupdf as fitz
import pytest
from pydantic import ValidationError
from app.services.document_parser import parse_pdf,quality,OCRUnavailable
from app.services.fact_extractor import extract
from app.services.fact_normalizer import amount,normalize_time
from app.services.candidate_matcher import candidate_pairs
from app.services.consistency_verifier import verify
from app.schemas import Extraction,AtomicFact,Verification
from app.llm.ollama import Ollama

class NoOCR:
    def parse(self,path): raise OCRUnavailable('OCR unavailable')

def pdf(path,pages):
    with fitz.open() as doc:
        for text in pages:
            page=doc.new_page()
            if text: page.insert_text((50,50),text)
        doc.save(path)

def test_parser_text_and_page_numbers(tmp_path):
    p=tmp_path/'multi.pdf'; pdf(p,['First page has a reliable text layer.','Second page has its own original text.'])
    r=parse_pdf(p,NoOCR())
    assert [x['page_number'] for x in r['pages']]==[1,2]
    assert r['pages'][1]['blocks'][0]['text'].startswith('Second')
    assert r['pages'][0]['blocks'][0]['bbox'] and not r['warnings']

def test_parser_empty_file(tmp_path):
    p=tmp_path/'empty.pdf'; p.write_bytes(b'')
    with pytest.raises(ValueError): parse_pdf(p)

def test_no_text_layer_and_blank(tmp_path):
    p=tmp_path/'scan.pdf'; pdf(p,[''])
    r=parse_pdf(p,NoOCR())
    assert r['warnings'] and r['empty_page_ratio']==1
    assert r['pages'][0]['page_number']==1

def test_ocr_fallback_only_low_quality(tmp_path):
    p=tmp_path/'mixed.pdf'; pdf(p,['This page already has sufficient valid text.',''])
    class OCR:
        def parse(self,path): return {2:[{'text':'Local OCR recovered text.','bbox':None,'parser':'MinerU'}]}
    r=parse_pdf(p,OCR())
    assert r['pages'][0]['blocks'][0]['parser']=='PyMuPDF'
    assert r['pages'][1]['blocks'][0]['parser']=='MinerU'
    assert not quality('\ufffd'*40)['reliable']

def af(**changes):
    return {'subject':'张某','predicate':'进入','object_text':'','object_person':'','recipient':'',
        'location':'宾馆','time_text':'2026年3月17日21时','amount_text':'','polarity':'denied',
        'source_person':'张某','source_type':'self_report','quote':'张某没有进入宾馆。','confidence':.9,**changes}

def test_extraction_valid_multiple_negative_and_missing_fields():
    value=Extraction.model_validate({'persons':[],'facts':[af(),af(polarity='affirmed')]})
    assert len(value.facts)==2 and value.facts[0].polarity=='denied'
    with pytest.raises(ValidationError): Extraction.model_validate({'facts':[{'quote':'x'}]})
    with pytest.raises(ValidationError): Extraction.model_validate_json('broken')

def test_fabricated_citation_rejected():
    class Mock:
        def structured(self,*args): return Extraction(persons=[],facts=[AtomicFact(**af())])
    with pytest.raises(ValueError,match='引用'): extract(Mock(),'张某走过宾馆。')
    assert len(extract(Mock(),'张某没有进入宾馆。').facts)==1

def test_wrapped_quote_restores_exact_source():
    from app.services.fact_extractor import original_quote
    assert original_quote('张某没有进入\n宾馆。','张某没有进入宾馆。')=='张某没有进入\n宾馆。'
    with pytest.raises(ValueError): original_quote('张某没有进入宾馆。','张某进入宾馆。')

@pytest.mark.parametrize('raw,expected',[('十万元',100000),('100000元',100000),('10万',100000),('十万块',100000),('两千元',2000),('1.5万元',15000),('不详',None)])
def test_amounts(raw,expected): assert amount(raw)==expected

def test_time_no_guesses():
    assert normalize_time('第二天凌晨')==(None,None,'low')
    assert normalize_time('当晚九点左右')==(None,None,'low')
    assert normalize_time('2026年3月17日晚九点左右')[0]=='2026-03-17T20:30:00'

def fact(**changes):
    return NS(subject_person_id='zhang',predicate='进入',statement_id='s1',normalized_time_start='2026-03-17T21:00:00',
        normalized_time_end='2026-03-17T21:00:00',location='宾馆',object_text='',recipient_person_id=None,**changes)

def test_candidates():
    a=fact(); b=fact(); b.statement_id='s2'
    c=fact(); c.subject_person_id='li'
    d=fact(); d.normalized_time_start='2026-04-01T21:00:00'; d.normalized_time_end=d.normalized_time_start
    assert list(candidate_pairs([a,b,c,d]))==[(a,b)]

def test_objective_candidates_use_wider_time_window():
    a=fact(source_type='objective')
    b=fact(source_type='objective'); b.statement_id='s2'
    b.normalized_time_start='2026-03-17T10:00:00'; b.normalized_time_end=b.normalized_time_start
    assert list(candidate_pairs([a,b]))==[(a,b)]
    b.normalized_time_start='2026-03-16T06:00:00'; b.normalized_time_end=b.normalized_time_start
    assert not list(candidate_pairs([a,b]))

def test_continuation_units_keep_ids_and_page():
    from app.services.text_units import units
    a=NS(id='a',page_number=2,text='张某交付了红色',bbox=[40,40,300,56])
    b=NS(id='b',page_number=2,text='手提袋。',bbox=[40,65,100,81])
    c=NS(id='c',page_number=3,text='另一页。',bbox=[40,85,200,100])
    assert units([a,b,c])==[[a,b],[c]]
    b.bbox=[350,65,400,81]
    assert units([a,b,c])==[[a],[b],[c]]

def test_money_and_bag_are_not_candidates():
    a=fact();a.predicate='交付';a.object_text='黑色手提袋'
    b=fact();b.predicate='收款';b.amount=100000;b.statement_id='s2'
    assert not list(candidate_pairs([a,b]))

@pytest.mark.parametrize('relation',['SUPPORTS','CONTRADICTS','PARTIAL_DIFFERENCE','INDEPENDENT'])
def test_verifier_schema(relation):
    class Mock:
        def structured(self,prompt,schema):
            assert '不得' not in relation and 'Fact A' in prompt
            return schema(relation_type=relation,explanation='需要人工核验。',confidence=.8)
    a=NS(**{k:v for k,v in af().items()},amount=None)
    assert verify(Mock(),a,a).relation_type==relation

def test_objective_difference_is_promoted_to_potential_conflict():
    class Mock:
        def structured(self,prompt,schema):
            return schema(relation_type='PARTIAL_DIFFERENCE',explanation='监控为21:00，打车记录为21:35。',confidence=.78)
    a=NS(**{k:v for k,v in af(source_type='objective').items()},amount=None)
    b=NS(**{k:v for k,v in af(source_type='self_report').items()},amount=None)
    result=verify(Mock(),a,b)
    assert result.relation_type=='CONTRADICTS'
    assert '客观记录' in result.explanation

def test_statement_only_minor_difference_remains_partial():
    class Mock:
        def structured(self,prompt,schema):
            return schema(relation_type='PARTIAL_DIFFERENCE',explanation='约九点与约九点半。',confidence=.7)
    a=NS(**{k:v for k,v in af(source_type='self_report').items()},amount=None)
    result=verify(Mock(),a,a)
    assert result.relation_type=='PARTIAL_DIFFERENCE'

def test_json_repair_once(monkeypatch):
    import app.llm.ollama as module
    replies=['{broken',json.dumps({'persons':[],'facts':[af()]},ensure_ascii=False)]
    calls=[]
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'message':{'content':replies.pop(0)}}
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,json): calls.append(json); return Response()
    monkeypatch.setattr(module.httpx,'Client',Client)
    assert Ollama().structured('test',Extraction).facts
    assert len(calls)==2
    replies.extend(['bad','bad']); calls.clear()
    with pytest.raises(ValueError): Ollama().structured('test',Extraction)
    assert len(calls)==2

def test_local_only_config_and_fallback(monkeypatch):
    from app.config import Settings
    with pytest.raises(ValueError): Settings(ollama_base_url='https://example.com')
    llm=Ollama(); monkeypatch.setattr(llm,'available',lambda:['qwen3:8b'])
    assert llm.select()=='qwen3:8b'
    monkeypatch.setattr(llm,'available',lambda:[])
    with pytest.raises(RuntimeError,match='Ollama'): llm.select()

def test_uncertainty_and_explicit_action_guards():
    from app.services.fact_normalizer import grounded_corrections
    f=AtomicFact(**af(predicate='到场',quote='2025年12月4日，钱某没有在办公室参与方案商议。'))
    corrections=grounded_corrections(f,'interrogation')
    assert f.predicate=='商议' and f.polarity=='denied' and corrections['predicate']['model']=='到场'
    f=AtomicFact(**af(quote='证人说不知道赵某是否进入库房。',source_type='objective'))
    grounded_corrections(f,'witness_statement')
    assert f.polarity=='uncertain' and f.source_type=='unknown'
    f=AtomicFact(**af(quote='赵某没有进入库房。'))
    grounded_corrections(f,'interrogation')
    assert f.polarity=='denied'
