# CODEX PM / Orchestrator Architecture

확정 구조: 2026-09-16

## 목적

Control Korea365의 모든 장기 운영은 특정 대화 세션이나 단일 AI 공급자의 사용량에 종속되지 않는다.

최종 흐름:

`Control Korea365 -> CODEX PM policy -> server-side Orchestrator -> OpenAI / Claude / Gemini / VPS / GitHub Actions -> publication -> verification -> Control Korea365`

## 역할

### CODEX PM

- 프로젝트 정책과 우선순위를 정의한다.
- 기존 `-WP-QWEN-autobot` 저장소를 단일 기준본으로 유지한다.
- 새 시스템을 별도로 만들지 않고 기존 control_center / operations / workflows를 확장한다.
- 실제 무인 운영은 대화 세션이 아니라 VPS의 Orchestrator가 맡는다.

### Server-side Orchestrator

`control_center/orchestrator.py`

- WordPress/general editorial: OpenAI -> Claude -> Gemini
- Blogger: Gemini -> Claude -> OpenAI
- 공급자별 429/quota/timeout/5xx/auth/overload 감지
- 공급자별 cooldown 기록
- 같은 요청을 다음 공급자에게 승계
- 모든 공급자가 실패하면 성공으로 위장하지 않고 `OrchestratorExhausted`로 중단
- 상태는 VPS SQLite에 보존하여 프로세스 재시작 후에도 cooldown/실패 기록 유지

## ChatGPT/Codex 사용량과 서버 자동화의 차이

ChatGPT/Codex 제품의 대화 사용량을 VPS가 직접 읽을 수는 없다. 따라서 무인 운영 연속성은 서버측 API에서 보장한다.

- OpenAI API quota/rate-limit/timeout -> Claude API 자동 승계
- Claude도 실패 -> Gemini API 자동 승계
- 특정 공급자가 복구될 때까지 cooldown으로 건너뜀

이 설계 때문에 현재 ChatGPT 세션이 종료되거나 사람이 자리를 비워도 VPS 작업은 독립적으로 계속될 수 있다.

## 비밀키

비밀키는 코드/Google Sheet/로그에 저장하지 않는다.

VPS 환경 파일 예시: `/etc/korea365/control.env`

필수/선택 환경변수:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `CONTROL_OPERATIONS_DB=/opt/korea365/data/control-operations.sqlite3`
- `ORCHESTRATOR_COOLDOWN_SECONDS=900`
- `ORCHESTRATOR_OPENAI_MODEL=gpt-5-mini`
- `ORCHESTRATOR_CLAUDE_MODEL=claude-sonnet-4-20250514`
- `ORCHESTRATOR_GEMINI_MODEL=gemini-2.5-flash`

선택적으로 체인을 덮어쓸 수 있다.

- `ORCHESTRATOR_CHAIN_WORDPRESS=openai:gpt-5-mini,anthropic:claude-sonnet-4-20250514,gemini:gemini-2.5-flash`
- `ORCHESTRATOR_CHAIN_BLOGGER=gemini:gemini-2.5-flash,anthropic:claude-sonnet-4-20250514,openai:gpt-5-mini`

실제 사용 가능한 모델명은 각 API 계정 권한에 맞춰 환경변수에서 교체한다.

## 안정성 원칙

1. 한 공급자 실패가 전체 발행기의 실패가 되지 않게 한다.
2. 같은 공급자를 무한 재시도하지 않는다.
3. provider health/cooldown을 SQLite에 보존한다.
4. 발행 작업의 기존 request_id와 중복 방지 정책은 유지한다.
5. AI 생성 성공과 실제 공개 성공은 별개이며 기존 공개 URL 검증 규칙을 유지한다.
6. 비밀키 누락 시 해당 공급자를 건너뛰되 다른 공급자가 있으면 계속한다.
7. 모든 공급자가 실패하면 발행하지 않고 명시적으로 실패 상태를 남긴다.

## 현재 범위

이 Orchestrator는 우선 텍스트 생성 공급자 장애를 자동 승계한다. GitHub Actions/VPS 작업 배분과 공개 검증은 기존 `control_center/operation_routes.py`, `operations.py`, `operation_gateway.py`를 유지한다.

후속 확장 항목:

- Control Korea365 화면에 provider health 표시
- 작업별 실제 provider/model 기록
- 비용/토큰 사용량 회수 가능한 공급자만 실제 값 기록
- 공급자별 일일 예산 상한과 circuit breaker
- 영상/이미지 작업도 동일 TaskRouter 인터페이스로 통합
