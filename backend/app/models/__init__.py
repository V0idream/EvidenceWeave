from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, Float, JSON, ForeignKey, UniqueConstraint
from ..db import Base

def uid(): return uuid4().hex
def now(): return datetime.now(timezone.utc).isoformat()

class Case(Base):
    __tablename__ = 'cases'
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)
    description = Column(Text, default='')
    target_person_id = Column(String, nullable=True)
    created_at = Column(String, default=now)
    updated_at = Column(String, default=now, onupdate=now)
    analysis_status = Column(String, default='PENDING')
    analysis_phase = Column(String, default='PENDING')
    analysis_error = Column(Text, default='')
    progress = Column(String, default='等待导入 PDF')
    active_run_id = Column(String, nullable=True)
    model_used = Column(String, default='')

class Person(Base):
    __tablename__ = 'persons'
    __table_args__ = (UniqueConstraint('case_id', 'canonical_name'),)
    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey('cases.id'), nullable=False, index=True)
    canonical_name = Column(String, nullable=False)
    role = Column(String, default='other')
    aliases = Column(JSON, default=list)
    pending_aliases = Column(JSON, default=list)

class Document(Base):
    __tablename__ = 'documents'
    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey('cases.id'), nullable=False, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    document_type = Column(String, default='other')
    source_person_id = Column(String, ForeignKey('persons.id'), nullable=True)
    statement_time = Column(String, nullable=True)
    total_pages = Column(Integer, default=0)
    parser_type = Column(String, default='PyMuPDF')
    processing_status = Column(String, default='PENDING')
    warnings = Column(JSON, default=list)
    created_at = Column(String, default=now)

class DocumentBlock(Base):
    __tablename__ = 'document_blocks'
    id = Column(String, primary_key=True, default=uid)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    block_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    bbox = Column(JSON, nullable=True)
    locator_metadata = Column(JSON, default=dict)

class Statement(Base):
    __tablename__ = 'statements'
    id = Column(String, primary_key=True, default=uid)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False)
    source_person_id = Column(String, ForeignKey('persons.id'), nullable=True)
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    block_ids = Column(JSON, nullable=False)
    statement_time = Column(String, nullable=True)
    run_id = Column(String, nullable=False)

class Fact(Base):
    __tablename__ = 'facts'
    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey('cases.id'), nullable=False, index=True)
    run_id = Column(String, nullable=False, index=True)
    statement_id = Column(String, ForeignKey('statements.id'), nullable=False)
    subject_person_id = Column(String, ForeignKey('persons.id'), nullable=True)
    predicate = Column(String, nullable=False)
    object_text = Column(Text, default='')
    object_person_id = Column(String, ForeignKey('persons.id'), nullable=True)
    recipient_person_id = Column(String, ForeignKey('persons.id'), nullable=True)
    location = Column(String, default='')
    time_text = Column(String, default='')
    normalized_time_start = Column(String, nullable=True)
    normalized_time_end = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    polarity = Column(String, nullable=False)
    source_person_id = Column(String, ForeignKey('persons.id'), nullable=True)
    source_type = Column(String, default='unknown')
    document_id = Column(String, ForeignKey('documents.id'), nullable=False)
    page_number = Column(Integer, nullable=False)
    quote = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    extraction_metadata = Column(JSON, default=dict)

class EvidenceRelation(Base):
    __tablename__ = 'evidence_relations'
    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey('cases.id'), nullable=False, index=True)
    run_id = Column(String, nullable=False, index=True)
    fact_a_id = Column(String, ForeignKey('facts.id'), nullable=False)
    fact_b_id = Column(String, ForeignKey('facts.id'), nullable=False)
    relation_type = Column(String, nullable=False)
    issue_key = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(String, default=now)

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(String, primary_key=True, default=uid)
    evidence_relation_id = Column(String, ForeignKey('evidence_relations.id'), nullable=False, unique=True)
    review_status = Column(String, default='UNREVIEWED')
    note = Column(Text, default='')
    created_at = Column(String, default=now)
    updated_at = Column(String, default=now, onupdate=now)
