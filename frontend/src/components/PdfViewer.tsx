import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { ChevronLeft, ChevronRight, ExternalLink, X } from "lucide-react";
import type { Source } from "../types";
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
export function PdfViewer({
  source,
  onClose,
}: {
  source: Source;
  onClose: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [page, setPage] = useState(source.page_number);
  const [total, setTotal] = useState(1);
  const [error, setError] = useState("");
  const [size, setSize] = useState({ width: 0, height: 0 });
  useEffect(() => {
    setPage(source.page_number);
  }, [source]);
  useEffect(() => {
    let canceled = false;
    let renderTask: ReturnType<pdfjs.PDFPageProxy["render"]> | undefined;
    const loading = pdfjs.getDocument({
      url: "/api/documents/" + source.document_id + "/file",
      cMapUrl: "/pdfjs/cmaps/",
      cMapPacked: true,
      standardFontDataUrl: "/pdfjs/standard_fonts/",
      wasmUrl: "/pdfjs/wasm/",
    });
    setError("");
    (async () => {
      try {
        const doc = await loading.promise;
        if (canceled) return;
        setTotal(doc.numPages);
        const pdfPage = await doc.getPage(page);
        if (canceled || !canvas.current) return;
        const viewport = pdfPage.getViewport({ scale: 1.35 });
        const c = canvas.current;
        c.width = viewport.width;
        c.height = viewport.height;
        setSize({ width: viewport.width, height: viewport.height });
        renderTask = pdfPage.render({ canvas: c, viewport });
        await renderTask.promise;
      } catch (e) {
        if (!canceled) setError(String(e));
      }
    })();
    return () => {
      canceled = true;
      renderTask?.cancel();
      void loading.destroy();
    };
  }, [source.document_id, page]);
  const box = source.bbox;
  const meta = source.locator_metadata;
  return (
    <div
      className="modal-shade"
      role="dialog"
      aria-modal="true"
      aria-label="PDF 原文定位"
    >
      <div className="pdf-modal">
        <header>
          <div>
            <small>ORIGINAL RECORD · 原始卷宗</small>
            <h3>{source.filename}</h3>
          </div>
          <button className="icon" onClick={onClose} aria-label="关闭原文">
            <X />
          </button>
        </header>
        <div className="pdf-controls">
          <button
            className="icon"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            aria-label="上一页"
          >
            <ChevronLeft />
          </button>
          <span>
            第 {page} / {total} 页
          </span>
          <button
            className="icon"
            disabled={page >= total}
            onClick={() => setPage(page + 1)}
            aria-label="下一页"
          >
            <ChevronRight />
          </button>
          <button
            className="text-btn"
            onClick={() => setPage(source.page_number)}
          >
            回到引用页
          </button>
          <a
            target="_blank"
            rel="noreferrer"
            href={"/api/documents/" + source.document_id + "/file#page=" + page}
          >
            <ExternalLink size={15} /> 打开 PDF
          </a>
        </div>
        <div className="pdf-scroll">
          {error ? (
            <div className="notice error">PDF 显示失败：{error}</div>
          ) : (
            <div
              className="pdf-paper"
              style={{
                aspectRatio:
                  size.width && size.height
                    ? `${size.width}/${size.height}`
                    : undefined,
              }}
            >
              <canvas ref={canvas} />
              {box && meta?.width && page === source.page_number && (
                <div
                  className="pdf-highlight"
                  style={{
                    left: (box[0] / meta.width) * 100 + "%",
                    top: (box[1] / meta.height) * 100 + "%",
                    width: ((box[2] - box[0]) / meta.width) * 100 + "%",
                    height: ((box[3] - box[1]) / meta.height) * 100 + "%",
                  }}
                />
              )}
            </div>
          )}
        </div>
        {source.quote && (
          <div className="pdf-quote">
            <small>
              第 {source.page_number} 页 · 原文摘录
              {box ? " · 标记原文块" : " · 无可靠坐标"}
            </small>
            <p>{source.quote}</p>
          </div>
        )}
      </div>
    </div>
  );
}
