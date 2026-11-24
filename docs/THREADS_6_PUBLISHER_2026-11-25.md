# Threads 6 publisher (2026-11-25, 런던프로젝트클로드)

Chairman 지시: 쓰레드 6개에 자동 발행, 성공 후 GitHub 저장. 기존 12-destination 게이트(인스타 6 + 쓰레드 6 전부 검증)가
인스타 미완료 때문에 쓰레드까지 막고 있어서, 쓰레드 전용 워크플로를 분리했다. 인스타 워크플로·정책은 변경 없음.

- Workflow: `.github/workflows/threads-6-publisher.yml` (cron */10, workflow_dispatch `force_now`)
- Script: `scripts/threads_6_publisher.py` (meta_12_publisher 헬퍼 재사용, 슬롯은 `config/meta_12_account_daily_policy.json` 하루 3회/계정)
- Receipts: `data/threads_6_publishing_receipts.json` — 예약(ATTEMPT_RESERVED)과 결과(PUBLISHED/NEEDS_RECONCILIATION)를 각각 main에 커밋
- 계정별 가드: 토큰/USER_ID 없으면 건너뜀 · `/me` id+handle 불일치 시 건너뜀 · seoul_journal1은 검토된 출처 큐 항목 없으면 건너뜀
- 킬스위치: repo 변수 `THREADS_6_LIVE=false`
- 필요한 시크릿/변수(META-SOCIAL 환경): `META_THREADS_{ENGLISH,JAPANESE,CHINESE,KOREAN}_SOS1`, `META_THREADS_SEOUL_JISOO1`, `META_THREADS_SEOUL_JOURNAL1` 의 `_ACCESS_TOKEN`(secret) / `_USER_ID`(variable), 그리고 `GEMINI_API_KEY`
- 상태(검증 전): 토큰 저장 여부는 이 세션에서 확인 불가(API 차단). 첫 `force_now=true` 실행 결과 로그가 실제 확인 근거.
- 미검증: 실제 발행 URL 없음. VERIFIED_COMPLETE 아님.
