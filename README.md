# 천재따소미 (Cheonjae-Ddasomi)

발전소 전산/DCS 유지보수 인원을 위한 검색 기반 챗봇 MVP.
태그명이나 고장 증상을 입력하면 사전에 적재한 PDF 준공도서/벤더프린트에서 관련 페이지를 검색해
근거 문서(파일명·페이지 번호)와 발췌 원문을 그대로 보여준다.

> **보안성 검토 결과에 따라 외부 LLM API는 사용하지 않는다.** 답변은 벡터/텍스트 검색 결과를
> 그대로 정리해서 보여주는 방식이며, AI가 내용을 요약·생성·추론하지 않는다.

## ⚠️ 보안 안내: 원본 문서는 GitHub에 올라가지 않음

`backend/documents/`, `backend/fault_cases/`에 들어가는 준공도서·고장사례 원본은 회사 기밀문서이므로
`.gitignore`에서 제외되어 있다. 이 저장소를 클론해도 두 폴더는 비어 있으며(서버 최초 실행 시 빈 폴더가
자동 생성됨), 아래 항목들도 같은 이유로 git에 포함되지 않는다.

- `backend/documents/*.pdf`, `backend/fault_cases/*` — 원본 문서
- `backend/chroma_db/` — 위 문서를 임베딩한 벡터DB (문서 원문 청크가 그대로 들어있음)
- `backend/chat_history.db` — 챗봇이 답변하며 인용한 문서 원문이 남아있는 대화 이력
- `backend/.env` — 로컬 환경설정 (현재는 API 키를 포함하지 않음, 아래 "보안 안내" 참고)

로컬에서 실제 문서로 챗봇을 돌려보려면, 원본 문서를 **사내 채널(드라이브/메신저 등)로 별도 전달받아**
`backend/documents/`, `backend/fault_cases/`에 직접 넣어야 한다 (1-3, 1-3-2 참고).

## 아키텍처 요약

```
사용자 질문
   │
   ▼
[FastAPI /api/chat] → ChromaDB 벡터 검색 (관련 PDF 청크) + 태그 정확 일치 검색(Ctrl+F 방식)
   │
   ▼
answer_builder.py: 검색 결과를 그대로 정리 (LLM 미사용, 요약/생성 없음)
   │
   ▼
프론트엔드: 좌측 챗봇 / 우측 PDF 미리보기(react-pdf)
```

- PDF 적재: `backend/documents/*.pdf`
- 텍스트 추출: PyMuPDF (페이지 단위)
- 청크 분할: 페이지 텍스트를 800자 단위(150자 오버랩)로 슬라이딩 윈도우 분할
- 임베딩/저장: ChromaDB (`sentence-transformers` 다국어 모델로 로컬에서 임베딩, 로컬 디스크에 영속 — 외부 API 호출 없음)
- 답변 구성: `answer_builder.py`가 검색된 발췌/태그 일치 결과를 정리해서 반환 (LLM/외부 API 미사용)
- 고장사례 필드(설비/증상/원인/조치) 추출: `fault_case_processor.extract_fields_heuristic`이 라벨 기반 정규식으로 처리 (LLM 미사용)

## 폴더 구조

```
cheonjae-ddasomi/
├── backend/            # FastAPI 서버
│   ├── documents/      # 여기에 준공도서 PDF를 넣는다 (git 제외, 사내 채널로 전달받음)
│   ├── fault_cases/    # 여기에 고장사례 PDF/HWP/엑셀을 넣는다 (git 제외, 사내 채널로 전달받음)
│   ├── chroma_db/      # 벡터DB 저장소 (자동 생성, git 제외)
│   └── app/
├── frontend/           # Next.js 앱
└── README.md
```

## 1. 백엔드 실행

