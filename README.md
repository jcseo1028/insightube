# InSighTube 🎬

YouTube 영상 URL을 입력하면 AI가 핵심 내용을 요약해주는 웹 애플리케이션입니다.

## 주요 기능

- **YouTube URL 입력** — 다양한 URL 형식 지원 (`youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`)
- **자막 자동 추출** — 한국어 → 영어 → 자동 생성 자막 우선순위
- **AI 핵심 요약** — GPT-4o-mini 기반 구조화된 요약 (한 줄 요약 + 주요 포인트 + 키워드)
- **요약 상세도 조절** — 간단 / 보통 / 상세 3단계 + 포인트·키워드 수 조정 (기본값: 상세)
- **전체 스크립트 보기** — 타임스탬프(`[MM:SS]`) 기반 문단 구분, 복사 버튼 제공
- **실시간 UI** — HTMX 기반 페이지 리로드 없는 요약 결과 표시
- **오늘의 독서 내용** — Notion 독서 DB의 "읽기 종료" 페이지 중 무작위 한 권을 골라 새 팝업 창에 **본깨적**(본 것 / 깨달은 것 / 적용할 것) 3카드 구조로 요약 표시
- **Rate Limit 대응** — 자동 재시도(max_retries=5) + 동시 요청 수 제한(Semaphore)
- **콘텐츠 필터 완화 재시도** — `content_filter` 감지 시 민감 표현을 최소 마스킹해 1회 자동 재요약
- **반복 차단 폴백** — 같은 영상이 정책 차단으로 반복 실패하면 `간단(brief)` 요약으로 1회 자동 재시도

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

### (선택) 오늘의 독서 내용 기능

Notion 독서 DB와 연동하여 "읽기 완료" 도서 중 한 권을 랜덤으로 요약하는 기능을 사용하려면 다음 환경 변수를 추가합니다:

```env
NOTION_API_KEY=your-notion-secret-here
NOTION_READING_DB_ID=your-notion-database-id
# 완료 판별용 date 속성명 (기본: '읽기 종료')
NOTION_READING_DONE_PROPERTY=읽기 종료
```

사전 작업으로 Notion에서 해당 DB 페이지의 "연결(Connections)"에 사용 중인 Integration을 추가해야 합니다. 메인 화면 우측 상단의 **📖 오늘의 독서 내용** 버튼을 클릭하면 새 팝업에서 요약 결과를 확인할 수 있습니다.

#### 독서 DB 페이지 구조 (권장)

요약 품질을 높이려면 각 도서 페이지에 다음 세 개의 `heading_2` 세션을 작성해 두세요:

- **본 것** — 책에서 직접 본 사실/핵심 인용/표현
- **깨달은 것** — 책을 통해 깨달은 통찰/생각의 전환
- **적용할 것** — 일상/업무/행동에 적용할 구체적 실천

팝업은 이 세 섹션을 우선적으로 요약 주재로 사용하며, 비어 있는 경우 페이지 전체 본문을 참고합니다. 세 섹션과 본문이 모두 비면 속성(메모/비고/저자 등)만으로 요약하며 안내 배너가 경고로 표시됩니다.

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

서버는 콘솔 창 없이 백그라운드에서 실행됩니다 (`wscript.exe` → `pythonw.exe` → uvicorn). Crash 시 자동 재시작되며, 60초 이내 연속 10회 실패 시 중단됩니다. 로그는 `logs/server.log`에 기록됩니다.

### 토큰 갱신 후 서버 재시작

`GITHUB_TOKEN`(또는 `OPENAI_API_KEY`, `NOTION_API_KEY` 등) 값을 `.env`에서 변경한 경우, 실행 중인 uvicorn 자식 프로세스만 종료하면 launcher(`run_server.py`)가 자동으로 새 프로세스를 띄우면서 변경된 `.env`를 다시 로드합니다. launcher 자체(`pythonw.exe run_server.py`)는 종료할 필요가 없습니다.

PowerShell 예시:

