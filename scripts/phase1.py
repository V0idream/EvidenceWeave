"""Run the real local PDF -> citations pipeline without database or browser."""
import sys,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.llm.ollama import Ollama
from app.services.document_parser import parse_pdf
from app.services.fact_extractor import extract
from app.services.fact_normalizer import normalize
from app.services.candidate_matcher import candidate_pairs
from app.services.consistency_verifier import verify

def main(paths):
    llm=Ollama();llm.select(); facts=[]
    for path in paths:
        parsed=parse_pdf(path)
        context='\n'.join(b['text'] for p in parsed['pages'][:1] for b in p['blocks'])
        for page in parsed['pages']:
            for i,block in enumerate(page['blocks']):
                result=extract(llm,block['text'],context)
                for f in result.facts:
                    n=normalize(f); n.pop('metadata')
                    facts.append(SimpleNamespace(**f.model_dump(),**n,subject_person_id=f.subject,recipient_person_id=f.recipient,
                        statement_id=f'{path}:{page["page_number"]}:{i}',document_id=Path(path).name,page_number=page['page_number']))
    relations=[]
    for a,b in candidate_pairs(facts):
        r=verify(llm,a,b)
        def source(f):return {'document':f.document_id,'page':f.page_number,'quote':f.quote,'predicate':f.predicate,'subject':f.subject}
        relations.append({**r.model_dump(),'fact_a':source(a),'fact_b':source(b)})
    output={'model':llm.model,'facts':len(facts),'relations':relations}
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=='__main__': main(sys.argv[1:])
