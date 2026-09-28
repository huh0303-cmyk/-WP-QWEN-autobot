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

## 2026-09-27 WordPress 계정 카드 글쓰기·개별 발행 보완

- `task_id`: `wp-social-cards-20260927-1628-kst`
- 요청/시작: 2026-09-27 16:00 KST경, 사용자 직접 요청
- 대상: `control.korea365.org/social-accounts`, WordPress 25개 운영 사이트
- 완료 기준: 방문자 많은 사이트부터 내림차순 표시, 사이트별 글쓰기 트리거와 개별 발행 동선 제공, 이미지 수 기본값 1장 및 발행 파이프라인 최대 1장 보장
- 확인된 원인: 전체 계정 화면이 YouTube/SNS/Tistory/Naver 카드만 조합하고 WordPress 데이터를 받지 않아 WordPress 버튼과 정렬이 표시되지 않았음
- 변경:
  - 메인 통제실의 실시간 WordPress 데이터를 전체 계정 화면에 연결
  - 오늘 방문자 수 내림차순, 미집계 사이트 후순위 정렬
  - 사이트별 `글쓰기 트리거`, `초안 확인 · 개별 글발행`, 비상 즉시 공개 버튼 추가
  - 글쓰기 이미지 입력을 0~1 범위, 기본 1장으로 설정
  - GitHub workflow와 WordPress writer에 `image_count`/`WP_IMAGE_COUNT` 전달; 뉴스 실제 사진과 생성 이미지를 합쳐도 최대 1장만 사용
- 검증:
  - Python 구문 검사 통과
  - workflow YAML 파싱 통과
  - WordPress 정렬/기본 이미지 수/버튼 템플릿 렌더 검사 통과
- 작업 중 장애 및 복구:
  - C: 여유 공간이 0바이트가 되어 압축 파일 수정이 중단됨
  - Windows 임시 정리와 재생성 가능한 브라우저·모델 캐시 압축으로 약 3GB 이상 확보
  - 일시적으로 0바이트가 된 `scripts/autopost_mega.py`는 변경 전 Git 원본으로 복구 후 수정 재적용; 운영 서버에는 영향 없음
- 상태: 코드 검증 완료, GitHub push 및 VPS 배포 검증 예정
- 배포/실화면 증거:
  - Git commit `4177366f`, GitHub Actions deploy run `36303309112` 성공
  - `https://control.korea365.org/social-accounts?platform=WordPress`에서 WordPress 27개, 방문자 158→81→78 순서, 이미지 수 1, 세 개 버튼을 로그인된 Chrome으로 확인
- 추가 장애:
  - `daily-network-publish.yml`이 과거 커밋 `05f67cc5`부터 job-level `if`에서 `matrix.site`를 참조해 모든 push에 0초 startup failure를 만들고 있었음
  - 사이트 선택 조건을 matrix가 사용 가능한 각 step-level `if`로 이동해 글을 발행하지 않고 문법 오류만 복구
- 최종 배포:
  - workflow 복구 commit `95264439`, deploy run `36303452952` 성공
  - 해당 commit에서는 과거의 `daily-network-publish.yml` startup failure가 더 이상 생성되지 않아 GitHub workflow 문법 복구 확인
  - 전체 저장소 CI는 변경 전 run과 동일하게 `41 failed, 602 passed`로 실패했으며, 누락된 과거 workflow 파일·오래된 26개 도메인 기대값 등 이번 변경과 무관한 기존 실패 41건임
- 최종 상태: 요청 화면과 발행 버튼 경로 배포 완료·실화면 확인 완료. 기존 저장소 전체 테스트 부채는 별도 정비 필요.
- 2026-09-28 KST — 런던프로젝트GPT 자동/수동 모드 확장. 사용자 지시대로 자동 모드는 기존 4-Agent 발행 경로를 유지하고, 수동 모드는 Agent 1~3 준비 후 Agent 4를 사람 발행 대기로 전환했다. 각 Agent 카드에 결과와 복사 동선을 넣고, 사람이 붙여넣은 공개 URL의 사이트/HTTP/제목을 검증하는 API를 추가했다. 수동 분기는 출판자 호출 없이 종료하며 수동 4번 재실행은 거부한다. 로컬 검증: 새 수동 모드 테스트 3개 통과, JavaScript 구문 검사와 `git diff --check` 통과. GitHub commit `7fb05b1`, PR #131 생성 후 fetch-back으로 저장 확인. 운영 서버 `/opt/korea365`에 대상 코드 4개 파일만 적용하고 `korea365-control.service`와 `korea365-n8n-gateway.service`를 재시작해 둘 다 active, 게이트웨이 health HTTP 200 확인. 실제 `https://control.korea365.org/london-gpt`에서 자동/수동 라디오와 네 Agent 개별 카드 및 수동 모드의 발행 선택 숨김/①~③ 실행 버튼을 확인했다. 전체 CI run `36364613552`는 기존 다른 영역 실패 41건, 통과 605건(이번 신규 3건 포함)으로 실패했다. 이번 변경의 실제 글 생성부터 수동 발행까지의 라이브 실행은 하지 않았다.
- 2026-09-28 10:10 KST — PR #131을 GitHub `main`의 `1c518628`로 병합했다. 운영 서버 HEAD도 같은 commit이며 이번 대상 코드 4개 파일은 Git 기준 수정 없음, control/gateway 서비스 active, 수동 UI/API 파일 존재를 재확인했다. 병합 후 일반 VPS deploy run `36364918940`은 배포된 commit `1c518628`과 내부 배포 요청의 오래된 target `2ec27ce3`가 달라 실패로 끝났다. 운영 배포 자체는 현재 commit에 도달했으므로 이 실패는 배포 요청 target 경합이다. 전체 테스트 run은 기존 41건 실패를 이어받았다. n8n workflow 별도 deploy 결과는 추후 확인 대상으로 남긴다.
