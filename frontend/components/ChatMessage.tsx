"use client";

import { getFaultCaseExcelUrl, getFaultCaseHwpUrl } from "@/lib/api";
import { ChatMessageData, FaultCaseMatch, SourceItem, TagMatch } from "@/types";

interface ChatMessageProps {
  message: ChatMessageData;
  onSourceClick: (source: SourceItem) => void;
  onTagMatchClick: (match: TagMatch) => void;
  onFaultCaseOpen: (match: FaultCaseMatch) => void;
}

function splitLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.replace(/^[\s\-*•]+|^\d+[.).]\s*/, "").trim())
    .filter(Boolean);
}

function BulletList({ title, text, icon }: { title: string; text: string; icon: string }) {
  const lines = splitLines(text);
  if (lines.length === 0) return null;
  return (
    <div className="space-y-sm">
      <h3 className="font-label-caps text-label-caps text-on-tertiary-container uppercase">{title}</h3>
      <div className="space-y-xs">
        {lines.map((line, i) => (
          <div key={i} className="flex items-start gap-sm bg-surface-container p-2 rounded industrial-border">
            <span className="material-symbols-outlined text-secondary text-[16px] mt-0.5 shrink-0">{icon}</span>
            <span className="flex-1 font-body-sm text-on-surface">{line}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ChatMessage({ message, onSourceClick, onTagMatchClick, onFaultCaseOpen }: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex flex-col items-end">
        <div className="bg-primary-container industrial-border rounded-xl p-md max-w-[85%]">
          <p className="text-on-surface font-body-base whitespace-pre-wrap">{message.question}</p>
        </div>
      </div>
    );
  }

  if (message.error) {
    return (
      <div className="flex flex-col items-start">
        <div className="max-w-[95%] bg-error-container border border-error/40 rounded-xl p-md flex gap-md">
          <span className="material-symbols-outlined text-error">error</span>
          <p className="text-body-sm text-on-error-container whitespace-pre-wrap">{message.error}</p>
        </div>
      </div>
    );
  }

  const response = message.response;
  if (!response) return null;

  const {
    answer_sections: sections,
    sources,
    has_document_evidence,
    exact_tag_matches: tagMatches,
    similar_fault_cases: faultCases,
  } = response;
  const uniquePages = new Set(sources.map((s) => `${s.file_name}::${s.page_number}`)).size;

  return (
    <div className="flex flex-col items-start w-full">
      <div className="bg-surface-container-low industrial-border rounded-xl p-md w-full ai-glow space-y-md">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-sm">
          <div className="flex items-center gap-sm">
            <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-on-secondary-container text-[18px]">manage_search</span>
            </div>
            <span className="font-headline-md text-headline-md text-on-surface">검색 완료</span>
          </div>
          <div className="flex gap-sm">
            <span className="bg-surface-container-highest text-on-surface-variant font-label-caps text-label-caps px-sm py-1 rounded">
              {sources.length} Docs
            </span>
            <span className="bg-surface-container-highest text-on-surface-variant font-label-caps text-label-caps px-sm py-1 rounded">
              {uniquePages} Pages
            </span>
          </div>
        </div>

        {/* Exact tag match results (Ctrl+F style) */}
        {tagMatches.length > 0 && (
          <div className="space-y-sm bg-secondary/5 border border-secondary/30 rounded-lg p-sm">
            <h3 className="font-label-caps text-label-caps text-secondary uppercase flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">verified</span>
              태그 정확 일치 검색 결과 (전체 문서 대상)
            </h3>
            <div className="grid grid-cols-1 gap-xs">
              {tagMatches.map((m, i) => (
                <button
                  key={`${m.file_name}-${m.page_number}-${i}`}
                  onClick={() => onTagMatchClick(m)}
                  className="industrial-border bg-surface-container p-sm rounded flex items-center justify-between hover:bg-surface-container-high cursor-pointer transition-colors text-left"
                >
                  <div className="flex items-center gap-sm min-w-0">
                    <span className="material-symbols-outlined text-secondary shrink-0 text-[18px]">description</span>
                    <span className="font-body-sm text-on-surface truncate">{m.file_name}</span>
                  </div>
                  <div className="flex items-center gap-sm shrink-0">
                    <span className="bg-secondary/10 text-secondary font-label-caps text-label-caps px-sm py-0.5 rounded">
                      &quot;{m.tag}&quot;
                    </span>
                    <span className="font-label-caps text-label-caps text-on-tertiary-container">
                      Page {m.page_number}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Similar past fault cases from other branches */}
        {faultCases.length > 0 && (
          <div className="space-y-sm bg-primary-container/60 border border-secondary/30 rounded-lg p-sm">
            <h3 className="font-label-caps text-label-caps text-secondary uppercase flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">history</span>
              과거 유사 고장사례
            </h3>
            <div className="grid grid-cols-1 gap-sm">
              {faultCases.map((fc) => (
                <div key={fc.case_id} className="industrial-border bg-surface-container p-sm rounded space-y-1">
                  <div className="flex items-center justify-between gap-sm flex-wrap">
                    <span className="font-body-sm font-semibold text-on-surface">
                      {fc.occurrence_date || "날짜 미상"} · {fc.site || "지사 미상"}
                    </span>
                    <span className="bg-secondary/10 text-secondary font-label-caps text-label-caps px-sm py-0.5 rounded">
                      유사도 {fc.similarity}%
                    </span>
                  </div>
                  <p className="font-body-sm text-on-surface">{fc.title}</p>
                  <p className="text-[11px] text-on-tertiary-container line-clamp-2">{fc.summary}</p>
                  {fc.document_type === "pdf" ? (
                    <button
                      onClick={() => onFaultCaseOpen(fc)}
                      className="mt-1 text-[11px] text-secondary hover:underline flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-[14px]">description</span>
                      관련 문서 읽어보기
                    </button>
                  ) : fc.document_type === "hwp" ? (
                    <a
                      href={getFaultCaseHwpUrl(fc.source_file)}
                      download={fc.source_file}
                      className="mt-1 text-[11px] text-secondary hover:underline flex items-center gap-1 w-fit"
                    >
                      <span className="material-symbols-outlined text-[14px]">download</span>
                      원본 파일 다운로드 (HWP)
                    </a>
                  ) : fc.document_type === "excel" ? (
                    <a
                      href={getFaultCaseExcelUrl(fc.source_file)}
                      download={fc.source_file}
                      className="mt-1 text-[11px] text-secondary hover:underline flex items-center gap-1 w-fit"
                    >
                      <span className="material-symbols-outlined text-[14px]">download</span>
                      근거 파일 다운로드 (고장현황 엑셀)
                    </a>
                  ) : (
                    <p className="mt-1 text-[11px] text-on-tertiary-container italic">
                      (요약 정보만 있고 원본 문서는 없습니다)
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Related Documents */}
        <div className="space-y-sm">
          <h3 className="font-label-caps text-label-caps text-on-tertiary-container uppercase">
            Related Documents
          </h3>
          {sources.length > 0 ? (
            <div className="grid grid-cols-1 gap-sm">
              {sources.map((source) => (
                <button
                  key={source.chunk_id}
                  onClick={() => onSourceClick(source)}
                  className="industrial-border bg-surface-container p-sm rounded flex items-center justify-between hover:bg-surface-container-high cursor-pointer transition-colors text-left"
                  title={source.snippet}
                >
                  <div className="flex items-center gap-sm min-w-0">
                    <span className="material-symbols-outlined text-secondary shrink-0">description</span>
                    <span className="font-body-sm text-on-surface truncate">{source.file_name}</span>
                  </div>
                  <div className="flex items-center gap-sm shrink-0">
                    <span className="bg-secondary/10 text-secondary font-label-caps text-label-caps px-sm py-0.5 rounded">
                      {source.similarity}%
                    </span>
                    <span className="font-label-caps text-label-caps text-on-tertiary-container">
                      Page {source.page_number}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-body-sm text-on-tertiary-container">관련성이 높은 문서를 찾지 못했습니다.</p>
          )}
        </div>

        {/* Maintenance actions */}
        <BulletList title="유지보수 조치사항" text={sections.maintenance_actions} icon="build" />

        {/* Possible causes */}
        <BulletList title="가능한 원인" text={sections.possible_causes} icon="troubleshoot" />

        {/* General recommendations (optional) */}
        {sections.general_recommendations && (
          <BulletList title="일반 점검 권고사항" text={sections.general_recommendations} icon="lightbulb" />
        )}

        {/* Safety warning */}
        <div className="bg-error-container border border-error/40 p-md rounded-lg flex gap-md">
          <span className="material-symbols-outlined text-error">warning</span>
          <div>
            <h4 className="font-label-caps text-label-caps text-error mb-1">주의사항</h4>
            <p className="text-body-sm text-on-error-container whitespace-pre-wrap">{sections.precautions}</p>
          </div>
        </div>

        {!has_document_evidence && (
          <p className="text-[10px] text-on-tertiary-container italic">
            * 관련성이 높은 문서를 찾지 못했습니다. 검색어를 조정하거나 담당자에게 확인해 주세요.
          </p>
        )}
      </div>
    </div>
  );
}
