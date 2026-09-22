from collections import defaultdict
from datetime import datetime, timedelta
from itertools import combinations

EVENTS = {'进入':'presence','到场':'presence','到达':'presence','前往':'presence','离开':'departure',
          '交付':'transfer','给付':'transfer','收款':'transfer','转账':'transfer','收到':'transfer'}

def event_key(f):
    kind=EVENTS.get(f.predicate,f.predicate)
    if kind=='transfer':
        obj=f.object_text or ''
        if f.predicate in ('收款','转账','收到') or getattr(f,'amount',None) is not None or any(word in obj for word in ('现金','货款','万元','人民币')):
            return 'transfer:money'
        if any(word in obj for word in ('手提袋','袋子','包')): return 'transfer:bag'
    return kind

def candidate_pairs(facts):
    groups=defaultdict(list)
    for f in facts:
        if f.subject_person_id:
            groups[(f.subject_person_id,event_key(f))].append(f)
    for group in groups.values():
        for a,b in combinations(group,2):
            if a.statement_id == b.statement_id: continue
            if a.normalized_time_start and b.normalized_time_start:
                sa,ea = datetime.fromisoformat(a.normalized_time_start),datetime.fromisoformat(a.normalized_time_end)
                sb,eb = datetime.fromisoformat(b.normalized_time_start),datetime.fromisoformat(b.normalized_time_end)
                # Objective records often expose the discrepancy itself through
                # a wider time gap (for example surveillance vs ride records).
                hours=12 if ('objective' in (getattr(a,'source_type',None),getattr(b,'source_type',None))) else 2
                if sa > eb+timedelta(hours=hours) or sb > ea+timedelta(hours=hours): continue
            # Do not filter different amounts, locations or recipients: these may be the actual disputed dimension.
            # With no dated event, require one other comparable anchor to avoid all-to-all LLM calls.
            if not a.normalized_time_start and not b.normalized_time_start:
                if not ((a.location and a.location == b.location) or (a.object_text and a.object_text == b.object_text)
                        or (a.recipient_person_id and a.recipient_person_id == b.recipient_person_id)): continue
            yield a,b
