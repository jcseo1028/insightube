# Copilot Instructions — InSighTube

## 프로젝트 개요

**InSighTube**는 YouTube 영상 URL을 입력받아 영상의 핵심 내용을 AI로 요약해주는 웹 애플리케이션이다.
사용자에게 빠르고 정확한 영상 요약을 제공하여, 영상을 시청하지 않고도 핵심 정보를 파악할 수 있도록 한다.

---

## 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| **Language** | Python 3.11+ | 타입 힌트 적극 사용 |
| **Web Framework** | FastAPI | 비동기(async) 엔드포인트 사용 |
| **Frontend** | Jinja2 Templates + HTMX + TailwindCSS | SPA 없이 서버 사이드 렌더링 |
| **YouTube 자막 추출** | youtube-transcript-api | 자막 기반 요약의 핵심 라이브러리 |
| **YouTube 메타데이터** | yt-dlp | 영상 제목, 채널명, 썸네일 등 추출 |
| **AI 요약** | OpenAI API (GPT-4o-mini) | LangChain 활용, GitHub Models 또는 OpenAI 직접 연동 |
| **LLM 프레임워크** | LangChain | 프롬프트 템플릿, 체인, 출력 파서 |
| **환경 변수 관리** | python-dotenv | `.env` 파일로 토큰/키 관리 |
| **패키지 관리** | pip + requirements.txt | 가상환경(venv) 사용 권장 |
| **테스트** | pytest + pytest-asyncio | 비동기 테스트 지원 |

---

## 프로젝트 디렉토리 구조

```
insightube/
├── .github/
│   └── copilot-instructions.md   # 이 파일 (Copilot 참조 문서)
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI 앱 진입점
│   ├── config.py                 # 환경 변수 및 설정 관리
│   ├── routers/
│   │   ├── __init__.py
│   │   └── summarize.py          # 요약 관련 API 라우터
│   ├── services/
│   │   ├── __init__.py
│   │   ├── youtube.py            # YouTube 자막/메타데이터 추출 서비스
│   │   └── summarizer.py         # LangChain 기반 AI 요약 서비스
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic 요청/응답 스키마
│   ├── templates/
│   │   ├── base.html             # 기본 레이아웃 템플릿
│   │   ├── index.html            # 메인 페이지 (URL 입력 폼)
│   │   └── partials/
│   │       └── summary_result.html  # HTMX 파셜 (요약 결과)
│   └── static/
│       ├── css/
│       │   └── style.css         # 커스텀 스타일
│       └── js/
│           └── app.js            # 클라이언트 스크립트
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # pytest 공통 fixture
│   ├── test_youtube.py           # YouTube 서비스 테스트
│   └── test_summarizer.py        # 요약 서비스 테스트
├── .env.example                  # 환경 변수 템플릿
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 핵심 기능 명세

### 1. YouTube URL 입력 및 검증

- 사용자가 YouTube URL을 입력하면 정규식으로 유효성을 검증한다.
- 지원 URL 형식:
  - `https://www.youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID`
  - `https://www.youtube.com/embed/VIDEO_ID`
- 유효하지 않은 URL은 사용자에게 즉시 에러 메시지를 표시한다.

### 2. YouTube 자막 추출

- `youtube-transcript-api`를 사용하여 자막을 추출한다.
- 자막 우선순위: **한국어(ko)** → **영어(en)** → **자동 생성 자막**
- 자막이 없는 경우 사용자에게 "자막을 사용할 수 없는 영상입니다" 메시지를 표시한다.

### 3. 영상 메타데이터 추출

- `yt-dlp`를 사용하여 다음 정보를 추출한다:
  - 영상 제목
  - 채널명
  - 영상 길이(duration)
  - 썸네일 URL
- 메타데이터 추출 실패 시에도 요약 기능은 정상 동작해야 한다.

### 4. AI 기반 핵심 내용 요약

- LangChain을 사용하여 프롬프트 체인을 구성한다.
- **요약 전략:**
  - 자막 텍스트가 짧은 경우 (토큰 4,000 이하): 단일 요약 (Stuff)
  - 자막 텍스트가 긴 경우 (토큰 4,000 초과): Map-Reduce 방식 분할 요약
- **요약 출력 형식:**
  - 한 줄 핵심 요약 (1~2문장)
  - 주요 포인트 (bullet point, 3~7개)
  - 키워드 태그 (3~5개)

### 5. 웹 UI

- 메인 페이지에서 URL 입력 및 요약 결과를 동일 화면에 표시한다.
- HTMX를 사용하여 페이지 전체 리로드 없이 요약 결과를 렌더링한다.
- 요약 처리 중 로딩 인디케이터를 표시한다.
- 반응형 디자인 (모바일/데스크톱 지원)

---

## API 엔드포인트

### `GET /`

- 메인 페이지 렌더링 (URL 입력 폼 표시)

### `POST /api/summarize`

- **Request Body:**
  ```json
  {
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }
  ```
- **Response (성공):**
  ```json
  {
    "success": true,
    "data": {
      "video_id": "VIDEO_ID",
      "title": "영상 제목",
      "channel": "채널명",
      "duration": "12:34",
      "thumbnail_url": "https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg",
      "summary": {
        "one_line": "영상의 핵심 내용 한 줄 요약",
        "key_points": [
          "주요 포인트 1",
          "주요 포인트 2",
          "주요 포인트 3"
        ],
        "keywords": ["키워드1", "키워드2", "키워드3"]
      }
    }
  }
  ```