```powershell
# 1) 8000 포트를 점유 중인 uvicorn 자식 프로세스 ID 확인
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'uvicorn' } |
  Select-Object ProcessId, CommandLine

# 2) 자식 uvicorn 프로세스만 종료 (launcher PID 는 종료하지 않음)
Stop-Process -Id <child-pid> -Force

# 3) 5~10초 후 헬스체크
(Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 5).StatusCode
```

작업 스케줄러를 사용하지 않고 직접 실행한 경우에는 해당 uvicorn 프로세스를 종료한 뒤 `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` 으로 다시 실행하면 됩니다.

## 요약 옵션

여기서의 옵션은 **YouTube 요약**에 적용됩니다. 오늘의 독서 팝업은 원적(본깨적) 구조로 고정되어 있어 별도의 옵션이 없습니다.

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| **상세도** | 간단(brief) / 보통(normal) / 상세(detailed) | 상세 |
| **최대 주요 포인트 수** | 3~15개 | 7개 |
| **최대 키워드 수** | 3~10개 | 5개 |
| **전체 스크립트 포함** | 타임스탬프 포함 자막 텍스트 표시 | ON |

기본 상태에서 별도 선택 없이 요약을 실행하면 `상세(detailed)` 옵션으로 처리됩니다.

## 테스트

```bash
pytest
```

## 프로젝트 구조

```text
app/
├── main.py              # FastAPI 앱 진입점
├── config.py            # 환경 변수 및 설정 (LLM + Notion)
├── models/
│   ├── schemas.py       # Pydantic 스키마 (요약/히스토리/독서 모델)
│   └── exceptions.py    # 커스텀 예외 (Notion 예외 포함)
├── routers/
│   ├── history.py       # 히스토리 API + HTMX 라우터
│   ├── daily_log.py     # 일별 로그 API 라우터
│   ├── reading.py       # 오늘의 독서 (팝업 + JSON API)
│   └── summarize.py     # 요약 API 라우터 (JSON + HTMX)
├── services/
│   ├── history.py       # SQLite 히스토리 저장/조회 서비스
│   ├── daily_log.py     # 일별 로그 DB + 파일 로그
│   ├── notion.py        # Notion 독서 DB 연동 (본깨적 추출 포함)
│   ├── youtube.py       # YouTube 자막/메타데이터 추출
│   └── summarizer.py    # LangChain AI 요약 (YouTube + 독서용 `summarize_reading`)
├── templates/
│   ├── base.html        # 공통 레이아웃
│   ├── index.html       # 메인 입력 페이지
│   ├── reading_popup.html  # 오늘의 독서 팝업 (본깨적 3카드)
│   └── partials/
│       ├── history_panel.html   # 최근 요약 사이드 패널
│       └── summary_result.html  # 요약 결과 파셜
└── static/
    ├── css/
    │   └── style.css    # 추가 스타일
    └── js/
        └── app.js       # 클라이언트 보조 스크립트 (팝업 오픈 포함)
data/
└── history.db           # 히스토리/일별 로그 SQLite DB
logs/
├── server.log           # 서버 실행 로그
└── daily/               # 일별 이벤트 텍스트 로그
scripts/
├── setup-task.ps1       # Windows 작업 스케줄러 등록/해제
├── start-server.vbs     # 창 숨김 VBS 래퍼 (Task Scheduler 진입점)
├── run_server.py        # 서버 실행 + 자동 재시작 루프
└── start-server.ps1     # 수동 서버 시작 (디버깅용)
tests/
├── conftest.py          # 테스트 공통 설정
├── test_daily_log.py    # 일별 로그 테스트
├── test_history.py      # 히스토리 서비스/라우터 테스트
├── test_reading.py      # Notion 독서 파서/라우터 테스트
├── test_summarize_router.py  # 요약 폼 옵션 파싱 테스트
├── test_summarizer.py   # 요약 서비스 테스트
└── test_youtube.py      # YouTube 서비스 테스트
```

## 라이선스

MIT
