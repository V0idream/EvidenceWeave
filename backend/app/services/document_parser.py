import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import pymupdf as fitz
from ..config import settings

class OCRUnavailable(RuntimeError): pass

class MinerUProvider:
    def available(self):
        return settings.ocr_provider.lower() == 'mineru' and shutil.which(settings.mineru_command) is not None

    def parse(self, path):
        if not self.available():
            raise OCRUnavailable('此页需要 OCR；MinerU 未配置或未安装。文本页仍可使用。')
        with tempfile.TemporaryDirectory(prefix='ew-ocr-', dir=settings.data_dir) as tmp:
            result = subprocess.run([settings.mineru_command, '-p', str(path), '-o', tmp, '-b', 'pipeline'],
                                    capture_output=True, timeout=900, env={**__import__('os').environ, 'MINERU_MODEL_SOURCE':'local'})
            if result.returncode:
                raise OCRUnavailable('MinerU 本地解析失败，请检查本地权重和命令配置。')
            files = list(Path(tmp).rglob('*_content_list.json'))
            if not files: raise OCRUnavailable('MinerU 未输出 content_list.json；请检查版本兼容性。')
            items = json.loads(files[0].read_text(encoding='utf-8'))
            pages = {}
            for item in items:
                text = item.get('text') or item.get('table_body') or ''
                if text.strip():
                    pages.setdefault(int(item.get('page_idx',0))+1, []).append({'text':text,'bbox':None,'parser':'MinerU'})
            return pages

def quality(text):
    chars = [c for c in text if not c.isspace()]
    count = len(chars)
    printable = sum(c.isprintable() for c in chars) / max(count,1)
    bad = sum(c == '\ufffd' or '\ue000' <= c <= '\uf8ff' for c in chars) / max(count,1)
    return {'characters':count, 'printable_ratio':printable, 'garbled_ratio':bad,
            'reliable':count >= 15 and printable >= .95 and bad < .05}

def parse_pdf(path, ocr=None):
    ocr = ocr or MinerUProvider()
    pages, warnings, low = [], [], []
    try:
        with fitz.open(path) as pdf:
            if pdf.needs_pass: raise ValueError('PDF 已加密，请先提供未加密副本')
            if pdf.page_count == 0: raise ValueError('PDF 没有页面')
            for number, page in enumerate(pdf,1):
                text = page.get_text()
                q = quality(text)
                blocks = [{'text':b[4].strip(),'bbox':list(b[:4]),'parser':'PyMuPDF'} for b in page.get_text('blocks') if b[6] == 0 and b[4].strip()]
                if not q['reliable']: low.append(number)
                pages.append({'page_number':number,'blocks':blocks,'quality':q,'width':page.rect.width,'height':page.rect.height})
    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise ValueError('无效或空 PDF') from exc
    if low:
        try:
            parsed = ocr.parse(path)
            for page in pages:
                if page['page_number'] in low:
                    if parsed.get(page['page_number']):
                        page['blocks'] = parsed[page['page_number']]
                        page['quality'] = quality('\n'.join(b['text'] for b in page['blocks']))
                    else: warnings.append(f"第 {page['page_number']} 页未识别到文字，可能为空页；请人工检查。")
        except (OCRUnavailable, subprocess.TimeoutExpired) as exc:
            warnings.append(f'第 {", ".join(map(str,low))} 页：{exc}')
    return {'pages':pages,'warnings':warnings,'empty_page_ratio':sum(not p['blocks'] for p in pages)/len(pages)}
