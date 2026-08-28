# 시스템 정상화 및 소액 E2E 검증 보고서 — 2026-08-28

최상위 기준은 `MASTER_MONETIZATION_STRATEGY_2026.md`이다. 이 작업에서는 새 사이트·채널·유료 API를 추가하지 않았고, DNS/SSL/AdSense 등록을 변경하지 않았으며, 모든 쓰기 테스트를 DRAFT/PRIVATE 범위로 제한했다.

## A. AdSense / ads.txt

- 검사 범위: 요청된 WordPress 도메인 26개 전수검사
- GitHub Actions 실행: [33096434789](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33096434789) — Success, 1분 4초
- 결과: OK 0 / WARN 26 / FAIL 0
- 공통 정상 항목: 26개 모두 `/ads.txt` HTTP 200, 58 bytes, `text/plain`, 정확한 `pub-3456727916386941`, WordPress REST 200, robots 차단 없음, IPv4 강제 요청 200, root/www canonical 정상
- 공통 경고: GitHub 호스팅 러너에서 26개 모두 IPv6 강제 접속 실패(`ipv6_probe_failed_from_runner`)
- 승인군과 Not Found군: 승인군 7개에도 같은 IPv6 경고가 있으며 응답시간도 승인군 약 677ms, 문제군 약 658ms로 유의미한 차이를 확인하지 못했다. 따라서 AAAA 문제만으로 AdSense 상태 반복을 설명할 수 없다.
- DNS 차이: 대부분 A `151.106.124.169`; `kworld365.com`은 별도 A 레코드 집합을 사용한다. 이 차이만으로 현재 현상과의 인과관계는 입증되지 않았다.
- 실제 수정: 반복 가능한 read-only 감사 스크립트, JSON/CSV/Markdown 출력, 수동 GitHub Action, 단위 테스트 추가. 실행 환경의 IPv6 미지원은 사이트 장애가 아니라 경고로 분류한다.
- 변경하지 않은 항목: AAAA/A/CNAME/TXT/MX, SSL, 기존 ads.txt, AdSense 사이트 등록, control site `k-trip365.com`
- Hostinger 권장 조치: 즉시 DNS 변경 없음. 다음 단계는 승인군/문제군 각각의 Hostinger origin 로그에서 `Google-adstxt` 요청 도달 여부와 장기 응답시간을 같은 기간으로 비교하는 것이다.

## B. Tistory

- 현재 자동화 가능 수준: 저장소의 publisher는 `InteractiveEditorPublisher`이며 GitHub Actions 무인 환경에서는 `local_login_required` 또는 `official_write_api_unavailable`로 안전하게 중단한다.
- 발견 문제: 수동 workflow에서 Tistory 선택 경로 부족, DRAFT 강제 및 중복 본문/출처 검사 불충분, 계정 누락 및 empty run의 불명확한 성공 처리 가능성
- 수정: `platform-publish.yml`, `process_platform_queue.py`, `content_identity.py`에서 Tistory/Naver 수동 필터, DRAFT 강제, 제목·본문·source 중복 차단, 계정 누락 기록, empty manual run 실패, publisher 실패 시 non-zero 종료를 적용했다.
- 실제 draft 생성: 불가. 로컬 로그인 세션과 안전한 대화형 편집기 연결이 없으므로 쓰기 테스트를 실행하지 않았다.
- 추가 인증: 필요. ID/password를 Secret에 넣는 Selenium 우회는 구현하지 않았다.

## C. Blogger 6개 DRAFT E2E

공통 원칙: Blogger 본문은 Gemini만 사용하고 승인 Replicate 이미지 경로만 사용한다. PUBLIC 발행은 실행하지 않았다. Google Sheet `자동화_플랫폼계정`에 검증된 기존 Blog ID 6개를 등록했다.

