from app.db import Base,engine,SessionLocal
from app.models import Case,Person
from app.services.entity_resolver import discover_literal,resolve
from sqlalchemy import select

def test_title_is_not_a_person_and_roster_has_roles():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        c=Case(name='人物检测');db.add(c);db.flush()
        discover_literal(db,c.id,'13_周某_证人证言\n证人：周某\n案件被告人：张某、李某、王某、赵某、孙某。')
        people={p.canonical_name:p.role for p in db.scalars(select(Person).where(Person.case_id==c.id))}
        assert '证言' not in people
        assert people['周某']=='witness'
        assert all(people[n]=='defendant' for n in ('张某','李某','王某','赵某','孙某'))
        assert resolve(db,c.id,'bank_record') is None
        assert resolve(db,c.id,'other') is None
        db.rollback()
