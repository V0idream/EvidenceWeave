from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ExtractedPerson(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    role: Literal['defendant', 'witness', 'victim', 'investigator', 'other']

class AtomicFact(StrictModel):
    subject: str
    predicate: Literal['到场','进入','离开','交付','收款','转账','商议','联系','看见','持有','其他']
    object_text: str
    object_person: str
    recipient: str
    location: str
    time_text: str
    amount_text: str
    polarity: Literal['affirmed', 'denied', 'uncertain', 'unknown']
    source_person: str
    source_type: Literal['self_report', 'eyewitness', 'hearsay', 'objective', 'unknown']
    quote: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)

class Extraction(StrictModel):
    persons: list[ExtractedPerson]
    facts: list[AtomicFact]

class Verification(StrictModel):
    relation_type: Literal['SUPPORTS', 'CONTRADICTS', 'PARTIAL_DIFFERENCE', 'INDEPENDENT']
    explanation: str = Field(min_length=1, max_length=1500)
    confidence: float = Field(ge=0, le=1)

class CaseInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=4000)

class PersonInput(StrictModel):
    canonical_name: str = Field(min_length=1, max_length=80)
    role: Literal['defendant', 'witness', 'victim', 'investigator', 'other'] = 'other'
    aliases: list[str] = Field(default_factory=list, max_length=50)

class TargetInput(StrictModel):
    person_id: str

class MergeInput(StrictModel):
    target_person_id: str
    confirmed_same_person: Literal[True]

class ReviewInput(StrictModel):
    review_status: Literal['CONFIRMED', 'DISMISSED', 'UNCERTAIN', 'UNREVIEWED']
    note: str = Field(default='', max_length=6000)

class DocumentInput(StrictModel):
    document_type: Literal['interrogation','witness_statement','victim_statement','objective_evidence','chat_record','bank_record','surveillance','other']
    source_person_id: str | None = None
    statement_time: str | None = None
