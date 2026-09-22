from pathlib import Path
import re
from ..schemas import Extraction

PROMPT = (Path(__file__).parents[1] / 'llm/prompts/extraction.txt').read_text(encoding='utf-8')

def original_quote(text, quote):
    if quote.strip() and quote in text: return quote
    # PDF line wrapping is whitespace, not evidence. Restore the EXACT source span
    # after a whitespace-only match. Never fuzzy-match or change lexical characters.
    positions=[i for i,c in enumerate(text) if not c.isspace()]
    compact=''.join(text[i] for i in positions)
    needle=''.join(c for c in quote if not c.isspace())
    start=compact.find(needle) if needle else -1
    if start<0: raise ValueError('引用校验失败：模型引文不是原始块的连续原文，已拒绝保存。')
    return text[positions[start]:positions[start+len(needle)-1]+1]

def extract(llm, text, context=''):
    # Recognizable form metadata and interrogator questions cannot establish facts.
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    if lines and all(re.match(r'^(?:被讯问人|被告人|案件被告人|案件相关人员|证人|被害人|询问人|讯问日期|询问日期|记录日期|姓名|性别|出生日期|卷号|页码)[：:]|^\d+[_、].*(?:讯问|证言|摘要)$|^EvidenceWeave |^本材料完全虚构',line) for line in lines):
        return Extraction(persons=[],facts=[])
    analysis_lines=[line for line in lines if not re.match(r'^(?:问|询问人|讯问人)[：:]',line)]
    analysis_text='\n'.join(analysis_lines)
    if not analysis_text.strip():
        return Extraction(persons=[],facts=[])
    prompt=PROMPT + '\n上下文：\n' + context + '\n当前块（仅此可引用）：\n' + analysis_text
    result = llm.structured(prompt, Extraction)
    try:
        for fact in result.facts: fact.quote=original_quote(text,fact.quote)
    except ValueError:
        # One grounded retry; an invalid citation is never written or silently accepted.
        result=llm.structured(prompt+'\n校验反馈：上一输出引用了块外内容或改写原文。只复制当前块中原句，保留“我”等字样；本块无事件则 facts=[]。',Extraction)
        for fact in result.facts: fact.quote=original_quote(text,fact.quote)
    unique=[]; seen=set()
    for fact in result.facts:
        key=(fact.subject,fact.predicate,fact.object_text,fact.object_person,fact.recipient,fact.location,
             fact.time_text,fact.amount_text,fact.polarity,fact.source_person,fact.source_type,fact.quote)
        if key not in seen:
            seen.add(key); unique.append(fact)
    result.facts=unique
    return result
