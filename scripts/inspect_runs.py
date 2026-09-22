from collections import Counter, defaultdict
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Fact, Statement

CASE_ID="ac80cc6c0a09460b8acfaca80e5f5504"
with SessionLocal() as db:
    facts=list(db.scalars(select(Fact).where(Fact.case_id==CASE_ID)))
    by=defaultdict(list)
    for f in facts: by[f.run_id].append(f)
    for run, items in by.items():
        print(run, len(items), Counter(f.predicate for f in items))
        print("questions", sum(1 for f in items if f.quote.lstrip().startswith(("问：","问:"))))