요구사항: Python 3.10 이상 (Windows에는 기본 설치되어 있지 않은 경우가 많으니
[python.org](https://www.python.org/downloads/)에서 설치 후 진행).

### 1-1. 가상환경 및 패키지 설치

```powershell
cd cheonjae-ddasomi/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 1-2. 환경변수 설정

`backend/.env.example`을 복사해 `backend/.env`를 만든다 (LLM API 키는 사용하지 않으므로 채울 필요 없음).

```powershell
copy .env.example .env
```

```
TOP_K_RESULTS=5
FRONTEND_ORIGIN=http://localhost:3000
```

### 1-3. 원본 문서 넣기

사내 채널로 전달받은 원본 문서를 아래 폴더에 넣는다 (git에는 포함되어 있지 않음 — 위 "보안 안내" 참고).

- `backend/documents/` — 준공도서/벤더프린트 PDF
- `backend/fault_cases/` — 고장사례 PDF/HWP/엑셀 (연도별 하위 폴더 구조 유지)

### 1-4. 서버 실행

```powershell
uvicorn app.main:app --reload --port 8000
```

### 1-5. 문서 인덱싱

서버가 뜨면 아래 중 하나로 인덱싱을 실행한다 (프론트엔드의 "문서 인덱싱" 버튼으로도 가능).

```powershell
curl -X POST http://localhost:8000/api/index
```

이미 인덱싱된(내용이 바뀌지 않은) 파일은 자동으로 스킵되므로, 이후 PDF를 추가할 때마다
같은 명령을 다시 호출하면 새 파일만 증분 인덱싱된다.

`backend/fault_cases/`에 파일을 넣었다면 고장사례도 별도로 인덱싱한다 (프론트엔드의
"고장사례 인덱싱" 버튼으로도 가능).

```powershell
curl -X POST http://localhost:8000/api/index-fault-cases
```

## 2. 프론트엔드 실행

```powershell
cd cheonjae-ddasomi/frontend
copy .env.local.example .env.local
npm install
npm run dev
```

브라우저에서 `http://localhost:3000` 접속.

## 3. 사용 방법

1. "문서 인덱싱" 버튼 클릭 (최초 1회, 또는 PDF 추가 후)
2. 좌측 채팅창에 태그명(예: `PIT-7610`) 또는 고장 증상(예: `유량 전송기 신호 튐`) 입력
3. 답변 카드에서 "관련 문서" 배지를 클릭하면 우측에 해당 PDF 페이지가 열림
4. "문서 기반 확인사항"에는 검색된 발췌 원문이 그대로 표시됨(AI가 요약/생성하지 않음).
   관련 문서를 찾지 못하면 "제공된 문서에서 관련 근거를 찾지 못했습니다"로 명시됨
5. 주의사항에는 항상 작업허가·안전조치·담당자 확인 문구가 포함됨

## 4. API 명세

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/index` | `backend/documents`의 PDF를 추출·청크 분할해 ChromaDB에 저장 (증분) |
| POST | `/api/index-fault-cases` | `backend/fault_cases`의 고장사례(PDF/HWP/엑셀)를 인덱싱 (증분) |
| POST | `/api/chat` | `{ "question": "..." }` → 검색 결과 기반 답변(LLM 미사용) + 근거 문서 목록 반환 |
| GET | `/api/pdf/{filename}` | PDF 원본 파일 스트리밍 (미리보기용) |
| GET | `/api/health` | 헬스체크 |

## 5. 1GB급 문서로 확장하는 방법

MVP는 소량 PDF로 동작을 검증하기 위한 구조이며, 다음과 같이 그대로 확장할 수 있다.

- **인덱싱 스케일**: `/api/index`는 이미 파일 해시 기반 증분 인덱싱을 지원하므로, 대량 PDF를 나눠서
  여러 번 호출해도 안전하다. 필요 시 `index_router.py`를 배치 작업/큐(Celery 등)로 옮겨 백그라운드
  처리로 전환한다.
- **벡터DB 스케일**: `vector_store.py`는 ChromaDB `PersistentClient`만 사용하므로, 문서량이 늘면
  `HttpClient`(서버 모드) 또는 다른 벡터DB로 교체해도 `add_chunks`/`query` 인터페이스는 그대로 유지된다.
- **청크 전략**: 현재는 단순 슬라이딩 윈도우 분할이다. 문서량이 늘면 문장/표 경계를 인식하는 분할기로
  교체하되, 메타데이터 스키마(`file_name`, `page_number`, `chunk_id`, `pdf_path`, `text`)는 유지한다.
- **PDF 스토리지**: 현재는 로컬 폴더(`backend/documents`)에서 직접 서빙한다. 용량이 커지면 객체 스토리지
  (S3 등)로 옮기고 `pdf_router.py`에서 signed URL을 반환하도록 바꾼다.

## 6-1. 배포 (Vercel + Render)

보안 정책상 회사 문서(`backend/documents`, `backend/fault_cases`)는 저장소에 포함하지 않는다.
배포 후 프론트엔드의 **Doc Management** 탭에서 직접 업로드해서 채워야 한다.

### 백엔드 (Render)

Vercel 서버리스는 ChromaDB 영구 디스크·무거운 ML 의존성(sentence-transformers)·HWP 추출용
서브프로세스 호출을 지원하지 않으므로 상시 서버가 필요하다. 이 레포 루트의 `render.yaml`을
Render Blueprint로 연결하면 아래가 자동 구성된다:

- Root: `backend`, `pip install -r requirements.txt`, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- 영구 디스크(`/var/data`)에 `chroma_db`/`documents`/`fault_cases`/`chat_history.db`를 마운트
  (재배포해도 인덱싱 데이터·업로드 파일이 유지됨) — **디스크는 Starter 이상 유료 플랜 필요**
- 환경변수 `FRONTEND_ORIGIN`은 Vercel 배포 후 실제 프론트엔드 URL로 설정해야 한다(CORS)

### 프론트엔드 (Vercel)

1. Vercel에서 New Project → 이 저장소 선택
2. **Root Directory**를 `frontend`로 지정 (Next.js 자동 인식)
3. 환경변수 `NEXT_PUBLIC_API_BASE_URL`에 Render 백엔드 URL 입력

### 순서

1. Render에 백엔드 먼저 배포 → 백엔드 URL 확보
2. Vercel에 프론트엔드 배포 시 `NEXT_PUBLIC_API_BASE_URL`에 백엔드 URL 입력 → 프론트엔드 URL 확보
3. Render 백엔드의 `FRONTEND_ORIGIN`을 프론트엔드 URL로 업데이트 후 재배포
4. 배포된 앱의 Doc Management 탭에서 PDF/HWP/엑셀 업로드

## 6-2. 알려진 제한사항 (해커톤 MVP)

- 인증/권한 없음 (내부 시연용)
- 청크 분할은 문자 길이 기준이라 문장이 중간에 끊길 수 있음
- 임베딩 모델은 CPU에서 로컬로 동작하며, 최초 실행 시 모델 다운로드 시간이 소요됨
- LLM을 사용하지 않으므로 원인/조치 등에 대한 AI 요약·추론은 제공하지 않음 — 검색된 발췌 원문을
  사용자가 직접 판단해야 함
- 고장상보 PDF/HWP의 설비/증상/원인/조치 필드는 라벨 기반 정규식으로 추출하므로, 문서 형식이
  일정하지 않으면(라벨-콜론 형식이 아니면) 일부 필드가 비어 있을 수 있음
