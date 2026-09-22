from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import EvidenceRelation, Review
from ..schemas import ReviewInput
from .common import row

router=APIRouter()

@router.post('/relations/{relation_id}/review')
def review(relation_id:str,data:ReviewInput,db:Session=Depends(get_db)):
    if not db.get(EvidenceRelation,relation_id): raise HTTPException(404,'关系不存在')
    r=db.scalar(select(Review).where(Review.evidence_relation_id==relation_id))
    if not r: r=Review(evidence_relation_id=relation_id); db.add(r)
    r.review_status=data.review_status; r.note=data.note; db.commit(); return row(r)
