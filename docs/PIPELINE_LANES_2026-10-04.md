# 파이프라인 레인 분리 (WP / Blogspot / YouTube / SNS) — 2026-10-04

Chairman 요청(2026-10-04): "WP, blogspot 이두개만 따로 해줘. 유튜브와 SNS따로 나눠줘."
배경(2026-09-18): 통합 관제실이 한 플랫폼 문제로 전체가 멈추는 현상.

## 이전 구조 (문제)
`control_center/operations.py`의 `Store` 하나(SQLite 1개, `jobs` 1개 테이블)와 `Worker` 1개가
WordPress·뉴스룸·Blogspot·Tistory 작업을 모두 처리했다. 한 사이트의 stuck 작업, 느린 GitHub 호출,
DB 락이 모든 플랫폼을 동시에 멈출 수 있었다.

## 현재 구조
| 레인 | 대상 | DB 파일 | 워커 스레드 | 풀 |
|---|---|---|---|---|
| wordpress | 일반 WP + 뉴스룸 2 (`wp25`, `news2`, `wp_*`) | `control-operations-wordpress.sqlite3` | `receipts-wordpress` | 4 |
| blogspot | Blogspot 33 (`blogspot33`, `blogspot_*`) | `control-operations-blogspot.sqlite3` | `receipts-blogspot` | 4 |
| youtube | YouTube 채널 (`youtube_*`) | `control-operations-youtube.sqlite3` | `receipts-youtube` | 2 |
| sns | SNS 계정 (`sns_*`) | `control-operations-sns.sqlite3` | `receipts-sns` | 2 |
| tistory | Tistory (`tistory5`, `tistory_*`) — 요청 범위 밖이라 어느 쪽에도 묶지 않고 별도 유지 | `control-operations-tistory.sqlite3` | `receipts-tistory` | 2 |

- 코어 DB(`control-operations.sqlite3`)는 세션/CSRF 비밀값과 레거시 작업표만 보관한다.
- 시작 시 레거시 작업을 플랫폼별 레인 DB로 **1회 복사**한다(`lanes.migrate_legacy`). 레거시 파일은 삭제·수정하지 않으므로
  이전 릴리스로 롤백해도 작업이 그대로 있다. 중복 실행(gunicorn 다중 워커)에도 안전(`INSERT OR IGNORE`).
- `/api/operations` 응답에 `lanes`(레인별 활성/확인필요/실패/마지막 발행 시각, 워커 alive/stalled/last_error)가 추가됐다.
  한 레인의 DB/워커가 실패해도 그 레인만 오류로 표시되고 나머지는 정상 응답한다.
- 같은 사이트 ID가 서로 다른 레인에 있어도 충돌하지 않는다. 같은 레인 안의 중복 클릭 보호는 그대로다.

## 의도적으로 바꾸지 않은 것 (미검증/범위 밖)
- YouTube 실행 경로(`/trigger/youtube-batch` → 앱 내 스레드 + 채널별 `bulk_publish_state_youtube_*.json`)와
  SNS 실행 경로(`social-topic-publish.yml`)는 원래부터 이 공용 큐를 쓰지 않았고, 이번에 재배선하지 않았다.
  두 레인은 큐·워커·상태가 분리되어 준비돼 있지만, 현재 그 경로의 작업이 레인 큐로 들어오지는 않는다.
- `orchestrator.py`의 `provider_health`(공급자 장애/쿼터 상태)는 코어 DB를 그대로 공유한다. 공급자 장애는 전 레인에
  공통이라 의도적으로 유지했다. 레인별로 나누려면 별도 결정이 필요하다.
- 미배포: 브랜치 `split-pipeline-lanes-2026-10-04`. `main`에 합치면 `deploy-to-vps.yml`이 VPS를 재배포한다.

## 검증
- `tests/test_lanes.py` 신규 (레인 매핑, DB/워커 분리, 레인 간 비차단, 한 레인 실패 격리, 레거시 이전·멱등·롤백 안전).
- 기존 `tests/test_operations.py` 31개 통과. `tests/test_control_center.py::test_visitor_deploy_uses_current_wordpress_secret_names`는
  변경 전 `main`에서도 실패(없는 `deploy-visitor-api.yml` 참조) — 이번 변경과 무관한 기존 실패.
