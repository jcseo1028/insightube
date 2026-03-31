# 1차 개발 계획 — InSighTube MVP

> **목표:** YouTube URL을 입력하면 자막을 추출하고 AI 요약 결과를 화면에 출력하는 **End-to-End 동작 확인**
> **범위:** 핵심 파이프라인만 구현 (URL 입력 → 자막 추출 → AI 요약 → 결과 표시)
> **예상 산출물:** 브라우저에서 URL을 붙여넣고 "요약" 버튼을 누르면 요약 결과가 표시되는 상태

---

## Phase 1: 프로젝트 초기 설정

### 1-1. 프로젝트 스캐폴딩

- [ ] 디렉토리 구조 생성 (`app/`, `tests/`, `app/routers/`, `app/services/`, `app/models/`, `app/templates/`, `app/static/`)
- [ ] 각 패키지에 `__init__.py` 생성
- [ ] `requirements.txt` 작성
- [ ] `.env.example` 작성
- [ ] `.gitignore` 작성 (venv, .env, __pycache__ 등)

### 1-2. 환경 구성

- [ ] 가상환경 생성 및 의존성 설치
- [ ] `app/config.py` — python-dotenv 기반 환경 변수 로드
  - LLM Provider 자동 감지: `GITHUB_TOKEN` 우선 → `OPENAI_API_KEY` 펴백
  - 둘 다 없으면 서버 시작 시 에러
  - 공통 설정: `LLM_MODEL`, `MAX_TRANSCRIPT_LENGTH`, `SUMMARY_LANGUAGE`

### 1-3. FastAPI 앱 기본 골격

- [ ] `app/main.py` — FastAPI 앱 인스턴스, 라우터 등록, 정적 파일/템플릿 설정
- [ ] `GET /` 엔드포인트 — 메인 페이지 렌더링 확인
- [ ] `uvicorn app.main:app --reload`로 서버 기동 확인

**완료 기준:** 브라우저에서 `http://localhost:8000` 접속 시 빈 페이지라도 정상 응답

---

## Phase 2: YouTube 서비스 구현

### 2-1. URL 파싱 및 검증

- [ ] `app/services/youtube.py` — `extract_video_id(url: str) -> str`
  - 정규식으로 `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/` 지원
  - 유효하지 않은 URL 시 `InvalidURLError` 발생

### 2-2. 자막 추출

- [ ] `app/services/youtube.py` — `get_transcript(video_id: str) -> str`
  - `youtube-transcript-api`로 자막 추출
  - 언어 우선순위: ko → en → 자동 생성
  - 자막 없을 시 `TranscriptNotFoundError` 발생

### 2-3. 메타데이터 추출

- [ ] `app/services/youtube.py` — `get_video_metadata(video_id: str) -> VideoMetadata`
  - `yt-dlp`로 제목, 채널명, 영상 길이, 썸네일 URL 추출
  - 실패해도 None 반환 (요약 기능에 영향 없음)

### 2-4. Pydantic 모델 정의

- [ ] `app/models/schemas.py`
  - `SummarizeRequest` — url 필드
  - `VideoMetadata` — title, channel, duration, thumbnail_url
  - `SummaryResult` — one_line, key_points, keywords
  - `SummarizeResponse` — success, data, error

**완료 기준:** 터미널에서 `extract_video_id()`, `get_transcript()` 호출 시 실제 자막 텍스트 출력

---

## Phase 3: AI 요약 서비스 구현

### 3-1. LangChain 기반 요약 체인

- [ ] `app/services/summarizer.py` — `summarize_transcript(text: str) -> SummaryResult`
  - LLM 인스턴스 생성 (`ChatOpenAI`)
    - `GITHUB_TOKEN` 사용 시: `base_url="https://models.inference.ai.azure.com"`, `api_key=GITHUB_TOKEN`
    - `OPENAI_API_KEY` 사용 시: 기본 OpenAI 엔드포인트
  - 요약 프롬프트 작성 (한 줄 요약 + 주요 포인트 + 키워드)
  - `PydanticOutputParser`로 구조화된 출력 파싱

### 3-2. 텍스트 길이별 전략 분기

