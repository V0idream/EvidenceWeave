"""Join geometric line continuations without discarding original block IDs."""
def units(blocks):
    result=[]
    for block in blocks:
        previous=result[-1][-1] if result else None
        join=False
        if previous and previous.page_number==block.page_number and previous.bbox and block.bbox:
            a,b=previous.bbox,block.bbox
            gap=b[1]-a[3]
            # Never join columns, pages, or completed sentences/paragraphs.
            join=(abs(a[0]-b[0])<12 and -2<=gap<=max(a[3]-a[1],b[3]-b[1])*.9
                  and previous.text.rstrip()[-1:] not in '。！？.!?；;：:')
        if join: result[-1].append(block)
        else: result.append([block])
    return result
