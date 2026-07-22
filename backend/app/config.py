from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    top_k_results: int = 5
    frontend_origin: str = "http://localhost:3000"

    # PDF / 벡터DB 저장 경로 (docker/배포 환경에서도 상대경로로 동작)
    documents_dir: Path = BACKEND_DIR / "documents"
    chroma_dir: Path = BACKEND_DIR / "chroma_db"
    history_db_path: Path = BACKEND_DIR / "chat_history.db"

    # 타지사 고장사례 원본 폴더 (PDF/HWP/엑셀). 배포 환경에서도 그대로 동작하도록
    # 레포 상대경로를 기본값으로 쓰고, 필요하면 .env의 FAULT_CASE_DIR로 덮어쓴다.
    fault_case_dir: Path = BACKEND_DIR / "fault_cases"
    fault_case_collection_name: str = "fault_cases"

    # 청크 분할 설정 (1GB급 문서 확장 시에도 그대로 사용)
    chunk_size: int = 800
    chunk_overlap: int = 150

    # 임베딩 모델 (한국어를 포함한 다국어 지원)
    embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"

    collection_name: str = "dcs_documents"

    # Doc Management 탭에서 업로드 가능한 파일 1개당 최대 용량
    max_upload_size_mb: int = 100


settings = Settings()

settings.documents_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
settings.fault_case_dir.mkdir(parents=True, exist_ok=True)
