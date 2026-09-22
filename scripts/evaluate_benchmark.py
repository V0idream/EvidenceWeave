"""Evaluate only fixed hand-authored pairs; missing facts are misses, not exclusions."""
import argparse,json
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
def compact(text):return ''.join(text.split())
def evaluate(cid):
    gold=json.loads((ROOT/'benchmark/synthetic_case/gold_labels.json').read_text(encoding='utf-8'))
    with httpx.Client(base_url='http://127.0.0.1:8765/api',timeout=60,trust_env=False) as client:
        case=client.get('/cases/'+cid).json()
        facts=client.get('/cases/'+cid+'/facts?all_persons=true').json()
        relations=client.get('/cases/'+cid+'/relations?all_persons=true').json()
        persons=client.get('/cases/'+cid+'/persons').json()
        documents=client.get('/cases/'+cid+'/documents').json()
        blocks={d['id']:client.get('/documents/'+d['id']+'/blocks').json() for d in documents}
    def ids(key):
        s=gold['statements'][key]
        return {f['id'] for f in facts if f['source']['filename']==s['document'] and f['page_number']==s['page'] and (compact(f['quote']) in compact(s['quote']) or compact(s['quote']) in compact(f['quote']))}
    results=[]; tp=fp=fn=0
    for label in gold['labels']:
        a,b=ids(label['a']),ids(label['b'])
        predicted={r['relation_type'] for r in relations if (r['fact_a_id'] in a and r['fact_b_id'] in b) or (r['fact_a_id'] in b and r['fact_b_id'] in a)}
        # INDEPENDENT may correctly be filtered out by the candidate matcher.
        actual='CONTRADICTS' if 'CONTRADICTS' in predicted else label['relation_type'] if label['relation_type'] in predicted else sorted(predicted)[0] if predicted else ('INDEPENDENT' if a and b else 'MISSING')
        expected=label['relation_type']
        tp+=actual==expected=='CONTRADICTS'; fp+=actual=='CONTRADICTS' and expected!='CONTRADICTS'; fn+=actual!='CONTRADICTS' and expected=='CONTRADICTS'
        results.append({**label,'predicted':actual,'matched_facts_a':len(a),'matched_facts_b':len(b),'correct':actual==expected})
    valid=sum(bool(f['quote']) and f['quote'] in '\n'.join(b['text'] for b in blocks.get(f['document_id'],[]) if b['id'] in f['source']['block_ids'] and b['page_number']==f['page_number']) for f in facts)
    expected_people=set(sum(gold['persons'].values(),[])); actual_people={p['canonical_name'] for p in persons}
    report={'case_id':cid,'status':case['analysis_status'],'model':case['model_used'],'scope':'20 fixed synthetic labeled pairs; not a real-world accuracy claim',
      'documents':len(documents),'facts':len(facts),'relations':len(relations),'contradiction_precision':tp/(tp+fp) if tp+fp else None,'contradiction_recall':tp/(tp+fn) if tp+fn else None,
      'source_citation_accuracy':valid/len(facts) if facts else None,'person_precision':len(expected_people&actual_people)/len(actual_people) if actual_people else None,
      'person_recall':len(expected_people&actual_people)/len(expected_people),'pair_accuracy':sum(r['correct'] for r in results)/len(results),'true_positive':tp,'false_positive':fp,'false_negative':fn,'results':results}
    output=ROOT/'benchmark/last_report.json';output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case_id');evaluate(parser.parse_args().case_id)
