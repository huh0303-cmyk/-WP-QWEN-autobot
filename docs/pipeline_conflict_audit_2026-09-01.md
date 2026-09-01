# WP 27 + Blogger 27 + YouTube 10 파이프라인 충돌 감사

- 감사일: 2026-09-01 (Asia/Bangkok)
- 운영 저장소: `huh0303-cmyk/-WP-QWEN-autobot`
- 감사 범위: WordPress 27, Blogger 27, YouTube 10
- 원칙: 공개 발행 작업은 정지하고, 읽기 전용 통계·보고와 수동 진입점은 유지

## 즉시 조치

다음 GitHub Actions 워크플로를 GitHub UI에서 `disabled_manually`로 전환했다.

1. `publish-scheduler.yml` — WordPress 캘린더 발행 디스패처
2. `blogger-daily-scheduler.yml` — Blogger 재작성 디스패처
3. `platform-publish.yml` — Blogger 큐 소비 및 원격 초안 생성기
4. `youtube-control-scheduler.yml` — YouTube 10채널 디스패처
5. `newsrooms-daily-publisher.yml` — WordPress 뉴스룸 2개 예약 작성기

정지 직후 GitHub Actions의 실행 중 작업은 0개였다. 다음 수동 작업과 읽기 전용 보고 작업은 비활성화하지 않았다.

- `daily-network-publish.yml`
- `blogger-rewrite.yml`
- `generate-youtube-playlist.yml`
- `curio-longform-daily.yml`
- 종합상황실·GSC·AdSense 읽기 전용 수집

## 복구 백업

Git 전체 이력과 모든 로컬·원격 ref를 포함하는 번들을 만들고 `git bundle verify`를 통과했다.

- 운영 원격 포함 백업: `artifacts/pipeline-backups/wp-autobot-operating-remote-20260901-073414.bundle`
- SHA-256: `0E764B68E98AE22863A292682E70AC06C056126FE8412DCA4E9B10815D979D5D`

## 가장 큰 구조적 문제

### 1. 단일 통제자가 없다

현재 발행 판단이 Google Sheet, `config/automation_hub_sites.json`, `config/automation_rooms.json`, Git에 커밋되는 여러 `*_state.json` 파일에 분산돼 있다.

- WordPress 예약기는 Google Sheet의 런타임 레지스트리를 읽는다.
- Blogger 예약기는 Git 저장소의 `automation_hub_sites.json`을 읽는다.
- YouTube 예약기는 다시 Google Sheet 캘린더와 `automation_rooms.json`을 함께 사용한다.

한 시스템의 ON/OFF 또는 주소가 바뀌어도 다른 시스템에는 즉시 반영되지 않는다.

### 2. 선언된 대상 수와 실제 활성 대상 수가 다르다

`automation_rooms.json`은 총 72개 대상을 선언한다.

| 플랫폼 | 선언 | 활성 |
|---|---:|---:|
| WordPress | 27 | 27 |
| Blogger | 27 | 7 |
| YouTube | 10 | 10 |
| Tistory | 5 | 5 |
| Naver | 3 | 0 |

별도 사이트 설정 파일에는 Blogger 자체가 7개만 존재한다. 따라서 “Blogger 27개 자동화”라는 운영 기대와 실제 코드가 일치하지 않는다.

### 3. 워크플로 성공이 콘텐츠 성공을 의미하지 않는다

스케줄러는 대상이 없거나, 디스패치만 하고 끝나도 성공으로 표시될 수 있다. 반대로 실제 하위 작업은 실패할 수 있다. GitHub의 초록색 체크만 보고서는 초안 생성·품질 통과·원격 저장·URL 검증 여부를 알 수 없다.

### 4. 교차 워크플로 잠금이 없다

각 워크플로 내부에는 `concurrency`가 일부 있지만 워크플로끼리는 서로 다른 그룹을 사용한다. 따라서 다음 작업이 동시에 같은 Sheet 또는 같은 사이트를 만질 수 있다.

- WP 예약기와 Blogger 예약기
- Blogger 큐 생산자와 큐 소비자
- 승인 보드 동기화와 발행 결과 기록
- 캘린더 생성·키워드 승격·발행 상태 갱신

Google Sheet 셀을 작업 잠금으로 사용하는 방식은 원자적 비교·교환이 아니므로 두 실행이 같은 행을 동시에 소유할 수 있다.

### 5. 실행 빈도가 과도하다

활성 cron 기준으로 하루 약 500회 수준의 GitHub Actions 실행이 발생할 수 있다. 핵심 예시는 다음과 같다.

- 승인 보드: 10분마다 144회/일
- WP 예약 확인: 15분마다 96회/일
- YouTube 예약 확인: 15분마다 96회/일
- Blogger 예약 확인: 20분마다 72회/일
- Blogger 큐 처리: 24회/일
- 뉴스룸: 20회/일

대부분이 실제 콘텐츠 작업 없이 종료되어도 API 호출·로그·상태 갱신이 누적되고 장애 신호를 묻는다.

### 6. 테스트가 운영 변경을 차단하지 못한다

