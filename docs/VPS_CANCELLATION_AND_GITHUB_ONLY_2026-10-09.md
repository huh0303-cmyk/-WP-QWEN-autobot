# VPS 해지 및 GitHub-only 전환 — 2026-10-09

## 결정
- Hostinger VPS 해지 완료 (Chairman 확인, 2026-10-09). n8n-on-VPS 마이그레이션 계획(`docs/N8N_LONDON_PROJECT_MIGRATION_2026-09-26.md`)은 **폐기**.
- 모든 발행/운영은 GitHub Actions 중심으로 통일. VPS가 없으므로 "VPS에서 돈다"고 적힌 과거 문서/설정은 현재 사실이 아님 — 재확인 필요.

## 라이브 점검 결과 (2026-10-09)

### Blogspot 33 — 정상
- `blogger-33-daily-github.yml` (workflow id 374965862)가 이미 GitHub Actions에서 실행 중, 최근 5회 전부 success.
- VPS 없이도 Blogspot 발행은 영향 없음.

### WordPress 25 immediate isolated publish — 버그 발견 및 조치
- 최근 4회 연속 "failure"였으나, 실제로는 24개 사이트 중 **k-visa365.com 하나만** 실패 (per-site isolation 정상 작동).
- 원인: `scripts/autopost_mega.py`의 `plain_len=...` 할당 라인이 과거 커밋(f3239ec, 2026-10-09 03:03 UTC)에서 직전 줄의 `#` 주석과 리터럴 `\n` 텍스트가 한 물리적 줄에 뭉쳐지면서, 실제 코드가 주석 처리되어 `NameError: plain_len not defined` 발생.
- 현재 HEAD(910dd39)에는 이미 해당 라인이 정상 분리되어 있어 문법 검증(`py_compile`) 통과 — 같은 세션 내 다른 트랙에서 선조치된 것으로 보임.
- 검증을 위해 `daily-network-publish.yml`(id 339777797)을 수동 workflow_dispatch로 재실행함 (run 37884784939). 결과는 이 문서에 후속 기록하거나 activity ledger 참조.

### Tistory Daily Plan — 버그 수정 (이번 세션)
- 최근 50회 실행 중 32회 실패.
- 원인: `build_plan()`은 사이트별 예외를 개별 처리해 `plan["failures"]`에 기록하지만, `main()`이 `failures`가 하나라도 있으면 전체를 종료 코드 1로 끝내버려 — 하루에 2~3개만 선택되는 구조상 한 사이트의 일시적 실패(RSS/키워드 조회 등)가 나머지 정상 사이트의 발행까지 전부 막음.
- 수정 커밋: `910dd39` — "fix: one flaky site no longer zeroes out the whole day's Tistory output"

## 남은 작업
1. VPS 의존으로 문서화된 컴포넌트 재점검: control_center 대시보드 앱, Tistory/Naver 브라우저 로그인 러너(과거 "persistent browser runner on VPS"로 기록됨) — GitHub Actions에서 어떻게 대체되는지/이미 대체됐는지 확인 필요.
2. `N8N_LONDON_PROJECT_MIGRATION_2026-09-26.md` 등 VPS 전제 문서에 "폐기됨" 표시 남기기 (전체 재작성은 보류, 혼선 방지 목적).
3. daily-network-publish 재실행(run 37884784939) 결과 확인 후 k-visa365.com 정상 발행 확정.

## 비고
- 사용자 요청으로 크롬 확장프로그램("Korea365 단타 실행기")을 별도 제작 — GitHub Actions workflow_dispatch를 브라우저 버튼 클릭으로 즉시 실행. 레포에는 포함하지 않고 파일로 직접 전달.