| 사이트 | 결과 | 실행 | 생성 제목 / draft ID | 품질·이미지 | 실패 이유 |
|---|---|---|---|---|---|
| blogger_jobkorea365 | FAIL | [33095072537](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33095072537) | 없음 / 없음 | 생성 전 중단 | 새 공개 WordPress source 없음 |
| blogger_ktrip365 | FAIL | [33095634430](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33095634430) | 없음 / 없음 | 1차 95, 2차 labels 형식 실패 | YMYL 문구/출력 형식 quality gate 실패 |
| blogger_kvisa365 | FAIL | [33095874009](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33095874009) | 없음 / 없음 | 생성 전 중단 | 새 공개 WordPress source 없음 |
| blogger_koreainsurance365 | FAIL | [33095096301](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33095096301) | 없음 / 없음 | 생성 단계 실패 | workflow exit 1; 실제 draft 없음 |
| blogger_koreamedicaltour365 | FAIL | 생성 [33095990391](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33095990391), 전송 [33096305440](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33096305440) | `Ensuring Safe Post-Surgery Recovery: Choosing Accommodation for` / 없음 | score 100, similarity 0.003, Replicate-approved | Blogger API 403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT` |
| blogger_kstudy365 | FAIL | [33095111928](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/33095111928) | 없음 / 없음 | 생성 단계 실패 | workflow exit 1; 실제 draft 없음 |

실제 Blogger draft는 0/6이다. 의료관광 큐 항목은 `publish_now=FALSE`였으며 API 403 후 `failed`로 기록됐다. 동일 OAuth refresh token의 Blogger write scope를 사용자가 재승인하기 전에는 추가 생성·전송을 중단한다. publisher가 실패했는데 workflow가 성공으로 보이던 문제는 수정하여 이후에는 실패 결과가 non-zero로 종료된다.

## D. WordPress

- 요청된 26개 mapping: `site_id`, domain, language/persona, credential 환경변수 이름과 REST 접근을 검사했다. 26개 모두 domain/REST가 유효하다.
- 저장소에는 범위 밖 추가 설정 `kskin365.com` 1개가 있어 총 27개다. 사업 판단이 필요하므로 삭제하지 않았다.
- DRAFT enforcement: workflow/runtime에서 WordPress 생성물은 draft로 강제한다.
- Gemini fallback: WordPress 본문 생성 경로의 Gemini fallback을 제거했다. 레거시 함수명은 호환성을 위해 남아 있지만 내부는 GPT-only이며 GPT를 사용할 수 없으면 실패한다.
- Blogger 전용 Gemini 경로는 유지했다.

## E. GitHub / 테스트 / 비용

### 변경 파일

- `.github/workflows/adsense-infrastructure-audit.yml`
- `.github/workflows/blogger-rewrite.yml`
- `.github/workflows/platform-publish.yml`
- `.gitignore`
- `automation_hub/content_identity.py`
- `scripts/audit_adsense_sites.py`
- `scripts/autopost_mega.py`
- `scripts/process_platform_queue.py`
- `scripts/queue_blogger_rewrite.py`
- `tests/test_adsense_audit.py`
- `tests/test_content_identity.py`
- `tests/test_master_policy_regressions.py`
- `docs/SYSTEM_AUDIT_2026-08-28.md`

### 구형/충돌 경로 비활성화

- WordPress 본문의 Gemini fallback 차단
- Tistory의 GitHub 무인 로그인 우회 미구현/차단 유지
- 플랫폼 publisher 오류를 성공으로 기록하던 workflow 동작 제거
- Blogger source REST의 GitHub IPv6 경로 문제를 Actions에서 IPv4로 제한

### 커밋

- `ffc87ce969aad791ac084b221a6e172db82eb7df` — read-only AdSense 감사
- `ea76e358bc08643888f773cd8287f304f7e152d4` — Tistory/플랫폼 큐 안전장치
- `3951bed9bb7039f2d6c4ca97e49ea4e53265babb` — WordPress Gemini fallback 금지
- `66f947654ae21f31120027644f57c451d129ff60` — Blogger source IPv4 안정화
- `9bc52f4e630b61a3ab3300000f791c8cfe880d82` — publisher 오류 시 workflow 실패 처리

### 검증 결과

- repository unit/regression tests: 63 passed
- active MASTER policy audit: PASS
- GitHub Actions workflow YAML: 31 files PASS
- live read-only AdSense audit: Action Success, 26개 결과 산출
- 참고: 저장소 루트 전체를 pytest 자동 수집하면 `scripts/test_*.py`의 수동 운영 도구가 외부 자격증명/Playwright를 즉시 요구한다. 정식 회귀 suite인 `tests/`는 전부 통과했으며, 운영 스크립트를 실행하지 않도록 범위를 분리했다.

### 비용

- 신규 유료 API/SaaS: 0
- AdSense 진단: 외부 유료 API 비용 0
- Blogger 검사 중 실제 호출: k-trip 품질 재작성과 koreamedicaltour 생성/이미지에 기존 Gemini/Replicate가 최소 단위로 호출됨
- 실제 청구 금액: 비용 API/청구 연결이 없어 확인 불가. 숫자를 추정하지 않고 `연결 필요`로 기록한다.

### 남은 차단 사항과 다음 작업

1. Google OAuth refresh token을 Blogger write scope로 사용자 재승인한 뒤, 기존 ready 큐 1건만 DRAFT 전송 재시험
2. 새 source가 없는 3개 사이트는 콘텐츠 생성 없이 정상 skip 정책을 확정하고, source가 생긴 뒤 각각 1건만 시험
3. insurance/study 생성 실패 원인의 구조화 로그를 Sheet에 남기도록 보강
4. Tistory는 로컬 대화형 로그인 세션 방식이 확정되기 전까지 자동 쓰기 중단 유지
5. Hostinger origin 로그를 승인군/문제군 동일 기간으로 비교해 AdSense crawler 도달성 추적

North Star는 월 순수익 1,000,000원이며, 현재 단계는 대량 발행이 아니라 측정·판단·개선 기반의 정상화 상태다.
