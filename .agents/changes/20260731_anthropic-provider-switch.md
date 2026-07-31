# Anthropic Claude LLM Provider 추가

## Context

- GitHub Models 서비스가 2026-07-30 자로 완전히 은퇴(retired)되어, 기존 `GITHUB_TOKEN` 기반 LLM 경로가 401 오류를 반환하기 시작함.
- 사용자가 Anthropic API 키를 발급하고 크레딧을 충전하여, Claude Sonnet을 새 기본 LLM으로 채택하기로 결정.

## Decision

- `LLMProvider` enum에 `ANTHROPIC = "anthropic"` 추가.
- 프로바이더 자동 감지 우선순위를 `ANTHROPIC → OPENAI → GITHUB` 로 재정렬 (GitHub는 은퇴 상태이나 하위 호환을 위해 유지).
- `_create_llm()` 이 `LLMProvider.ANTHROPIC` 일 때 `langchain_anthropic.ChatAnthropic` 을 반환하도록 분기 (지연 import).
- Provider 별 기본 모델:
  - Anthropic: `claude-sonnet-4-5`
  - OpenAI / GitHub: `gpt-4o-mini`
  - `LLM_MODEL` 환경 변수로 언제든 override.
- Anthropic 경로는 `max_tokens=4096` 명시 (Anthropic 요구사항).

## Scope of Changes

- `requirements.txt`: `langchain-anthropic>=0.3.0` 추가.
- `app/config.py`:
  - `LLMProvider.ANTHROPIC` enum 값 추가.
  - `_detect_provider()` 감지 순서 변경 및 `ANTHROPIC_API_KEY` 처리 추가.
  - `get_settings()` provider-specific `default_model` 매핑 추가.
- `app/services/summarizer.py`:
  - `BaseChatModel` 반환형으로 시그니처 확장.
  - `LLMProvider.ANTHROPIC` 분기에서 `ChatAnthropic` 생성.
- `.env.example`: Anthropic을 방법 1로 승격, GitHub Token은 DEPRECATED 주석.
- `README.md`: `.env` 설정 예시 재정렬 및 GitHub Models 은퇴 표기.
- `.agents/contracts.md`, `.agents/modules.md`: 3-provider 지원 반영.

## Non-Scope

- 기존 OpenAI/GitHub 코드 경로는 유지 (하위 호환).
- 테스트는 `_create_llm` 을 mock 하므로 변경 없음.
- 프롬프트/파서/스키마는 그대로 사용 (LangChain 인터페이스가 통일되어 있어 provider 교체가 투명).

## Verification

- 74/74 pytest 통과.
- `.env` 에 `ANTHROPIC_API_KEY=sk-ant-...` 를 추가하고 uvicorn 자식 프로세스를 재기동한 후 오늘의 독서 팝업으로 스모크 테스트 필요 (사용자 후속 작업).

## Status

Implemented (코드/문서 반영 완료, 사용자 `.env` 갱신 및 서버 재기동 대기).