로컬 `tests/` 실행 결과는 186개 중 9개 실패였다. GitHub의 Automation Hub 테스트도 2026-08-31 이후 확인된 15회가 모두 실패했다. 그런데 운영 스케줄러는 계속 활성 상태였다.

주요 실패:

- Blogger 기대 개수 6/실제 7 불일치
- 전체 방 개수 69/실제 72 불일치
- Blogger 초안 강제 정책 회귀 검사 실패
- YouTube 동영상 생성 동결 정책 회귀 검사 실패
- Tistory 생성 품질 검사 실패
- 이미지 정책 감사 실패 (`PEXELS_KEY` 잔존)

즉 테스트 실패가 배포·발행의 차단문 역할을 하지 않는다.

### 7. 콘텐츠 정책이 코드와 일치하지 않는다

- Blogger 최소 품질점수 기본값은 70으로 남아 있으며 확정 운영 기준 75와 다르다.
- Blogger 라벨 수는 8~14개를 만들 수 있어 확정 기준 3~5개와 다르다.
- Blogger는 Gemini 실패 시 GPT로 재작성해 “Blogger 본문은 Gemini” 원칙과 다르다.
- WordPress 활성 진입점 주석과 실제 환경변수의 이미지 제공자 정책이 서로 모순된다.
- 테스트는 Blogger 6개, 방 69개 등 오래된 수량을 기대한다.

### 8. Git 저장소를 런타임 상태 저장소로 사용한다

WP와 Blogger 예약기는 실행 상태 JSON을 매번 Git에 커밋하고 push한다. 동시에 실행되면 pull/rebase/push 충돌이 생길 수 있고, 불확실한 HTTP 결과 뒤의 작업 소유권을 안정적으로 복구하기 어렵다.

### 9. OAuth가 목적별로 조각나 있다

Sheets/Drive, Blogger, YouTube가 서로 다른 scope와 refresh token을 사용한다. 이 분리는 맞지만, 현재는 인증 상태를 시작 전에 한 번에 검증하는 중앙 health check가 없다. 인증 오류가 콘텐츠 생성 비용을 쓴 뒤 늦게 드러날 수 있다.

## 충돌 방지 목표 구조

### 단일 데이터베이스

Sheet와 Git JSON 대신 PostgreSQL 또는 MVP 단계의 SQLite를 실행 원장으로 사용한다. Sheet는 읽기 쉬운 보고용 복제본으로만 둔다.

핵심 테이블:

- `sites`
- `credentials_health`
- `content_jobs`
- `content_versions`
- `approvals`
- `publication_attempts`
- `audit_events`

### 단일 상태 머신

허용 상태 전환만 서버가 수행한다.

`KEYWORD_RECEIVED → WP_GENERATED → WP_REVIEW → WP_APPROVED → WP_PUBLISHED_VERIFIED → BLOGGER_GENERATED → BLOGGER_REVIEW → BLOGGER_APPROVED → BLOGGER_PUBLISHED_VERIFIED`

YouTube는 `GENERATED → PRIVATE_UPLOADED → REVIEW → APPROVED → PUBLIC_VERIFIED`로 분리한다.

### 단일 작업자와 원자적 잠금

- 플랫폼별 worker는 하나만 실행한다.
- DB의 행 잠금 또는 lease를 사용한다.
- 고유키는 `(platform, destination_id, source_content_id, content_version)`로 둔다.
- 외부 API 호출 전에 attempt를 생성하고, 응답의 remote ID를 같은 트랜잭션 원장에 기록한다.
- 불확실한 응답은 새 글을 만들지 않고 원격 조회로 먼저 복구한다.

### 승인과 발행 권한 분리

- 생성 worker에는 공개 발행 권한을 주지 않는다.
- 승인 레코드가 있어야 별도 publisher worker가 동작한다.
- 초안 생성 요청의 `publish_now`는 사용자 입력으로도 변경할 수 없게 서버에서 강제한다.
- 공개 후 API 상태와 실제 URL을 모두 검증해야 완료로 기록한다.

### 재가동 조건

다음 조건을 전부 통과하기 전에는 5개 예약 워크플로를 다시 켜지 않는다.

1. WP 1개 + Blogger 1개 + YouTube 1개 canary가 승인 전 비공개를 유지한다.
2. 동일 job을 3회 재요청해도 원격 초안이 1개만 존재한다.
3. API timeout 직후 재실행해도 중복이 없다.
4. OAuth 만료를 생성 전에 탐지한다.
5. 전체 테스트가 통과한다.
6. 운영 규칙(SEO 75, Blogger Gemini, 라벨 3~5, 이미지 0~2)이 코드·테스트·UI에서 동일하다.
7. 성공 판정에 원격 ID, 편집 URL, 상태 검증 시각이 모두 존재한다.

## 결론

가장 큰 문제는 개별 API가 아니라 **여러 스케줄러·여러 설정 파일·Google Sheet가 동시에 실행 제어권을 갖는 것**이다. 안정화의 핵심은 기존 55개 워크플로를 조금씩 수리하는 것이 아니라, 한 앱의 데이터베이스와 상태 머신만 실행 권한을 갖게 만드는 것이다.
