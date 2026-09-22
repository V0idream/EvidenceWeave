import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db
from ..models import Document, DocumentBlock, uid
from ..schemas import DocumentInput
from ..services.document_parser import parse_pdf
from ..services.entity_resolver import discover_literal,resolve
from .common import row,get_case,check_person,mark_changed

router=APIRouter()

def ingest(db,case_id,path,filename,doc_id):
    parsed=parse_pdf(path)
    doc=Document(id=doc_id,case_id=case_id,filename=filename,original_path=str(path),total_pages=len(parsed['pages']),
        processing_status='NEEDS_ATTENTION' if parsed['warnings'] else 'READY',warnings=parsed['warnings'])
    header='\n'.join(b['text'] for p in parsed['pages'][:1] for b in p['blocks'])
    discover_literal(db,case_id,header)
    source=re.search(r'(被讯问人|证人|被害人)[：: \t]+([\u4e00-\u9fff]{2,4})(?=[\s，。；:：]|$)',header)
    if source:
        doc.source_person_id=resolve(db,case_id,source[2]).id
        doc.document_type='interrogation' if source[1]=='被讯问人' else 'witness_statement'
    for marker,kind in [('银行流水','bank_record'),('监控摘要','surveillance'),('聊天记录','chat_record')]:
        if marker in header: doc.document_type=kind
    date=re.search(r'(?:讯问日期|询问日期|记录日期)[：: ]*(\d{4}-\d{2}-\d{2})',header)
    if date: doc.statement_time=date[1]
    db.add(doc); db.flush()
    for p in parsed['pages']:
        for index,b in enumerate(p['blocks']):
            db.add(DocumentBlock(document_id=doc.id,page_number=p['page_number'],block_index=index,text=b['text'],bbox=b['bbox'],
                locator_metadata={'width':p['width'],'height':p['height'],'parser':b['parser'],'quality':p['quality']}))
            if b['parser']=='MinerU': doc.parser_type='PyMuPDF + MinerU'
    mark_changed(get_case(db,case_id))
    db.commit(); return row(doc)

@router.post('/cases/{case_id}/documents',status_code=201)
def upload(case_id:str,files:list[UploadFile]=File(...),db:Session=Depends(get_db)):
    get_case(db,case_id,True)
    if len(files)>100: raise HTTPException(422,'每次最多上传 100 份 PDF')
    imported=[]; errors=[]
    directory=settings.data_dir/'documents'/case_id; directory.mkdir(parents=True,exist_ok=True)
    for file in files:
        name=Path((file.filename or 'document.pdf').replace('\\','/')).name
        doc_id=uid(); path=directory/(doc_id+'.pdf')
        try:
            size=0
            with path.open('wb') as output:
                while chunk:=file.file.read(1024*1024):
                    size+=len(chunk)
                    if size>settings.max_upload_mb*1024*1024: raise ValueError(f'文件超过 {settings.max_upload_mb} MB 限制')
                    output.write(chunk)
            with path.open('rb') as stream:
                if b'%PDF-' not in stream.read(1024): raise ValueError('文件内容不是 PDF')
            imported.append(ingest(db,case_id,path,name,doc_id))
        except Exception as exc:
            db.rollback(); path.unlink(missing_ok=True); errors.append({'filename':name,'error':str(exc)[:600]})
        finally: file.file.close()
    return {'documents':imported,'errors':errors}

@router.get('/cases/{case_id}/documents')
def documents(case_id:str,db:Session=Depends(get_db)):
    get_case(db,case_id)
    return [row(d) for d in db.scalars(select(Document).where(Document.case_id==case_id).order_by(Document.created_at))]

def get_document(db,doc_id):
    d=db.get(Document,doc_id)
    if not d: raise HTTPException(404,'文档不存在')
    return d

@router.get('/documents/{doc_id}/file')
def file(doc_id:str,db:Session=Depends(get_db)):
    doc=get_document(db,doc_id)
    return FileResponse(doc.original_path,media_type='application/pdf',filename=doc.filename,content_disposition_type='inline')

@router.get('/documents/{doc_id}/blocks')
def blocks(doc_id:str,db:Session=Depends(get_db)):
    get_document(db,doc_id)
    return [row(b) for b in db.scalars(select(DocumentBlock).where(DocumentBlock.document_id==doc_id).order_by(DocumentBlock.page_number,DocumentBlock.block_index))]

@router.patch('/documents/{doc_id}')
def edit(doc_id:str,data:DocumentInput,db:Session=Depends(get_db)):
    doc=get_document(db,doc_id); get_case(db,doc.case_id,True)
    if data.source_person_id: check_person(db,doc.case_id,data.source_person_id)
    if data.statement_time:
        from datetime import date
        try: date.fromisoformat(data.statement_time)
        except ValueError: raise HTTPException(422,'陈述日期应为 YYYY-MM-DD')
    for key,value in data.model_dump().items(): setattr(doc,key,value)
    mark_changed(get_case(db,doc.case_id))
    db.commit(); return row(doc)
