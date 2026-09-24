# 런던프로젝트 작업 원장 정책

모든 런던프로젝트 작업은 성공 여부와 관계없이 흔적을 남긴다.

## 기록 시작점
사용자 요청 또는 자동 스케줄이 생성되는 순간 `task_id`를 발급하고 `TASK_CREATED`를 기록한다. 작업이 실제 실행되지 못해도 요청 자체는 삭제하지 않는다.

## 반드시 기록할 항목
- task_id / correlation_id / parent_task_id
- 요청자와 요청 시각
- 플랫폼과 실제 대상 사이트·채널
- 작업 목적과 완료 기준
- 최초 담당 Agent 및 담당 변경
- Plan A/B/C/SAFE HOLD 전환
- VPS/GitHub worker 실행 시도
- API provider와 시도 결과
- 시작/종료 시각
- 모든 상태 변경
- 재시도 횟수
- 성공 결과와 실패 오류/원인
- 외부 URL, post ID, video ID, channel ID, HTTP/API 증거
- 사람 검수/승인 시각과 승인자
- Deterministic Audit 결과

## 금지
- 실패 작업 삭제
- 재시도를 새 작업으로 숨기기
- workflow success를 publication success로 기록
- Agent 말만으로 VERIFIED_COMPLETE 기록
- 증거 없는 완료 상태
- task_id 없는 자동 발행

## 저장 위치
1. SQLite durable ledger: `/opt/korea365/data/control-operations.sqlite3`
2. Append-only JSONL mirror: `/opt/korea365/data/london_project_activity.jsonl`
3. 운영 요약 JSON: `/opt/korea365/data/london_project_activity_report.json`
4. 운영 요약 Markdown: `/opt/korea365/data/london_project_activity_report.md`

SQLite는 현재 상태와 질의를 담당하고 JSONL은 사후 감사용 append-only 보조 기록이다. 두 기록은 task_id와 correlation_id로 대조 가능해야 한다.

## 상태 흐름
REQUESTED → PLANNED → ASSIGNED → RUNNING → READY_FOR_AUDIT → AUDITING

YouTube 비공개 검증: VERIFIED_PRIVATE → REVIEW_REQUIRED
감사 실패: REWORK_REQUIRED 또는 NEEDS_ATTENTION
외부 의존성: BLOCKED
작업 실패: FAILED
공개 결과가 Deterministic Audit을 통과한 경우만 VERIFIED_COMPLETE

## Failover 기록
Plan A CODEX → Plan B Claude → Plan C Gemini → SAFE HOLD 전환은 모두 `FAILOVER` 이벤트로 남긴다.
기록 항목은 전 담당자, 새 담당자, 전환 원인, 당시 열린 작업, handoff packet, 복귀 시각이다.

## 사람 승인 기록
YouTube 및 review-gated 콘텐츠는 사용자 승인 자체가 `HUMAN_APPROVAL` 이벤트다. 이 이벤트가 없으면 public 전환을 실행하지 않는다.

## 원칙
런던프로젝트에서는 실패도 운영 자산이다. 같은 실패를 반복하지 않도록 요청부터 최종결과까지 하나의 task_id 계보로 보존한다.


## GitHub same-session 기록 의무 — 2026-09-25
- 모든 중간·최종 결과, 판단, 수정, 확인된 ID, 실패·차단 원인, 미확정 항목과 다음 행동을 같은 작업 세션 안에 GitHub에 기록한다.
- 채팅만 남아 있는 상태는 공식 기록으로 인정하지 않는다.
- 다음 세션은 GitHub 최신 기록을 먼저 읽고 이어서 처리하며, 이미 기록된 결정을 사용자에게 다시 묻지 않는다.
- 비밀번호·토큰·개인 인증정보는 예외로 GitHub에 기록하지 않는다.
