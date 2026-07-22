"""ChromaDB 기반 벡터스토어 래퍼.

MVP에서는 PersistentClient(로컬 디스크)를 사용한다. 1GB급으로 문서량이
늘어나면 chromadb의 HttpClient(서버 모드)로 교체해도 이 모듈의 인터페이스
(add_chunks/query/is_file_up_to_date)는 그대로 유지할 수 있도록 설계했다.
"""

import gc
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings
from app.services.pdf_processor import Chunk

_client = None
_collection = None
_embedding_fn = None


def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model_name,
            # newer transformers versions default to meta-device "fast init", which crashes
            # (NotImplementedError: Cannot copy out of meta tensor) with this sentence-transformers
            # version on some machines. Forcing normal (non-meta) weight loading avoids it.
            model_kwargs={"low_cpu_mem_usage": False},
        )
    return _embedding_fn


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return _client


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_client().get_or_create_collection(
            name=settings.collection_name,
            embedding_function=get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def is_file_up_to_date(file_name: str, file_hash: str) -> bool:
    """이미 동일한 해시로 인덱싱된 파일인지 확인 (증분 인덱싱용)."""
    collection = get_collection()
    existing = collection.get(where={"file_name": file_name}, limit=1)
    if not existing["ids"]:
        return False
    existing_hash = existing["metadatas"][0].get("file_hash")
    return existing_hash == file_hash


def delete_file_chunks(file_name: str) -> None:
    collection = get_collection()
    collection.delete(where={"file_name": file_name})


# ChromaDB(Rust 백엔드)는 한 번의 add() 호출에 담을 수 있는 항목 수 제한이 있다.
# 1GB급 문서에서는 파일 하나가 수천 개 청크를 만들 수 있으므로 배치로 나눠 추가한다.
# add() 호출마다 임베딩 함수가 배치 전체를 한 번에 인코딩하므로, 배치 크기가 크면
# 메모리가 제한된 배포 환경(예: RAM 1GB)에서 OOM으로 죽을 수 있다. 200으로도 부족해서
# 훨씬 작게 잡고, 배치 사이마다 gc.collect()로 파이썬이 메모리를 계속 누적 보유하지
# 않도록 강제한다.
MAX_ADD_BATCH_SIZE = 20


def add_chunks(chunks: List[Chunk], file_hash: str) -> int:
    if not chunks:
        return 0

    collection = get_collection()

    for start in range(0, len(chunks), MAX_ADD_BATCH_SIZE):
        batch = chunks[start : start + MAX_ADD_BATCH_SIZE]
        collection.add(
            ids=[c.chunk_id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[
                {
                    "file_name": c.file_name,
                    "page_number": c.page_number,
                    "pdf_path": c.pdf_path,
                    "file_hash": file_hash,
                }
                for c in batch
            ],
        )
        gc.collect()
    return len(chunks)


def list_indexed_files() -> dict:
    """file_name -> {"chunks": int, "pages": int} 매핑. Doc Management 목록 표시용."""
    collection = get_collection()
    if collection.count() == 0:
        return {}

    result = collection.get(include=["metadatas"])
    per_file: dict[str, dict] = {}
    for meta in result["metadatas"]:
        if not meta or not meta.get("file_name"):
            continue
        name = meta["file_name"]
        entry = per_file.setdefault(name, {"chunks": 0, "pages": set()})
        entry["chunks"] += 1
        entry["pages"].add(meta.get("page_number"))

    return {name: {"chunks": info["chunks"], "pages": len(info["pages"])} for name, info in per_file.items()}


def get_stats() -> dict:
    """실제 인덱싱 현황(총 청크 수/파일 수)을 반환한다. 프론트엔드에 가짜 통계 대신 표시하는 용도."""
    collection = get_collection()
    total_chunks = collection.count()

    file_names: set[str] = set()
    if total_chunks:
        result = collection.get(include=["metadatas"])
        for meta in result["metadatas"]:
            if meta and meta.get("file_name"):
                file_names.add(meta["file_name"])

    return {"total_chunks": total_chunks, "total_files": len(file_names)}


def query(question: str, top_k: Optional[int] = None) -> List[dict]:
    collection = get_collection()
    k = top_k or settings.top_k_results

    results = collection.query(query_texts=[question], n_results=k)

    hits: List[dict] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for chunk_id, text, meta, distance in zip(ids, documents, metadatas, distances):
        hits.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "file_name": meta.get("file_name"),
                "page_number": meta.get("page_number"),
                "pdf_path": meta.get("pdf_path"),
                "distance": distance,
            }
        )
    return hits
