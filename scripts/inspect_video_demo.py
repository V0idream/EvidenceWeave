from collections import Counter
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Fact, Statement, Person

CASE_ID = "ac80cc6c0a09460b8acfaca80e5f5504"
with SessionLocal() as db:
    facts = list(db.scalars(select(Fact).where(Fact.case_id == CASE_ID)))
    people = {p.id:p.canonical_name for p in db.scalars(select(Person).where(Person.case_id == CASE_ID))}
    print("facts", len(facts))
    print("predicates", Counter(f.predicate for f in facts))
    for f in facts:
        print(f.predicate, f.polarity, people.get(f.subject_person_id), "|", f.quote)
