"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { SourceItem, TagMatch } from "@/types";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerProps {
  fileUrl: string | null;
  fileName: string | null;
  pageNumber: number;
  onPageNumberChange: (page: number) => void;
  sources: SourceItem[];
  onSourceSelect: (source: SourceItem) => void;
  tagMatches: TagMatch[];
  onTagMatchSelect: (match: TagMatch) => void;
}

export default function PdfViewer({
  fileUrl,
  fileName,
  pageNumber,
  onPageNumberChange,
  sources,
  onSourceSelect,
  tagMatches,
  onTagMatchSelect,
}: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [numPages, setNumPages] = useState(0);
  const [containerWidth, setContainerWidth] = useState(600);
  const [zoom, setZoom] = useState(1);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [panMode, setPanMode] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const dragStateRef = useRef<{ x: number; y: number; scrollLeft: number; scrollTop: number } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(Math.max(entry.contentRect.width - 64, 280));
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [isFullscreen]);

  useEffect(() => {
    setLoadError(null);
    setNumPages(0);
  }, [fileUrl]);

  useEffect(() => {
    if (!isFullscreen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen]);

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (!panMode || !containerRef.current) return;
    e.preventDefault();
    try {
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // 포인터 캡처가 지원되지 않는 환경이어도 드래그 이동 자체는 계속 동작한다.
    }
    dragStateRef.current = {
      x: e.clientX,
      y: e.clientY,
      scrollLeft: containerRef.current.scrollLeft,
      scrollTop: containerRef.current.scrollTop,
    };
    setIsDragging(true);
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragStateRef.current || !containerRef.current) return;
    const drag = dragStateRef.current;
    containerRef.current.scrollLeft = drag.scrollLeft - (e.clientX - drag.x);
    containerRef.current.scrollTop = drag.scrollTop - (e.clientY - drag.y);
  }

  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    dragStateRef.current = null;
    setIsDragging(false);
    if (containerRef.current) {
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
    }
  }

  const renderedWidth = containerWidth * zoom;

  const currentPageMatches = useMemo(
    () =>
      tagMatches.filter(
        (m) => m.file_name === fileName && m.page_number === pageNumber && m.page_width > 0
      ),
    [tagMatches, fileName, pageNumber]
  );

  if (!fileUrl) {
    return (
      <section className="w-[55%] flex flex-col bg-surface-container-lowest items-center justify-center text-center px-lg">
        <span className="material-symbols-outlined text-6xl text-on-tertiary-container mb-md">picture_as_pdf</span>
        <p className="text-on-tertiary-container font-body-base max-w-sm">
          답변의 근거가 된 PDF 페이지가 여기에 표시됩니다. 관련 문서 항목을 클릭해 보세요.
        </p>
      </section>
    );
  }

  return (
    <section
      className={
        isFullscreen
          ? "fixed inset-0 z-[100] w-full h-full flex flex-col bg-surface-container-lowest"
          : "w-[55%] flex flex-col bg-surface-container-lowest overflow-hidden"
      }
    >
      {/* Viewer Toolbar */}
      <div className="h-14 bg-surface-container-high border-b border-outline-variant flex items-center justify-between px-md shrink-0 gap-md">
        <div className="flex items-center gap-md min-w-0">
          <span className="material-symbols-outlined text-secondary shrink-0">picture_as_pdf</span>
          <span className="font-body-sm text-on-surface font-semibold truncate" title={fileName ?? ""}>
            {fileName}
          </span>
        </div>
        <div className="flex items-center gap-lg bg-background/50 rounded-lg px-md py-1 border border-outline-variant shrink-0">
          <div className="flex items-center gap-sm">
            <button
              onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(1)))}
              className="text-on-surface-variant hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-[18px]">remove</span>
            </button>
            <span className="font-data-mono text-data-mono text-on-surface w-10 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(2.5, +(z + 0.1).toFixed(1)))}
              className="text-on-surface-variant hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
            </button>
          </div>
          <div className="h-4 w-px bg-outline-variant" />
          <div className="flex items-center gap-sm">
            <button
              onClick={() => onPageNumberChange(Math.max(1, pageNumber - 1))}
              disabled={pageNumber <= 1}
              className="text-on-surface-variant hover:text-on-surface disabled:opacity-30"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_left</span>
            </button>
            <span className="font-data-mono text-data-mono text-on-surface">{pageNumber}</span>
            <span className="text-on-tertiary-container">/</span>
            <span className="text-on-tertiary-container font-data-mono">{numPages || "-"}</span>
            <button
              onClick={() => onPageNumberChange(numPages ? Math.min(numPages, pageNumber + 1) : pageNumber + 1)}
              disabled={numPages > 0 && pageNumber >= numPages}
              className="text-on-surface-variant hover:text-on-surface disabled:opacity-30"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_right</span>
            </button>
          </div>
        </div>
        <div className="flex items-center gap-sm shrink-0">
          <button
            onClick={() => setPanMode((v) => !v)}
            className={
              "flex items-center justify-center w-8 h-8 rounded transition-colors " +
              (panMode
                ? "bg-secondary-container text-on-secondary-container"
                : "text-on-surface-variant hover:text-secondary hover:bg-surface-container-highest")
            }
            title={panMode ? "이동(손 도구) 끄기" : "이동(손 도구) 켜기 — 드래그로 화면 이동"}
          >
            <span className="material-symbols-outlined text-[20px]">back_hand</span>
          </button>
          <button
            onClick={() => setIsFullscreen((v) => !v)}
            className="text-on-surface-variant hover:text-secondary"
            title={isFullscreen ? "전체화면 종료 (Esc)" : "전체화면으로 보기"}
          >
            <span className="material-symbols-outlined">
              {isFullscreen ? "fullscreen_exit" : "fullscreen"}
            </span>
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Related sources sidebar */}
        {(sources.length > 0 || tagMatches.length > 0) && (
          <aside className="w-44 bg-surface-container border-r border-outline-variant flex flex-col p-sm custom-scrollbar overflow-y-auto gap-md shrink-0">
            {tagMatches.length > 0 && (
              <div className="space-y-sm">
                <h4 className="font-label-caps text-label-caps text-on-tertiary-container uppercase px-1 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px] text-secondary">verified</span>
                  정확 일치
                </h4>
                {tagMatches.map((m, i) => {
                  const active = m.file_name === fileName && m.page_number === pageNumber;
                  return (
                    <button
                      key={`${m.file_name}-${m.page_number}-${i}`}
                      onClick={() => onTagMatchSelect(m)}
                      className={
                        "w-full text-left industrial-border rounded p-sm transition-colors " +
                        (active ? "border-secondary bg-surface-container-high" : "hover:bg-surface-container-high")
                      }
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-label-caps text-label-caps text-secondary">
                          &quot;{m.tag}&quot;
                        </span>
                      </div>
                      <p className="text-[10px] text-on-surface">Page {m.page_number}</p>
                      <p className="text-[10px] text-on-tertiary-container truncate" title={m.file_name}>
                        {m.file_name}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}

            {sources.length > 0 && (
              <div className="space-y-sm">
                <h4 className="font-label-caps text-label-caps text-on-tertiary-container uppercase px-1">
                  Related Pages
                </h4>
                {sources.map((source) => {
                  const active = source.file_name === fileName && source.page_number === pageNumber;
                  return (
                    <button
                      key={source.chunk_id}
                      onClick={() => onSourceSelect(source)}
                      className={
                        "w-full text-left industrial-border rounded p-sm transition-colors " +
                        (active ? "border-secondary bg-surface-container-high" : "hover:bg-surface-container-high")
                      }
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-label-caps text-label-caps text-secondary">
                          PAGE {source.page_number}
                        </span>
                        <span className="text-[9px] bg-secondary/10 text-secondary px-1 rounded">
                          {source.similarity}%
                        </span>
                      </div>
                      <p className="text-[10px] text-on-tertiary-container truncate" title={source.file_name}>
                        {source.file_name}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </aside>
        )}

        {/* Main PDF Canvas */}
        <div
          ref={containerRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          className={
            "flex-1 bg-surface-container-lowest p-xl overflow-auto custom-scrollbar flex justify-center " +
            (panMode ? (isDragging ? "cursor-grabbing select-none" : "cursor-grab") : "")
          }
        >
          {loadError ? (
            <div className="text-error self-start">{loadError}</div>
          ) : (
            <div className="industrial-border bg-white shadow-lg p-md h-fit">
              <div className="relative inline-block leading-[0]">
                <Document
                  file={fileUrl}
                  onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                  onLoadError={(err) => setLoadError(`PDF를 불러오지 못했습니다: ${err.message}`)}
                  loading={<div className="text-on-tertiary-container p-lg">PDF 로딩 중...</div>}
                >
                  <Page pageNumber={pageNumber} width={renderedWidth} />
                </Document>
                {currentPageMatches.map((match, mi) => {
                  const scale = renderedWidth / match.page_width;
                  return match.rects.map((rect, ri) => {
                    const [x0, y0, x1, y1] = rect;
                    return (
                      <div
                        key={`${mi}-${ri}`}
                        className="absolute border-2 border-error bg-error/10 pointer-events-none rounded-sm"
                        style={{
                          left: x0 * scale,
                          top: y0 * scale,
                          width: Math.max((x1 - x0) * scale, 4),
                          height: Math.max((y1 - y0) * scale, 4),
                          boxShadow: "0 0 0 2px rgba(229,57,53,0.25)",
                        }}
                        title={`"${match.tag}" 발견 위치`}
                      />
                    );
                  });
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
