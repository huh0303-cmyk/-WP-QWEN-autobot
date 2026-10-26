# 통제실 통계 고정 기준

- 기준 버전: kst0700-v1. 변경 시 과거 자료와 자동 혼합하지 않는다.
- 실행 위치: GitHub Actions only. VPS timer/systemd installation is retired.
- A scheduled workflow must be the single owner of the 07:00 Asia/Seoul collection window; do not create a parallel cron or server timer.
- 실제 API 수집·검사에는 시간이 걸린다. 기준 시각과 실제 항목별 확인 시각을 함께 보관한다. 실행 시작이 10분 이상 지연되면 정기 자료로 확정하지 않는다.
- 일일 방문자수는 전날 7시부터 오늘 7시 수집까지 누적 원천 조회수의 증가분이다. WP·Blogger 자체 조회수이며 고유 사용자 수를 보장하는 GA4 지표가 아니다.
- 일일 증감은 직전 24시간 증가분과 비교한다. 누적 증감은 전날 누적값을 뺀다. 누적 카운터가 초기화·감소하면 방문 수를 계산하지 않는다.
- 총 발행 글수는 공개 글 URL 전체 목록으로 확인한다. 초안·페이지·카테고리는 제외한다.
- Google 색인 발행 글수는 같은 공개 글 URL 목록을 URL Inspection API로 검사해 PASS만 센다. 일부라도 검사 실패면 전체 색인 글수는 미확인, 확인된 수와 실패 수는 별도 표시한다.
- 색인 API는 Google이 보관한 검사 정보를 제공하므로 실시간 검색 노출을 보장하지 않는다.
- 전날의 같은 버전 정기 자료가 없으면 증감을 만들지 않는다. 첫 날은 누적·총글·색인 원값부터 보관하고, 두 번째 날부터 24시간 방문 수, 세 번째 날부터 방문 수 증감을 계산한다.
- 정기 자료: data/core_metrics_daily_history.json 및 core_metrics_daily_latest.json. 하루 한 번 확정하며 수동 재검사로 덮어쓰지 않는다.
- 임시 자료: data/core_metrics_latest.json. 정기 자료가 있으면 통제실은 정기 자료를 우선한다.
- 유료 AI·글 발행은 호출하지 않는다. 통계 수집은 read-only API만 사용한다.

## GitHub Actions requirements
- Keep exactly one scheduled workflow responsible for this metric set.
- Use GitHub Actions secrets/environment variables for API credentials; never commit credentials.
- Upload a sanitized artifact and/or persist an explicit history file with the run date, source timestamps, and per-source failure counts.
- If no GitHub-native scheduler currently writes these files, report metrics as stale/unverified; do not imply the retired VPS timer is still running.
