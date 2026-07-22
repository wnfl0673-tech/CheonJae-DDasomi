"use client";

import { useEffect, useState } from "react";

const PHASES = [
  "도면을 뒤적이는 중",
  "관련 문서를 대조하는 중",
  "유사 고장사례를 찾는 중",
  "답변을 정리하는 중",
];

export default function DdasomiLoading() {
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhaseIndex((prev) => (prev + 1) % PHASES.length);
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-md bg-surface-container-low industrial-border rounded-xl p-md w-fit ai-glow overflow-hidden">
      <div className="relative w-14 h-14 shrink-0">
        <span className="blueprint-chip blueprint-chip-1" />
        <span className="blueprint-chip blueprint-chip-2" />
        <span className="blueprint-chip blueprint-chip-3" />
        <span className="glint" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/mascot/ddasomi-thinking.png"
          alt="따소미가 도면을 찾는 중"
          className="relative z-10 w-full h-full object-contain ddasomi-scan"
        />
      </div>

      <div className="flex items-center gap-1">
        <span className="font-body-sm text-on-surface-variant">
          따소미가 {PHASES[phaseIndex]}
        </span>
        <span className="flex gap-0.5 text-on-surface-variant ml-1">
          <span className="loading-dot" style={{ animationDelay: "0ms" }} />
          <span className="loading-dot" style={{ animationDelay: "150ms" }} />
          <span className="loading-dot" style={{ animationDelay: "300ms" }} />
        </span>
      </div>
    </div>
  );
}
