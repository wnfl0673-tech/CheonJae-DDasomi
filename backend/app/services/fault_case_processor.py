"""타지사 고장사례(고장상보/고장속보 PDF/HWP + 고장현황 엑셀) 처리.

세 종류의 소스를 하나의 공통 구조(FaultCase)로 변환한다.
1. PDF/HWP 고장상보 (예: "0001_ 150310 광교.pdf"): 파일명에서 날짜/지사를 파싱하고,
   본문 텍스트는 라벨 기반 정규식(LLM 미사용, extract_fields_heuristic)으로
   설비/증상/원인/조치 필드를 뽑아낸다(인덱싱 시 1회, 캐시).
2. 엑셀 개요표(고장현황): 이미 컬럼이 정리되어 있어 그대로 매핑한다.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import openpyxl

_DATE_PATTERN = re.compile(r"(\d{6})")

# "최근/최신 고장사례 알려줘"처럼 날짜순 정렬이 필요한 질문을 감지한다.
# 임베딩 유사도 검색은 텍스트 의미만 비교할 뿐 실제 발생일을 모르므로,
# 이 키워드가 있으면 occurrence_date 기준 정렬 결과로 대체해야 한다.
_RECENCY_KEYWORDS = ("최근", "최신", "요즘", "가장 최근", "마지막으로")


def is_recency_query(question: str) -> bool:
    """질문이 '최근/최신' 등 날짜순 정렬을 요구하는지 판단한다."""
    return any(keyword in question for keyword in _RECENCY_KEYWORDS)


@dataclass
class FaultCase:
    case_id: str
    source_type: str  # "pdf" | "hwp" | "excel"
    site: str
    equipment_tag: str
    occurrence_date: str  # YYYY-MM-DD, 파싱 실패 시 빈 문자열
    title: str
    summary: str
    pdf_path: Optional[str]
    source_file: str


def discover_fault_case_pdfs(root: Path) -> List[Path]:
    """폴더 내 모든 고장상보/고장속보 PDF를 재귀적으로 찾는다."""
    if not root.exists():
        return []
    return sorted(root.rglob("*.pdf"))


def discover_fault_case_hwps(root: Path) -> List[Path]:
    """폴더 내 모든 HWP 고장사례 문서를 재귀적으로 찾는다."""
    if not root.exists():
        return []
    return sorted(root.rglob("*.hwp"))


def discover_fault_case_excels(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("*.xlsx"))


def _hwp5txt_executable() -> str:
    """pyhwp가 설치한 hwp5txt CLI 경로를 같은 venv의 Scripts/bin 폴더에서 찾는다."""
    scripts_dir = Path(sys.executable).parent
    candidate = scripts_dir / ("hwp5txt.exe" if sys.platform == "win32" else "hwp5txt")
    return str(candidate) if candidate.exists() else "hwp5txt"


def extract_hwp_text(hwp_path: Path) -> str:
    """HWP5 파일에서 텍스트를 추출한다 (pyhwp의 hwp5txt CLI 사용)."""
    result = subprocess.run(
        [_hwp5txt_executable(), str(hwp_path)],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"HWP 텍스트 추출 실패: {stderr[:300]}")
    return result.stdout.decode("utf-8", errors="replace")


def parse_date_from_filename(name: str) -> str:
    """'0001_ 150310 광교.pdf' 같은 파일명에서 YYMMDD를 찾아 YYYY-MM-DD로 변환한다."""
    match = _DATE_PATTERN.search(Path(name).stem)
    if not match:
        return ""
    yymmdd = match.group(1)
    yy, mm, dd = int(yymmdd[0:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return ""
    year = 2000 + yy
    return f"{year:04d}-{mm:02d}-{dd:02d}"


def parse_site_from_filename(name: str) -> str:
    """파일명 끝의 지사명 토큰을 추출한다 (예: '0001_ 150310 광교.pdf' -> '광교')."""
    stem = Path(name).stem
    tokens = [t for t in re.split(r"[_\s()]+", stem) if t]
    for token in reversed(tokens):
        if not token.isdigit() and not _DATE_PATTERN.fullmatch(token):
            return token
    return ""


def load_excel_records(xlsx_path: Path) -> List[dict]:
    """고장현황 overview 엑셀을 읽어 행(row) 단위 dict 목록으로 변환한다.

    헤더: 지사, 열공급시설, 보고유형, 고장제목, 고장분야, 고장설비, 고장기기명,
    상태, 발생일, 조치완료일, 고장내용, 결재진행
    """
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    sheet = wb.worksheets[0]

    rows_iter = sheet.iter_rows(values_only=True)
    header = [str(h).strip() if h else "" for h in next(rows_iter)]

    records = []
    last_site = ""
    for idx, row in enumerate(rows_iter, start=2):
        row_dict = dict(zip(header, row))
        site = str(row_dict.get("지사") or "").strip() or last_site
        last_site = site or last_site

        title = str(row_dict.get("고장제목") or "").strip()
        if not title and not row_dict.get("고장내용"):
            continue  # 완전히 빈 행은 건너뛴다

        occurrence = row_dict.get("발생일")
        occurrence_str = _format_excel_date(occurrence)

        records.append(
            {
                "row_index": idx,
                "site": site,
                "facility": str(row_dict.get("열공급시설") or "").strip(),
                "title": title,
                "category": str(row_dict.get("고장분야") or "").strip(),
                "equipment": str(row_dict.get("고장설비") or "").strip(),
                "equipment_tag": str(row_dict.get("고장기기명") or "").strip(),
                "status": str(row_dict.get("상태") or "").strip(),
                "occurrence_date": occurrence_str,
                "resolution_date": _format_excel_date(row_dict.get("조치완료일")),
                "description": str(row_dict.get("고장내용") or "").strip(),
            }
        )

    wb.close()
    return records


def _format_excel_date(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


# ---------------------------------------------------------------------------
# 고장상보 PDF/HWP 필드 추출 (라벨 기반 정규식, LLM/외부 API 미사용)
# ---------------------------------------------------------------------------

# 우선순위 순서로 나열: 더 구체적인 라벨을 먼저 시도해야 "설비" vs "설비명" 같은
# 부분 문자열 충돌을 피할 수 있다.
_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "equipment_tag": ("고장기기명", "기기명", "설비명", "대상설비", "설비"),
    "symptom": ("고장현상", "발생현상", "현상", "증상"),
    "cause": ("고장원인", "발생원인", "원인"),
    "action_taken": ("조치사항", "복구조치", "응급조치", "조치"),
}
_ALL_LABELS = [label for labels in _FIELD_LABELS.values() for label in labels]
_FIELD_VALUE_MAX_LEN = 300


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str:
    """'라벨: 내용' 형태에서 다음 라벨이 나오기 전까지의 내용을 추출한다.

    콜론이 바로 붙어있는 경우만 매칭한다(예: "설비: XXX"). 문서 형식이 일정하지
    않아 콜론 없이 쓰인 라벨은 잡아내지 못하는 한계가 있다.
    """
    for label in labels:
        other_labels = sorted((l for l in _ALL_LABELS if l != label), key=len, reverse=True)
        lookahead = "|".join(re.escape(l) for l in other_labels)
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:：]\s*(.*?)(?=(?:{lookahead})\s*[:：]|\Z)",
            re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip(" .")
            if value:
                return value[:_FIELD_VALUE_MAX_LEN]
    return ""


def extract_fields_heuristic(raw_text: str) -> dict:
    """LLM 없이 라벨 기반 정규식으로 고장상보 문서의 핵심 필드를 추출한다.

    문서 형식이 일정하지 않아 LLM 대비 추출 품질은 낮을 수 있으나, 보안 정책상
    외부 API를 호출할 수 없어 텍스트 원문의 라벨 매칭으로 대체한다. 라벨을 찾지
    못한 필드는 빈 문자열로 남긴다(추측해서 채우지 않음).
    """
    first_line = next((line.strip() for line in raw_text.splitlines() if line.strip()), "")
    return {
        "title": first_line[:80],
        "equipment_tag": _extract_labeled_value(raw_text, _FIELD_LABELS["equipment_tag"]),
        "symptom": _extract_labeled_value(raw_text, _FIELD_LABELS["symptom"]),
        "cause": _extract_labeled_value(raw_text, _FIELD_LABELS["cause"]),
        "action_taken": _extract_labeled_value(raw_text, _FIELD_LABELS["action_taken"]),
    }
