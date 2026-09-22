import re
from datetime import datetime, timedelta

def chinese_number(value):
    digits = dict(zip('零一二三四五六七八九',range(10))); digits['两']=2
    units = {'十':10,'百':100,'千':1000,'万':10000,'亿':100000000}
    total = section = number = 0
    for char in value:
        if char in digits: number = digits[char]
        elif char in units:
            unit = units[char]
            if unit < 10000: section += (number or 1)*unit
            else: total += (section+number)*unit; section=0
            number=0
        else: return None
    return total+section+number

def amount(value):
    value = value.replace(',','').replace('，','').strip()
    m = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(万|亿)?(?:元|块|人民币)?', value)
    if m: return float(m[1]) * {'万':10000,'亿':100000000,None:1}[m[2]]
    m = re.fullmatch(r'([零一二两三四五六七八九十百千万亿]+)(?:元|块|人民币)?',value)
    return chinese_number(m[1]) if m else None

def normalize_time(text):
    # Never infer a missing year/date from the interrogation date.
    m = re.search(r'(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})日?',text)
    if not m: return None,None,'low'
    try:
        day = datetime(*map(int,m.groups()))
        clock = re.search(r'(\d{1,2}|[一二三四五六七八九十两]+)[点时:：](\d{1,2})?',text[m.end():])
        if not clock: return day.isoformat(),(day+timedelta(days=1)-timedelta(seconds=1)).isoformat(),'day'
        hour = int(clock[1]) if clock[1].isdigit() else chinese_number(clock[1])
        if ('晚' in text or '下午' in text) and hour < 12: hour += 12
        minute = int(clock[2]) if clock[2] else (30 if '半' in text else 0)
        point = day.replace(hour=hour,minute=minute)
        delta = timedelta(minutes=30 if any(x in text for x in ('左右','许','多','大约')) else 0)
        return (point-delta).isoformat(),(point+delta).isoformat(),'approximate' if delta else 'exact'
    except (ValueError,TypeError): return None,None,'low'

def normalize(fact):
    start,end,precision=normalize_time(fact.time_text)
    return {'normalized_time_start':start,'normalized_time_end':end,'amount':amount(fact.amount_text),
            'metadata':{'amount_text':fact.amount_text,'location_original':fact.location,
                        'location_normalized':re.sub(r'\s+','',fact.location),'time_precision':precision}}

def grounded_corrections(fact,document_type):
    """Conservative lexical guards; keep an audit of the original model fields."""
    changes={}
    if fact.predicate=='到场' and re.search(r'参与.{0,8}商议',fact.quote):
        changes['predicate']={'model':fact.predicate,'normalized':'商议'}
        fact.predicate='商议'
    if fact.polarity=='denied' and re.search(r'(?:不能确认|无法确认|不清楚|不知道|没有注意到).{0,25}是否',fact.quote.replace('\n','')):
        changes['polarity']={'model':fact.polarity,'normalized':'uncertain'}
        fact.polarity='uncertain'
    if fact.source_type=='objective' and document_type in ('interrogation','witness_statement','victim_statement'):
        changes['source_type']={'model':fact.source_type,'normalized':'unknown'}
        fact.source_type='unknown'
    return changes
