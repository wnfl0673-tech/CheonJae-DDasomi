"use client";

import { DragEvent, useEffect, useState } from "react";
import {
  deleteDocument,
  deleteFaultCaseFile,
  listDocuments,
  listFaultCaseFiles,
  uploadDocuments,
  uploadFaultCaseFiles,
} from "@/lib/api";
import { DocumentFileInfo, FaultCaseFileInfo } from "@/types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function sourceTypeLabel(type: FaultCaseFileInfo["source_type"]): string {
  if (type === "pdf") return "PDF";
  if (type === "hwp") return "HWP";
  return "엑셀";
}

interface UploadDropZoneProps {
  accept: string;
  uploading: boolean;
  label: string;
  onFilesSelected: (files: FileList | null) => void;
}

function UploadDropZone({ accept, uploading, label, onFilesSelected }: UploadDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  function handleDragOver(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    if (!uploading) setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setIsDragging(false);
    if (!uploading) onFilesSelected(e.dataTransfer.files);
  }

  return (
    <label
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={
        "industrial-border rounded-lg p-lg flex items-center justify-center gap-sm cursor-pointer transition-colors border-dashed " +
        (isDragging
          ? "bg-secondary-container border-secondary"
          : "bg-surface-container-low hover:bg-surface-container-high")
      }
    >
      <span className="material-symbols-outlined text-secondary">upload_file</span>
      <span className="font-body-sm text-on-surface">{uploading ? "업로드 중..." : label}</span>
      <input
        type="file"
        accept={accept}
        multiple
        disabled={uploading}
        className="hidden"
        onChange={(e) => {
          const fileList = e.target.files;
          onFilesSelected(fileList);
          e.target.value = "";
        }}
      />
    </label>
  );
}

interface DocumentSectionProps {
  title: string;
  description: string;
  accept: string;
}

function DocumentSection({ title, description, accept }: DocumentSectionProps) {
  const [files, setFiles] = useState<DocumentFileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    setLoading(true);
    listDocuments()
      .then(setFiles)
      .catch((err) => setMessage(err instanceof Error ? err.message : "목록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleFilesSelected(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setMessage(null);
    try {
      const result = await uploadDocuments(Array.from(fileList));
      setMessage(result.message);
      load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "업로드에 실패했습니다.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(fileName: string) {
    if (!confirm(`"${fileName}" 파일을 삭제할까요? 인덱싱된 내용도 함께 제거됩니다.`)) return;
    try {
      await deleteDocument(fileName);
      setFiles((prev) => prev.filter((f) => f.file_name !== fileName));
    } catch {
      alert("삭제에 실패했습니다.");
    }
  }

  return (
    <section className="space-y-sm">
      <div>
        <h3 className="font-headline-md text-headline-md text-on-surface">{title}</h3>
        <p className="text-body-sm text-on-tertiary-container mt-0.5">{description}</p>
      </div>

      <UploadDropZone
        accept={accept}
        uploading={uploading}
        label="파일 선택 또는 여러 개 드래그해서 업로드"
        onFilesSelected={handleFilesSelected}
      />

      {message && <p className="text-body-sm text-on-tertiary-container">{message}</p>}

      <div className="space-y-xs">
        {loading ? (
          <p className="text-body-sm text-on-tertiary-container">불러오는 중...</p>
        ) : files.length === 0 ? (
          <p className="text-body-sm text-on-tertiary-container">업로드된 파일이 없습니다.</p>
        ) : (
          files.map((f) => (
            <div
              key={f.file_name}
              className="industrial-border bg-surface-container p-sm rounded flex items-center justify-between gap-sm group"
            >
              <div className="flex items-center gap-sm min-w-0">
                <span className="material-symbols-outlined text-secondary shrink-0">description</span>
                <div className="min-w-0">
                  <p className="font-body-sm text-on-surface truncate">{f.file_name}</p>
                  <p className="text-[11px] text-on-tertiary-container">
                    {formatSize(f.size_bytes)} · {f.chunks}청크 / {f.pages}페이지
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(f.file_name)}
                className="material-symbols-outlined text-on-tertiary-container hover:text-error opacity-0 group-hover:opacity-100 transition-opacity shrink-0 text-[20px]"
                title="삭제"
              >
                delete
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function FaultCaseSection() {
  const [files, setFiles] = useState<FaultCaseFileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    setLoading(true);
    listFaultCaseFiles()
      .then(setFiles)
      .catch((err) => setMessage(err instanceof Error ? err.message : "목록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleFilesSelected(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setMessage(null);
    try {
      const result = await uploadFaultCaseFiles(Array.from(fileList));
      setMessage(result.message);
      load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "업로드에 실패했습니다.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(fileName: string) {
    if (!confirm(`"${fileName}" 파일을 삭제할까요? 인덱싱된 고장사례도 함께 제거됩니다.`)) return;
    try {
      await deleteFaultCaseFile(fileName);
      setFiles((prev) => prev.filter((f) => f.file_name !== fileName));
    } catch {
      alert("삭제에 실패했습니다.");
    }
  }

  return (
    <section className="space-y-sm">
      <div>
        <h3 className="font-headline-md text-headline-md text-on-surface">고장사례 (PDF/HWP/엑셀)</h3>
        <p className="text-body-sm text-on-tertiary-container mt-0.5">
          타지사 고장상보/고장속보 및 고장현황 개요 엑셀을 업로드합니다.
        </p>
      </div>

      <UploadDropZone
        accept=".pdf,.hwp,.xlsx"
        uploading={uploading}
        label="파일 선택 또는 여러 개 드래그해서 업로드 (PDF/HWP/XLSX)"
        onFilesSelected={handleFilesSelected}
      />

      {message && <p className="text-body-sm text-on-tertiary-container">{message}</p>}

      <div className="space-y-xs">
        {loading ? (
          <p className="text-body-sm text-on-tertiary-container">불러오는 중...</p>
        ) : files.length === 0 ? (
          <p className="text-body-sm text-on-tertiary-container">업로드된 파일이 없습니다.</p>
        ) : (
          files.map((f) => (
            <div
              key={f.file_name}
              className="industrial-border bg-surface-container p-sm rounded flex items-center justify-between gap-sm group"
            >
              <div className="flex items-center gap-sm min-w-0">
                <span className="material-symbols-outlined text-secondary shrink-0">description</span>
                <div className="min-w-0">
                  <p className="font-body-sm text-on-surface truncate">{f.file_name}</p>
                  <p className="text-[11px] text-on-tertiary-container">
                    {sourceTypeLabel(f.source_type)} · {formatSize(f.size_bytes)} · 사례 {f.case_count}건
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(f.file_name)}
                className="material-symbols-outlined text-on-tertiary-container hover:text-error opacity-0 group-hover:opacity-100 transition-opacity shrink-0 text-[20px]"
                title="삭제"
              >
                delete
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export default function DocManagementPanel() {
  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar max-w-3xl mx-auto w-full p-lg space-y-xl">
      <div>
        <h2 className="font-display-lg text-headline-md text-on-surface mb-1">Doc Management</h2>
        <p className="text-body-sm text-on-tertiary-container">
          문서는 배포 환경에 미리 포함되지 않고, 여기서 업로드한 뒤 챗봇 검색에 즉시 반영됩니다.
        </p>
      </div>

      <DocumentSection
        title="기술문서 (PDF)"
        description="준공도서, 벤더프린트 등 설비 매뉴얼 PDF를 업로드합니다."
        accept=".pdf"
      />

      <FaultCaseSection />
    </div>
  );
}
