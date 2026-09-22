from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, update
from .config import settings,ROOT
from .db import Base,engine,SessionLocal
from .models import Case, Person, Document, Statement, Fact, EvidenceRelation
from .services.entity_resolver import is_placeholder
from .api import cases,documents,analysis,reviews
from .llm.ollama import Ollama
from .services.document_parser import MinerUProvider
from .services.pipeline import BUSY

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for c in db.scalars(select(Case).where(Case.analysis_status.in_(BUSY))):
            c.analysis_status='FAILED'; c.analysis_error='上次进程已中断。可以重试；此前完整结果仍保留。'
        # Older model runs may have emitted schema labels such as "other" as a
        # person name. They are explicit placeholders, never case entities.
        for person in list(db.scalars(select(Person))):
            if is_placeholder(person.canonical_name):
                for model,column in ((Document,'source_person_id'),(Statement,'source_person_id'),
                                     (Fact,'source_person_id'),(Fact,'subject_person_id'),
                                     (Fact,'object_person_id'),(Fact,'recipient_person_id')):
                    db.execute(update(model).where(getattr(model,column)==person.id).values({column:None}))
                for case in db.scalars(select(Case).where(Case.target_person_id==person.id)):
                    case.target_person_id=None
                db.delete(person)
        # Remove the retired relation category from existing local databases and
        # promote comparable objective-record differences into the review queue.
        for relation in db.scalars(select(EvidenceRelation)):
            if relation.relation_type=='INSUFFICIENT':
                relation.relation_type='INDEPENDENT'
                relation.explanation='现有材料无法确认属于同一事件，归入实际无关并保留人工复核。'+relation.explanation
            elif relation.relation_type=='PARTIAL_DIFFERENCE':
                a,b=db.get(Fact,relation.fact_a_id),db.get(Fact,relation.fact_b_id)
                if a and b and ('objective' in (a.source_type,b.source_type)):
                    relation.relation_type='CONTRADICTS'
                    relation.explanation='客观记录存在可比细节不一致，列为潜在矛盾并交由人工核验。'+relation.explanation
        db.commit()
    yield

app=FastAPI(title='EvidenceWeave Local API',version='1.0.0',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','[::1]','testserver'])

@app.middleware('http')
async def local_origin(request:Request,call_next):
    origin=request.headers.get('origin')
    if origin and origin not in ('http://127.0.0.1:8765','http://localhost:8765','http://127.0.0.1:5173','http://localhost:5173'):
        return JSONResponse({'detail':'仅接受本机工作台请求'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    return response

for router in (cases.router,documents.router,analysis.router,reviews.router):
    app.include_router(router,prefix='/api')
    app.include_router(router,include_in_schema=False)

@app.get('/api/system')
def system():
    llm=Ollama(); available=llm.available()
    selected=next((m for m in (settings.ollama_model,settings.ollama_fallback_model) if m in available),None)
    return {'local_mode':True,'llm':'Ollama','configured_model':settings.ollama_model,'active_model':selected,
            'available_models':available,'llm_ready':bool(selected),'parser':'PyMuPDF','ocr':'MinerU Local' if MinerUProvider().available() else 'unavailable',
            'database':'SQLite','external_ai_api':'Disabled'}

dist=ROOT/'frontend/dist'
if dist.is_dir():
    app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    if (dist/'pdfjs').is_dir(): app.mount('/pdfjs',StaticFiles(directory=dist/'pdfjs'),name='pdfjs')
    @app.get('/')
    def index(): return FileResponse(dist/'index.html')