- **Response (실패):**
  ```json
  {
    "success": false,
    "error": {
      "code": "INVALID_URL",
      "message": "유효하지 않은 YouTube URL입니다."
    }
  }
  ```

### `POST /summarize` (HTMX 전용)

- HTMX 요청 시 HTML 파셜(`summary_result.html`)을 반환한다.
- `HX-Request` 헤더 존재 여부로 HTMX 요청을 판별한다.

---

## 코딩 컨벤션

### Python 코드 스타일

- **PEP 8** 준수
- 타입 힌트를 모든 함수 시그니처에 적용한다.
- docstring은 Google 스타일을 사용한다.
- f-string을 문자열 포맷팅에 사용한다.
- `async`/`await`를 I/O 바운드 작업에 적극 활용한다.

### 함수 작성 예시

```python
async def extract_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """YouTube 영상의 자막 텍스트를 추출한다.

    Args:
        video_id: YouTube 영상 ID.
        languages: 선호 자막 언어 코드 목록. 기본값은 ["ko", "en"].

    Returns:
        결합된 자막 텍스트.

    Raises:
        TranscriptNotFoundError: 사용 가능한 자막이 없는 경우.
    """
    if languages is None:
        languages = ["ko", "en"]
    ...
```

### 에러 처리

- 커스텀 예외 클래스를 정의하여 도메인별 에러를 구분한다.
- FastAPI의 `HTTPException` 대신 커스텀 예외 핸들러를 사용한다.
- 모든 외부 API 호출에 타임아웃과 재시도 로직을 적용한다.

### 환경 변수

```env
# .env.example

# === LLM Provider 설정 (둘 중 하나만 설정) ===
# 방법 1: GitHub Token (GitHub Models 사용 — 별도 API 키 불필요)
GITHUB_TOKEN=your-github-token-here

# 방법 2: OpenAI API Key (OpenAI 직접 사용)
# OPENAI_API_KEY=your-openai-api-key-here

# === 공통 설정 ===
LLM_MODEL=gpt-4o-mini
MAX_TRANSCRIPT_LENGTH=50000
SUMMARY_LANGUAGE=ko
```

#### LLM Provider 우선순위

1. `GITHUB_TOKEN`이 설정되어 있으면 **GitHub Models** 엔드포인트(`https://models.inference.ai.azure.com`) 사용
2. `OPENAI_API_KEY`가 설정되어 있으면 **OpenAI API** 직접 사용
3. 둘 다 없으면 서버 시작 시 에러 발생

---

## 의존성 목록 (requirements.txt)

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
jinja2>=3.1.0
python-dotenv>=1.0.0
youtube-transcript-api>=0.6.0
yt-dlp>=2024.0.0
langchain>=0.3.0
langchain-openai>=0.3.0
httpx>=0.27.0
pydantic>=2.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

---

## 주요 구현 가이드라인

### YouTube 서비스 (`app/services/youtube.py`)

1. `extract_video_id(url: str) -> str` — URL에서 영상 ID를 추출한다.
2. `get_transcript(video_id: str) -> str` — 자막 텍스트를 추출한다.
3. `get_video_metadata(video_id: str) -> VideoMetadata` — 메타데이터를 가져온다.
4. 각 함수는 독립적으로 실패 가능하며, 개별 에러 처리가 필요하다.

### 요약 서비스 (`app/services/summarizer.py`)

1. LangChain의 `ChatOpenAI`를 사용하여 LLM 인스턴스를 생성한다.
   - `GITHUB_TOKEN` 사용 시: `base_url="https://models.inference.ai.azure.com"`, `api_key=GITHUB_TOKEN`
   - `OPENAI_API_KEY` 사용 시: 기본 OpenAI 엔드포인트 사용
2. `PromptTemplate`으로 요약 프롬프트를 정의한다.
3. 출력은 `PydanticOutputParser`를 사용하여 구조화된 JSON으로 파싱한다.
4. 긴 텍스트는 `RecursiveCharacterTextSplitter`로 분할 후 Map-Reduce 한다.

### 프론트엔드

1. TailwindCSS CDN을 사용하여 별도 빌드 과정 없이 스타일링한다.
2. HTMX를 사용하여 서버에서 렌더링된 HTML 파셜을 동적으로 삽입한다.
3. 다크 모드를 지원한다 (`prefers-color-scheme` 미디어 쿼리 활용).

---

## 보안 고려사항

- API 키는 절대 소스 코드에 하드코딩하지 않는다.
- `.env` 파일은 `.gitignore`에 반드시 포함한다.
- 사용자 입력(URL)은 서버 측에서 엄격하게 검증한다.
- Rate Limiting을 적용하여 API 남용을 방지한다.

---

## 실행 방법

```bash
# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
copy .env.example .env       # Windows
cp .env.example .env         # macOS/Linux
# .env 파일을 편집하여 GITHUB_TOKEN 또는 OPENAI_API_KEY 설정

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 참고 사항

- 이 문서는 GitHub Copilot이 프로젝트 컨텍스트를 이해하고 일관된 코드를 생성하기 위한 참조 문서이다.
- 모든 코드 생성 시 이 문서의 기술 스택, 디렉토리 구조, 코딩 컨벤션을 따른다.
- 한국어 사용자를 주 대상으로 하며, UI 텍스트와 요약 결과는 한국어로 제공한다.
