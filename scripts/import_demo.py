import argparse,json
from pathlib import Path
from contextlib import ExitStack
import httpx

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--case-id'); parser.add_argument('--analyze',action='store_true'); args=parser.parse_args()
    with httpx.Client(base_url='http://127.0.0.1:8765/api',timeout=120,trust_env=False) as client:
        cid=args.case_id
        if not cid:
            response=client.post('/cases',json={'name':'鑫源宾馆案 · 虚构演示','description':'Synthetic data · 17 份虚构卷宗，仅用于软件测试'})
            response.raise_for_status(); cid=response.json()['id']
        with ExitStack() as stack:
            files=[('files',(p.name,stack.enter_context(p.open('rb')),'application/pdf')) for p in sorted((ROOT/'benchmark/synthetic_case').glob('*.pdf'))]
            response=client.post('/cases/'+cid+'/documents',files=files); response.raise_for_status()
            result=response.json()
        people=client.get('/cases/'+cid+'/persons').json()
        target=next((p for p in people if p['canonical_name']=='张某'),None)
        if target: client.patch('/cases/'+cid+'/target-person',json={'person_id':target['id']}).raise_for_status()
        if args.analyze: client.post('/cases/'+cid+'/analyze').raise_for_status()
        print(json.dumps({'case_id':cid,'imported':len(result['documents']),'errors':result['errors']},ensure_ascii=False))
if __name__=='__main__': main()
