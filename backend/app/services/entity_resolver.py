import re
from sqlalchemy import select
from ..models import Person

PLACEHOLDERS = {
    'other', 'unknown', 'objective', 'self_report', 'eyewitness', 'hearsay',
    'interrogation', 'witness_statement', 'victim_statement', 'objective_evidence',
    'chat_record', 'bank_record', 'surveillance', 'none', 'null', 'n/a',
    '未知', '不详', '无', '客观记录', '来源未明确',
}

def is_placeholder(name):
    return name.strip().lower() in PLACEHOLDERS

def resolve(db, case_id, name, role='other'):
    name = name.strip()
    if not name or name in ('我','他','她','我们') or is_placeholder(name): return None
    people = list(db.scalars(select(Person).where(Person.case_id == case_id)))
    for p in people:
        if name == p.canonical_name or name in p.aliases:
            if p.role=='other' and role!='other': p.role=role
            return p
    # Similar names are suggestions only; never automatically merge them.
    suggestions = [p.canonical_name for p in people if name[0] == p.canonical_name[0] and ('某' in name or '某' in p.canonical_name)]
    person = Person(case_id=case_id, canonical_name=name, role=role, aliases=[], pending_aliases=suggestions)
    db.add(person); db.flush()
    return person

def discover_literal(db, case_id, text):
    for roster in re.findall(r'(?:案件)?被告人[：:]([^\n。]+)',text):
        for name in re.split(r'[、，,]',roster):
            if re.fullmatch(r'[\u4e00-\u9fff]{2,4}',name.strip()): resolve(db,case_id,name,'defendant')
    for role, name in re.findall(r'(被告人|被讯问人|证人|被害人|询问人)[：: \t]+([\u4e00-\u9fff]{2,4})(?=[\s，。；:：]|$)', text):
        resolve(db, case_id, name, {'被告人':'defendant','被讯问人':'defendant','证人':'witness','被害人':'victim','询问人':'investigator'}[role])
    for name in set(re.findall(r'[\u4e00-\u9fff]某(?:某)?', text)):
        resolve(db, case_id, name)
