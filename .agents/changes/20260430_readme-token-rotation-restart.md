# README: 토큰 갱신 후 서버 재시작 절차 추가

## 배경
- `.env`의 `GITHUB_TOKEN` 등을 재발급한 뒤 어떻게 서버에 반영하는지 문서화 누락.
- 작업 스케줄러로 launcher(`scripts/run_server.py`, pythonw)가 자식 uvicorn을 자동 재시작하므로 launcher를 죽일 필요 없이 자식 uvicorn만 종료하면 새 `.env`가 자동 로드됨.

## 변경
- `README.md` "Windows 자동 시작" 섹션 다음에 "토큰 갱신 후 서버 재시작" 하위 섹션 추가.
  - launcher 구조와 재시작 동작 설명.
  - PowerShell 명령 예시(자식 uvicorn PID 식별 → `Stop-Process` → 헬스체크).
  - 작업 스케줄러를 쓰지 않는 경우의 대안 명시.

## 영향 범위
- 문서 변경만. 코드/계약/테스트 변경 없음.
