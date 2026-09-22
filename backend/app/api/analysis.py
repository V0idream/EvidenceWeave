from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Case, Fact, EvidenceRelation, Review, DocumentBlock, Document
from ..services.pipeline import analyze_case,BUSY
from ..services.source_locator import locate
from .common import row,get_case

router=APIRouter()

@router.post('/cases/{case_id}/analyze',status_code=202)
def analyze(case_id:str,background:BackgroundTasks,db:Session=Depends(get_db)):
    get_case(db,case_id,True)
    block=db.scalar(select(DocumentBlock.id).join(Document).where(Document.case_id==case_id).limit(1))
    if not block: raise HTTPException(422,'没有可分析文本，请先上传 PDF 并检查 OCR 提示')
    result=db.execute(update(Case).where(Case.id==case_id,Case.analysis_status.not_in(BUSY)).values(
        analysis_status='PARSING',analysis_phase='PARSING',analysis_error='',progress='检查本地模型与带页码文本'))
    if result.rowcount!=1: raise HTTPException(409,'案件已在分析中')
    db.commit(); background.add_task(analyze_case,case_id)
    return {'status':'PARSING','case_id':case_id}

def focused(f,c):
    t=c.target_person_id
    return not t or t in (f.subject_person_id,f.object_person_id,f.recipient_person_id,f.source_person_id)

@router.get('/cases/{case_id}/facts')
def facts(case_id:str,all_persons:bool=False,db:Session=Depends(get_db)):
    c=get_case(db,case_id)
    return [{**row(f),'source':locate(db,f)} for f in db.scalars(select(Fact).where(Fact.case_id==case_id,Fact.run_id==c.active_run_id)) if all_persons or focused(f,c)]

@router.get('/cases/{case_id}/relations')
def relations(case_id:str,all_persons:bool=False,db:Session=Depends(get_db)):
    c=get_case(db,case_id); result=[]
    for r in db.scalars(select(EvidenceRelation).where(EvidenceRelation.case_id==case_id,EvidenceRelation.run_id==c.active_run_id)):
        a,b=db.get(Fact,r.fact_a_id),db.get(Fact,r.fact_b_id)
        if not all_persons and not (focused(a,c) or focused(b,c)): continue
        review=db.scalar(select(Review).where(Review.evidence_relation_id==r.id))
        result.append({**row(r),'fact_a':{**row(a),'source':locate(db,a)},'fact_b':{**row(b),'source':locate(db,b)},'review':row(review) if review else None})
    return result