- [ ] 토큰 4,000 이하: 단일 요약 (Stuff)
- [ ] 토큰 4,000 초과: `RecursiveCharacterTextSplitter` 분할 → Map-Reduce

**완료 기준:** 자막 텍스트를 넣으면 `{ one_line, key_points, keywords }` 형태의 구조화된 요약 반환

---

## Phase 4: API 라우터 연결

### 4-1. 요약 API 엔드포인트

- [ ] `app/routers/summarize.py`
  - `POST /api/summarize` — JSON 요청/응답
  - `POST /summarize` — HTMX 요청 시 HTML 파셜 반환
  - 흐름: URL 검증 → 자막 추출 + 메타데이터 추출 (병렬) → AI 요약 → 응답

### 4-2. 커스텀 예외 핸들러

- [ ] `app/main.py`에 예외 핸들러 등록
  - `InvalidURLError` → 400 응답
  - `TranscriptNotFoundError` → 404 응답
  - 일반 Exception → 500 응답

**완료 기준:** `curl -X POST http://localhost:8000/api/summarize -d '{"url":"..."}' `로 JSON 요약 응답 수신

---

## Phase 5: 웹 UI 구현

### 5-1. 템플릿 작성

- [ ] `app/templates/base.html` — 기본 레이아웃 (TailwindCSS CDN, HTMX CDN)
- [ ] `app/templates/index.html` — URL 입력 폼 + 결과 영역
  - HTMX `hx-post="/summarize"` 으로 비동기 요청
  - 로딩 인디케이터 (`hx-indicator`)

### 5-2. 요약 결과 파셜

- [ ] `app/templates/partials/summary_result.html`
  - 영상 썸네일 + 제목 + 채널명
  - 한 줄 요약
  - 주요 포인트 (bullet list)
  - 키워드 태그

### 5-3. 최소 스타일링

- [ ] `app/static/css/style.css` — 커스텀 스타일 (있다면)
- [ ] `app/static/js/app.js` — 클라이언트 스크립트 (URL 클립보드 붙여넣기 등)

**완료 기준:** 브라우저에서 YouTube URL 입력 → "요약하기" 클릭 → 로딩 후 요약 결과 표시

---

## Phase 6: 테스트 및 마무리

### 6-1. 핵심 테스트 작성

- [ ] `tests/conftest.py` — 공통 fixture (FastAPI TestClient, mock 데이터)
- [ ] `tests/test_youtube.py` — URL 파싱, 자막 추출 테스트 (외부 API mock)
- [ ] `tests/test_summarizer.py` — 요약 서비스 테스트 (OpenAI API mock)

### 6-2. README 작성

- [ ] `README.md` — 프로젝트 소개, 실행 방법, 스크린샷 영역

**완료 기준:** `pytest` 실행 시 전체 테스트 통과

---

## 구현 순서 요약

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
 설정       YouTube    AI 요약    API 연결    웹 UI      테스트
(30분)     (1시간)    (1시간)    (30분)     (1시간)    (30분)
```

**총 예상 소요:** 약 4~5시간

---

## 1차 개발 범위에서 제외 (2차 이후)

| 항목 | 비고 |
|------|------|
| 다크 모드 | `prefers-color-scheme` 기반 — UI 안정화 후 |
| Rate Limiting | 운영 환경 배포 시 적용 |
| 에러 재시도 로직 | 외부 API 호출 안정화 단계 |
| 캐싱 | 동일 영상 재요약 방지 — 성능 최적화 단계 |
| 다국어 자막 선택 UI | 현재는 자동 우선순위 적용 |
| 요약 히스토리 저장 | DB 연동 필요 — 2차 이후 |

---

## 체크포인트

각 Phase 완료 시 다음을 확인한다:

1. **Phase 1 완료** → 서버 기동, 메인 페이지 응답 확인
2. **Phase 2 완료** → 실제 YouTube 영상의 자막 텍스트 추출 확인
3. **Phase 3 완료** → 자막 텍스트 → 구조화된 요약 결과 반환 확인
4. **Phase 4 완료** → API 엔드포인트로 전체 파이프라인 동작 확인
5. **Phase 5 완료** → 브라우저 UI에서 End-to-End 동작 확인
6. **Phase 6 완료** → 테스트 통과, README 완성
