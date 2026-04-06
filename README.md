# InSighTube 🎬

YouTube 영상 URL을 입력하면 AI가 핵심 내용을 요약해주는 웹 애플리케이션입니다.

## 주요 기능

- **YouTube URL 입력** — 다양한 URL 형식 지원 (`youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`)
- **자막 자동 추출** — 한국어 → 영어 → 자동 생성 자막 우선순위
- **AI 핵심 요약** — GPT-4o-mini 기반 구조화된 요약 (한 줄 요약 + 주요 포인트 + 키워드)
- **요약 상세도 조절** — 간단 / 보통 / 상세 3단계 + 포인트·키워드 수 조정
- **전체 스크립트 보기** — 타임스탬프(`[MM:SS]`) 기반 문단 구분, 복사 버튼 제공
- **실시간 UI** — HTMX 기반 페이지 리로드 없는 요약 결과 표시
- **Rate Limit 대응** — 자동 재시도(max_retries=5) + 동시 요청 수 제한(Semaphore)

## 기술 스택

- **Backend:** Python 3.11+ / FastAPI
- **Frontend:** Jinja2 + HTMX + TailwindCSS
- **AI:** LangChain + OpenAI (GitHub Models 또는 OpenAI API)
- **YouTube:** youtube-transcript-api + yt-dlp

## 빠른 시작

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
copy .env.example .env       # Windows
cp .env.example .env         # macOS/Linux
```

`.env` 파일에서 다음 중 **하나**를 설정합니다:

```env
# 방법 1: GitHub Token (추천 — 별도 API 키 불필요)
GITHUB_TOKEN=your-github-token-here

# 방법 2: OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here
```

```bash
# 4. 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000` 접속 후 YouTube URL을 입력하면 요약 결과를 확인할 수 있습니다.

### Windows 자동 시작 (선택)

Windows 로그온 시 서버를 자동 실행하려면:

```powershell
# 작업 스케줄러 등록
.\scripts\setup-task.ps1

# 등록 해제
.\scripts\setup-task.ps1 -Unregister
```

서버 crash 시 자동 재시작되며, 60초 이내 연속 10회 실패 시 중단됩니다. 로그는 `logs/server.log`에 기록됩니다.

## 요약 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| **상세도** | 간단(brief) / 보통(normal) / 상세(detailed) | 보통 |
| **최대 주요 포인트 수** | 3~15개 | 7개 |
| **최대 키워드 수** | 3~10개 | 5개 |
| **전체 스크립트 포함** | 타임스탬프 포함 자막 텍스트 표시 | ON |

## 테스트

```bash
pytest
```

## 프로젝트 구조

```
app/
├── main.py              # FastAPI 앱 진입점
├── config.py            # 환경 변수 및 설정
├── routers/
│   └── summarize.py     # 요약 API 라우터 (JSON + HTMX)
├── services/
│   ├── youtube.py       # YouTube 자막/메타데이터 추출
│   └── summarizer.py    # LangChain AI 요약 (상세도별 프롬프트)
├── models/
│   ├── schemas.py       # Pydantic 스키마 (요약 옵션 포함)
│   └── exceptions.py    # 커스텀 예외
├── templates/           # Jinja2 HTML 템플릿
└── static/              # CSS, JS 정적 파일
scripts/
├── start-server.ps1     # 서버 시작 (자동 재시작 루프 포함)
└── setup-task.ps1       # Windows 작업 스케줄러 등록/해제
tests/                       # pytest 테스트
```

## 라이선스

MIT
