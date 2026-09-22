from sqlalchemy import select
from ..models import Document, DocumentBlock, Statement

def locate(db,fact):
    doc=db.get(Document,fact.document_id)
    statement=db.get(Statement,fact.statement_id)
    if not doc or not statement or statement.document_id != doc.id or statement.page_number != fact.page_number:
        raise ValueError('来源链路失效')
    blocks=list(db.scalars(select(DocumentBlock).where(DocumentBlock.document_id==doc.id,DocumentBlock.page_number==fact.page_number)))
    ordered=sorted([b for b in blocks if b.id in statement.block_ids],key=lambda b:statement.block_ids.index(b.id))
    text='\n'.join(b.text for b in ordered)
    start=text.find(fact.quote) if fact.quote else -1
    if start<0: raise ValueError('引用不在对应原文页块中')
    end=start+len(fact.quote); matched=[]; offset=0
    for block in ordered:
        if offset<end and offset+len(block.text)>start: matched.append(block)
        offset+=len(block.text)+1
    if not matched: raise ValueError('引用定位为空')
    boxes=[b.bbox for b in matched if b.bbox]
    bbox=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)] if len(boxes)==len(matched) else None
    return {'document_id':doc.id,'filename':doc.filename,'page_number':fact.page_number,'quote':fact.quote,
            'bbox':bbox,'block_ids':[b.id for b in matched],'locator_metadata':matched[0].locator_metadata,'statement_time':statement.statement_time}
