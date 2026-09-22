from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select,update
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Case, Person, Document, Statement, Fact, EvidenceRelation
from ..schemas import CaseInput, TargetInput, PersonInput, MergeInput
from .common import row,get_case,case_view,check_person,mark_changed

router=APIRouter()

@router.post('/cases',status_code=201)
def create_case(data:CaseInput, db:Session=Depends(get_db)):
    if not data.name.strip(): raise HTTPException(422,'案件名称不能为空')
    c=Case(name=data.name.strip(),description=data.description); db.add(c); db.commit()
    return case_view(db,c)

@router.get('/cases')
def cases(db:Session=Depends(get_db)):
    return [case_view(db,c) for c in db.scalars(select(Case).order_by(Case.created_at.desc()))]

@router.get('/cases/{case_id}')
def case(case_id:str, db:Session=Depends(get_db)):
    return case_view(db,get_case(db,case_id))

@router.get('/cases/{case_id}/persons')
def persons(case_id:str,db:Session=Depends(get_db)):
    get_case(db,case_id)
    return [row(p) for p in db.scalars(select(Person).where(Person.case_id==case_id).order_by(Person.canonical_name))]

@router.patch('/cases/{case_id}/target-person')
def target(case_id:str,data:TargetInput,db:Session=Depends(get_db)):
    c=get_case(db,case_id); check_person(db,case_id,data.person_id)
    c.target_person_id=data.person_id; db.commit(); return case_view(db,c)

def validate_aliases(db,case_id,data,exclude=None):
    names=[data.canonical_name.strip()]+[a.strip() for a in data.aliases]
    if any(not n for n in names) or len(names)!=len(set(names)): raise HTTPException(422,'姓名/别名不得为空或重复')
    for p in db.scalars(select(Person).where(Person.case_id==case_id)):
        if p.id!=exclude and set(names)&{p.canonical_name,*p.aliases}:
            raise HTTPException(409,'该姓名或别名属于另一个人物。为避免误合并，请先核验并修改另一人物的名称。')

@router.post('/cases/{case_id}/persons',status_code=201)
def add_person(case_id:str,data:PersonInput,db:Session=Depends(get_db)):
    get_case(db,case_id,True); validate_aliases(db,case_id,data)
    p=Person(case_id=case_id,**data.model_dump()); db.add(p); db.commit(); return row(p)

@router.patch('/persons/{person_id}')
def edit_person(person_id:str,data:PersonInput,db:Session=Depends(get_db)):
    p=db.get(Person,person_id)
    if not p: raise HTTPException(404,'人物不存在')
    get_case(db,p.case_id,True); validate_aliases(db,p.case_id,data,p.id)
    for key,value in data.model_dump().items(): setattr(p,key,value)
    p.pending_aliases=[]; mark_changed(get_case(db,p.case_id)); db.commit(); return row(p)

@router.post('/persons/{person_id}/merge')
def merge_person(person_id:str,data:MergeInput,db:Session=Depends(get_db)):
    source=db.get(Person,person_id)
    if not source: raise HTTPException(404,'人物不存在')
    case=get_case(db,source.case_id,True)
    target=check_person(db,source.case_id,data.target_person_id)
    if source.id==target.id: raise HTTPException(422,'请选择另一个人物')
    target.aliases=sorted(set(target.aliases+source.aliases+[source.canonical_name])-{target.canonical_name})
    target.pending_aliases=[]
    for model,columns in ((Document,['source_person_id']),(Statement,['source_person_id']),
                          (Fact,['source_person_id','subject_person_id','object_person_id','recipient_person_id'])):
        for column in columns:
            db.execute(update(model).where(getattr(model,column)==source.id).values({column:target.id}))
    for relation in db.scalars(select(EvidenceRelation).where(EvidenceRelation.case_id==case.id)):
        if relation.issue_key.startswith(source.id+':'): relation.issue_key=target.id+relation.issue_key[len(source.id):]
    if case.target_person_id==source.id: case.target_person_id=target.id
    db.delete(source); mark_changed(case); db.commit()
    return {'person':row(target),'message':'已人工确认合并；已有引用和复核保留。请重新分析以发现新增候选关系。'}
