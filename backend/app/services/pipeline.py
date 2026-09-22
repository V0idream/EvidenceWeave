from sqlalchemy import select
from ..db import SessionLocal
from ..models import Case, Document, DocumentBlock, Statement, Fact, EvidenceRelation, uid
from ..llm.ollama import Ollama
from .entity_resolver import resolve
from .fact_extractor import extract
from .fact_normalizer import normalize,grounded_corrections
from .candidate_matcher import candidate_pairs, event_key
from .consistency_verifier import verify
from .source_locator import locate
from .text_units import units

BUSY = {'PARSING','EXTRACTING','NORMALIZING','MATCHING','VERIFYING'}

def analyze_case(case_id, llm=None):
    run_id=uid()
    with SessionLocal() as db:
        case=db.get(Case,case_id)
        def status(phase,message):
            case.analysis_status=phase; case.analysis_phase=phase; case.progress=message; db.commit()
        try:
            llm=llm or Ollama()
            if hasattr(llm,'select'): llm.select()
            docs=list(db.scalars(select(Document).where(Document.case_id==case_id)))
            facts=[]
            for di,doc in enumerate(docs,1):
                blocks=list(db.scalars(select(DocumentBlock).where(DocumentBlock.document_id==doc.id).order_by(DocumentBlock.page_number,DocumentBlock.block_index)))
                context='\n'.join(b.text for b in blocks[:3])[:2200]
                context+='\n材料类型：'+doc.document_type
                if doc.source_person_id:
                    from ..models import Person
                    context+='\n人工指定材料发言者：'+db.get(Person,doc.source_person_id).canonical_name
                for bi,unit in enumerate(units(blocks),1):
                    block=unit[0]
                    unit_text='\n'.join(b.text for b in unit)
                    # Bounded chunks retain the same original block ID and page coordinates.
                    for offset in range(0,len(unit_text),2400):
                        text=unit_text[offset:offset+2400]
                        status('EXTRACTING',f'文档 {di}/{len(docs)} · {doc.filename} · 第 {block.page_number} 页 · 块 {bi}/{len(blocks)}')
                        result=extract(llm,text,context)
                        for p in result.persons: resolve(db,case_id,p.name,p.role)
                        for af in result.facts:
                            corrections=grounded_corrections(af,doc.document_type)
                            def pid(name):
                                p=resolve(db,case_id,name)
                                return p.id if p else None
                            source=doc.source_person_id or pid(af.source_person)
                            statement=Statement(document_id=doc.id,source_person_id=source,page_number=block.page_number,
                                raw_text=text,block_ids=[b.id for b in unit],statement_time=doc.statement_time,run_id=run_id)
                            db.add(statement); db.flush()
                            normalized=normalize(af)
                            metadata=normalized.pop('metadata')
                            metadata['grounded_corrections']=corrections
                            metadata.update({'model':llm.model,'subject_text':af.subject,'source_person_text':af.source_person,'block_id':block.id})
                            fact=Fact(case_id=case_id,run_id=run_id,statement_id=statement.id,subject_person_id=pid(af.subject),
                                predicate=af.predicate,object_text=af.object_text,object_person_id=pid(af.object_person),
                                recipient_person_id=pid(af.recipient),location=af.location,time_text=af.time_text,polarity=af.polarity,
                                source_person_id=source,source_type=af.source_type,document_id=doc.id,page_number=block.page_number,
                                quote=af.quote,confidence=af.confidence,extraction_metadata=metadata,**normalized)
                            db.add(fact); db.flush(); locate(db,fact); facts.append(fact)
            status('NORMALIZING',f'已提取 {len(facts)} 条有来源事实，完成时间、金额和地点标准化')
            if not facts: raise ValueError('未提取到有来源的原子事实。请检查 PDF 文本、OCR 提示和模型输出；未发布空分析。')
            status('MATCHING','正在按人物、事件及时间筛选候选关系')
            pairs=list(candidate_pairs(facts))
            for i,(a,b) in enumerate(pairs,1):
                status('VERIFYING',f'正在核验候选关系 {i}/{len(pairs)}')
                result=verify(llm,a,b)
                locate(db,a); locate(db,b)
                issue=f'{a.subject_person_id}:{event_key(a)}:{(a.normalized_time_start or a.time_text)[:10]}'
                db.add(EvidenceRelation(case_id=case_id,run_id=run_id,fact_a_id=a.id,fact_b_id=b.id,
                    relation_type=result.relation_type,issue_key=issue,explanation=result.explanation,confidence=result.confidence))
            case.active_run_id=run_id; case.model_used=llm.model; case.analysis_error=''
            status('COMPLETED',f'完成 · {len(facts)} 条原子事实 · {len(pairs)} 条候选关系。AI 提示须经人工核验。')
        except Exception as exc:
            db.rollback()
            case=db.get(Case,case_id)
            case.analysis_error=str(exc)[:1600]; case.analysis_status='FAILED'; case.progress='分析失败，可修复后重试；上次完整分析和复核记录保留。'
            db.commit()
