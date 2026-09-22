from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import Case, Document, Person
from ..services.pipeline import BUSY

def row(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}

def get_case(db,case_id,mutable=False):
    case=db.get(Case,case_id)
    if not case: raise HTTPException(404,'案件不存在')
    if mutable and case.analysis_status in BUSY: raise HTTPException(409,'分析进行中，请完成后再修改材料或人物')
    return case

def case_view(db,case):
    return {**row(case),'document_count':db.scalar(select(func.count()).select_from(Document).where(Document.case_id==case.id))}

def check_person(db,case_id,person_id):
    person=db.get(Person,person_id)
    if not person or person.case_id!=case_id: raise HTTPException(422,'人物不属于当前案件')
    return person

def mark_changed(case):
    case.analysis_status='PENDING'
    case.progress='材料或人物信息已变更，请重新分析。显示的上一轮结果及复核记录仍保留。'
