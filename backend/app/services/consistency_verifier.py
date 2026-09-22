import json
from pathlib import Path
from ..schemas import Verification

PROMPT = (Path(__file__).parents[1]/'llm/prompts/verification.txt').read_text(encoding='utf-8')

def verification_prompt(a,b):
    def view(f):
        value={k:getattr(f,k) for k in ('predicate','object_text','location','time_text','amount','polarity','source_type','quote')}
        meta=getattr(f,'extraction_metadata',{}) or {}
        value.update({'subject':meta.get('subject_text',getattr(f,'subject','')),
                      'source_person':meta.get('source_person_text',getattr(f,'source_person',''))})
        return value
    return PROMPT+'\n'+json.dumps({'Fact A':view(a),'Fact B':view(b)},ensure_ascii=False)

def verify(llm,a,b):
    result=llm.structured(verification_prompt(a,b),Verification)
    # Objective records enter the potential-conflict queue whenever the model
    # identifies a comparable discrepancy. Final judgment remains manual.
    if result.relation_type=='PARTIAL_DIFFERENCE' and (
        getattr(a,'source_type',None)=='objective' or getattr(b,'source_type',None)=='objective'
    ):
        return Verification(
            relation_type='CONTRADICTS',
            explanation='客观记录存在可比细节不一致，列为潜在矛盾并交由人工核验。'+result.explanation,
            confidence=result.confidence,
        )
    return result
