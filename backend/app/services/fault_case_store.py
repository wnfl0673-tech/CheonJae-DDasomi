"""고장사례 전용 벡터 컬렉션.

기술 도면/매뉴얼(dcs_documents)과는 성격이 다른 데이터(과거 장애 이력)라서
별도 컬렉션으로 분리한다. 임베딩 모델과 ChromaDB 클라이언트는 vector_store와
공유해 리소스를 중복 로드하지 않는다.
"""

from typing import List, Optional

from app.config import settings
from app.services import vector_store
from app.services.fault_case_processor import FaultCase

_collection = None


def get_fault_collection():
    global _collection
    if _collection is None:
        _collection = vector_store.get_client().get_or_create_collection(
            name=settings.fault_case_collection_name,
            embedding_function=vector_store.get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def case_exists(case_id: str) -> bool:
    collection = get_fault_collection()
    existing = collection.get(ids=[case_id])
    return bool(existing["ids"])


def add_fault_cases(cases: List[FaultCase]) -> int:
    if not cases:
        return 0

    collection = get_fault_collection()
    collection.add(
        ids=[c.case_id for c in cases],
        documents=[c.summary for c in cases],
        metadatas=[
            {
                "source_type": c.source_type,
                "site": c.site,
                "equipment_tag": c.equipment_tag,
                "occurrence_date": c.occurrence_date,
                "title": c.title,
                "pdf_path": c.pdf_path or "",
                "source_file": c.source_file,
            }
            for c in cases
        ],
    )
    return len(cases)


def get_stats() -> dict:
    collection = get_fault_collection()
    return {"total_cases": collection.count()}


def count_cases_by_source_file() -> dict:
    """source_file -> 해당 파일에서 만들어진 고장사례 건수. Doc Management 목록 표시용."""
    collection = get_fault_collection()
    if collection.count() == 0:
        return {}

    result = collection.get(include=["metadatas"])
    counts: dict[str, int] = {}
    for meta in result["metadatas"]:
        source_file = (meta or {}).get("source_file")
        if source_file:
            counts[source_file] = counts.get(source_file, 0) + 1
    return counts


def delete_cases_by_source_file(source_file: str) -> None:
    collection = get_fault_collection()
    collection.delete(where={"source_file": source_file})


def query_fault_cases(question: str, top_k: int = 3) -> List[dict]:
    collection = get_fault_collection()
    total = collection.count()
    if total == 0:
        return []

    results = collection.query(query_texts=[question], n_results=min(top_k, total))

    hits: List[dict] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for case_id, summary, meta, distance in zip(ids, documents, metadatas, distances):
        hits.append(
            {
                "case_id": case_id,
                "summary": summary,
                "distance": distance,
                **meta,
            }
        )
    return hits


def get_recent_fault_cases(top_k: int = 3) -> List[dict]:
    """occurrence_date 기준 최신순으로 정렬된 고장사례를 반환한다.

    query_fault_cases()는 질문 텍스트와의 의미 유사도로만 정렬하므로 "최근 고장사례"
    처럼 실제 발생일 순서가 필요한 질문에는 맞지 않는다. 날짜가 비어있는(파싱 실패)
    사례는 최신이 아닌 것으로 간주해 뒤로 보낸다.
    """
    collection = get_fault_collection()
    total = collection.count()
    if total == 0:
        return []

    data = collection.get(include=["documents", "metadatas"])
    ids = data.get("ids", [])
    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])

    combined = [
        {"case_id": case_id, "summary": summary, "distance": 0.0, **meta}
        for case_id, summary, meta in zip(ids, documents, metadatas)
    ]
    combined.sort(key=lambda c: c.get("occurrence_date") or "", reverse=True)
    return combined[:top_k]


def find_pdf_path_for_source_file(root, source_file: str) -> Optional[str]:
    """source_file(파일명)로 실제 경로를 재탐색한다 (재인덱싱 없이 경로만 확인할 때 사용)."""
    for path in root.rglob(source_file):
        return str(path)
    return None
