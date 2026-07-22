"use client";

import { StatusResponse } from "@/types";

const SUGGESTIONS = [
  {
    icon: "precision_manufacturing",
    label: "Symptom Search",
    text: "PIT-1324 압력전송기 값이 비정상적입니다.",
  },
  {
    icon: "wifi_tethering_error",
    label: "System Alarm",
    text: "DCS에서 통신 Fail Alarm이 발생했습니다.",
  },
  {
    icon: "troubleshoot",
    label: "Data Calibration",
    text: "AI 출력값과 현장 밸브 개도가 일치하지 않습니다.",
  },
];

interface EmptyStateProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  loading: boolean;
  status: StatusResponse | null;
}

export default function EmptyState({ value, onChange, onSend, loading, status }: EmptyStateProps) {
  return (
    <div className="flex-1 flex flex-col relative overflow-hidden">
      <div className="flex-1 flex flex-col items-center justify-center p-md pb-40 max-w-5xl mx-auto w-full overflow-y-auto custom-scrollbar">
        <div className="relative mb-lg">
          <div className="absolute inset-0 bg-secondary opacity-10 blur-3xl rounded-full scale-150" />
          <div className="relative z-10 w-32 h-32 md:w-40 md:h-40 rounded-full bg-surface-container-low industrial-border flex items-center justify-center ai-glow overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/mascot/ddasomi-confident.png"
              alt="따소미"
              className="w-full h-full object-contain p-3"
            />
          </div>
        </div>

        <div className="text-center space-y-md max-w-2xl px-md">
          <h3 className="font-display-lg text-display-lg text-on-surface tracking-tight">
            설비 태그명 또는 고장 증상을 입력해 주세요.
          </h3>
          <p className="font-body-base text-on-surface-variant">
            준공도서 및 벤더프린트 등의 문서를 검색하여 점검 절차를 안내합니다. 문서 근거가 없는 내용은 단정하지
            않으며, 실제 작업 전에는 반드시 작업허가·안전조치·담당자 확인이 필요합니다.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-md w-full mt-xl">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => onChange(s.text)}
              className="group relative p-lg rounded-xl border border-outline-variant bg-surface-container-low hover:bg-surface-container hover:border-secondary/50 transition-all text-left flex flex-col gap-sm overflow-hidden ai-glow"
            >
              <div className="flex items-center gap-sm">
                <span className="material-symbols-outlined text-secondary text-sm">{s.icon}</span>
                <span className="text-[10px] font-label-caps text-secondary uppercase tracking-widest">
                  {s.label}
                </span>
              </div>
              <p className="font-body-sm text-on-surface group-hover:text-secondary-fixed transition-colors">
                &quot;{s.text}&quot;
              </p>
            </button>
          ))}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 p-lg">
        <div className="max-w-4xl mx-auto bg-surface-container/90 backdrop-blur-md border border-outline-variant rounded-xl p-base ai-glow">
          <div className="flex items-end gap-sm p-sm">
            <div className="flex-1 min-h-[44px] bg-surface-container-high rounded-lg px-md py-base border border-outline-variant focus-within:border-secondary/60 transition-colors">
              <textarea
                rows={1}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    onSend();
                  }
                }}
                placeholder="Message Ttasome (태그명, 고장증상)..."
                className="w-full bg-transparent border-none focus:ring-0 text-on-surface placeholder-on-surface-variant/50 resize-none py-sm font-body-base"
              />
            </div>
            <button
              onClick={onSend}
              disabled={loading || !value.trim()}
              className="bg-secondary text-on-secondary w-11 h-11 flex items-center justify-center rounded-lg hover:scale-105 active:scale-95 transition-all shadow-lg shadow-secondary/20 disabled:opacity-40 disabled:hover:scale-100 shrink-0"
            >
              <span className="material-symbols-outlined">arrow_upward</span>
            </button>
          </div>
          <div className="flex justify-between items-center px-md py-xs text-[10px] font-label-caps text-on-tertiary-container">
            <div className="flex gap-md">
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px]">verified</span>
                인덱싱된 청크: {status ? status.total_chunks.toLocaleString() : "-"}개 / 파일{" "}
                {status ? status.total_files.toLocaleString() : "-"}개
              </span>
            </div>
            <span className="uppercase">Standard Operating Procedures Only</span>
          </div>
        </div>
      </div>
    </div>
  );
}
