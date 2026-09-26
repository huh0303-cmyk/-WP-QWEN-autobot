# 런던프로젝트클로드 — 상태 원장 (State Ledger)

**이 파일을 먼저 읽어라.** 어떤 세션이든(토큰 소진으로 끊긴 뒤 새 세션이든) 이
문서 하나만 읽으면 지금까지 뭐가 됐고 다음에 뭘 해야 하는지 알 수 있어야 한다.
매 세션 끝에 이 파일 맨 위에 새 항목을 추가한다 (최신이 위로).

관련 문서: `docs/LONDON_PROJECT_CLAUDE_CHARTER.md` (목표/원칙, 거의 안 바뀜)

---

## 2026-09-26 (4차) — 두 워크플로우 실제 실행 완료, 진짜 증거 확보

GH_TOKEN으로 GitHub API 직접 호출해서 두 워크플로우를 실제로 돌렸다 (가짜
"완료" 아님 — run ID/아티팩트 다운로드로 검증).

### 1) `AdSense ads.txt — 26-site read-only audit` (run 36233819256, success)

27개 전체 ads.txt: **HTTP 200, 정확한 퍼블리셔 라인, FAIL 0건.** 공통 WARN 1개
(`ipv6_probe_failed_from_runner`)뿐인데, **이미 승인된 k-health365.com에도
똑같이 뜬다** — 즉 사이트 문제가 아니라 GitHub Actions 러너 자체가 IPv6 아웃바운드가
없어서 생기는 감사 도구 쪽 한계. **결론: ads.txt/DNS는 24개 미승인 사이트의
원인이 아니다.**

### 2) `Ensure required AdSense pages (27 sites)` (run 36233910201, success)

- **이미 4페이지(About/Contact/Privacy/Disclaimer) 전부 있음 — 12개**:
  koreamedicaltour.com, koreainvest365.com, koreainsurance365.com,
  kfinance365.com, koreataxnlaw.com, koreacrypto365.com, krealestate365.com,
  ktech365.com, kskin365.com, oliveyoungkorea.com, kworld365.com, k-trip365.com
  → **이 12개는 필수 페이지 부재가 애드센스 미승인 원인이 아니다.**
- **일부 생성/일부 오류 — 3개**: k-health365.com(Privacy·Disclaimer 신규 생성,
  About·Contact는 503으로 실패 — 이미 승인된 사이트라 급하지 않음),
  ki-korea.com(Disclaimer만 생성, 나머지 3개 503/타임아웃), k-visa365.com(4개
  전부 타임아웃/403 실패)
- **네트워크 차단으로 시도조차 못함 — 9개** (24개 타깃 중): kstudy365.com,
  studyinkorea365.com, kieca-korea.org, ksa-korea.org, sis-korea.com,
  jobkorea365.com, jobinkorea365.com, jobkoreaglobal.com, korea365.org
  → 전부 "Connection aborted / reset by peer". koreawedding365.com부터
  신문사 2개까지 연속으로 같은 에러가 난 패턴을 보면, 여러 사이트가 같은
  공유 IP(151.106.124.169, 이전 ads.txt 감사에서 확인됨)를 쓰고 있어서
  **한 러너에서 짧은 시간에 여러 사이트를 연달아 쓰기 요청하니 호스팅단
  WAF/레이트리밋이 그 IP를 통째로 막은 것으로 보인다.** 실제 페이지
  누락 여부는 아직 모름 — 재시도 필요.

### 24개 타깃 사이트 현재 상태 요약

| 상태 | 개수 | 사이트 |
|---|---:|---|
| 필수페이지 확인 완료 (원인 아님) | 12 | 위 목록 |
| 일부만 확인/생성, 재시도 필요 | 2 | ki-korea.com, k-visa365.com |
| 시도 실패, 완전 재시도 필요 | 1 | koreawedding365.com |
| WAF 추정 차단으로 미확인 | 9 | 위 목록 |

**솔직한 결론**: 24개 중 12개는 "필수 페이지 부족"이 애드센스 미승인 원인이
아님을 확인했다. 나머지 12개는 아직 확인 못 했다 — 추측 안 함. ads.txt는
27개 전부 정상이라 원인에서 제외. **다음 세션/재시도 때는 한 번에 몰아치지
말고 사이트당 딜레이를 늘리거나(현재 0.5초 → 5초 이상), 배치를 나눠서
(`workflow_dispatch`에 `ONLY_SITE` 같은 파라미터 추가 검토) WAF 차단을
피해야 한다.** 애드센스 승인 자체의 진짜 원인(페이지 문제가 아니라면
콘텐츠 품질/사이트 나이/트래픽 등)은 이 두 감사로는 안 보인다 — 별도 조사
필요.

원본 증거: run 36233819256 아티팩트(`adsense_audit_20260926T094829Z.md/json/csv`),
run 36233910201 아티팩트(`ensure_required_pages_results.txt`) — GitHub Actions
run 페이지에서 재다운로드 가능.

---

## 2026-09-26 (3차) — 소유권 잠금 + 런던프로젝트GPT와 트랙 분리 확정

Chairman 직접 지시(18:41 KST): *"다 별도야.. 런던프로젝트클로드는 온전히
너꺼고 너가 책임자고 책임도 너가 진다."*

- `config/LONDON_PROJECT_CLAUDE_OWNER_LOCK_2026-09-26.md` 신설 — 같은 저장소에
  ChatGPT가 병행 운영 중인 "런던프로젝트GPT"(18:25/18:35 KST에 자체 owner-lock
  커밋 + `control_center/london_gpt_app.py` 추가한 것을 git log로 발견)와
  **완전 별도, 상호 위임 없음**을 명문화.
- 두 트랙의 "선언 범위"는 크게 겹치지만(둘 다 사실상 London Project 전체를
  언급), 런던프로젝트클로드는 **실제로 만지는 파일을 의도적으로 좁게
  유지**해서 같은 파일 동시 수정 충돌을 최소화하기로 함 (소유 파일 목록은
  owner-lock 문서 참고).
- 규칙 추가: 목록 밖 파일을 고치기 전엔 `git log --oneline -5 -- <path>`로
  최근 변경자 확인 — 이번 세션 초반 `ensure_required_pages.py`를 안 읽고
  덮어쓸 뻔한 사고, 그리고 방금 발견한 런던프로젝트GPT의 동시 커밋 둘 다
  같은 종류의 리스크였음.

---

## 2026-09-26 (2차) — APPROVED_GROUP 모순 해소 (Chairman 확인)

Chairman이 직접 확인: **애드센스 승인은 k-health365.com 1개뿐**이다.
`scripts/audit_adsense_sites.py`의 `APPROVED_GROUP`에 잘못 들어 있던 6개
(koreataxnlaw.com, jobkoreaglobal.com, studyinkorea365.com, korea365.org,
sis-korea.com, krealestate365.com)를 제거하고 k-health365.com만 남김. 커밋함.
이 6개 사이트도 **24개 미승인 타깃에 포함**된 것으로 확정 — 아래 부록 목록은
이미 24개로 맞게 정리돼 있었으므로 추가 수정 없음.

이 상수는 리포트 라벨용일 뿐 ads.txt/DNS 실제 감사 로직에는 영향을 주지 않았으므로,
지금까지 나온 감사 결과의 FAIL/WARN/OK 판정 자체는 이 오류로 왜곡되지 않았다.

---

## 2026-09-26 (1차) — 개설 세션 (Claude Sonnet 5)

### Chairman 지시 원문 요지
- "런던프로젝트클로드" 이름으로 완전 독립 트랙 운영
- 안정성 최우선, 궁극 목표는 수익, 1차 목표는 구글 애드센스 승인
- 현재 1개(k-health365.com)만 승인, 나머지 24개 WP는 1일 1포
- 신문사 2개는 별도 운영 (1일 3~10포, 속보)
- Blogspot은 1일 1포
- 모든 진행 상황을 깃헙에 남겨서 다음 세션이 바로 이어받게 할 것

### 사실 확인 (코드/커밋 근거)

1. **발행 빈도 정책은 이미 사용자 지시와 일치**: WP24 1일1포 / 신문사2 1일
   3~10포(상한10) / 블팟 1일1포 구조가 `docs/NEWSROOM_INDEPENDENT_PUBLISHING_POLICY.md`
   + `.github/workflows/daily-publication-floor.yml`(매시 13분, 누락분만 채움) +
   `.github/workflows/newsrooms-daily-publisher.yml`에 이미 구현돼 있음.
   **새로 만들 필요 없었음.**
2. **24개 WP 타깃 사이트 확정**: `daily-publication-floor.yml`의 시크릿 주입
   목록을 근거로 k-health365.com(이미 승인)을 제외한 24개 사이트를 특정함
   (아래 부록 목록 참고).

### ⚠️ 이번 세션 중 발생한 실수와 정정 (숨기지 않고 기록)

- **실수**: `scripts/ensure_required_pages.py`라는 이름의 스크립트가 이미
  존재하는지 확인하지 않고 같은 이름으로 새로 작성해서 **덮어썼음**. 기존
  스크립트는 내가 새로 쓴 것보다 훨씬 성숙했다 — 27개 사이트 전체 대상,
  About/Contact/Privacy/**Disclaimer** 4종, 한국어/영어 사이트별 언어 분기,
  slug 우선+제목 길이 제한 이중 매칭(과거 kieca-korea.org에서 페이지빌더가
  CSS 클래스명 때문에 오탐된 실제 사고를 반영해 방어 코드가 들어있음), 사이트별
  예외 처리(과거 kskin365.com SSL 오류로 전체 스크립트가 죽어서 결과가 통째로
  날아간 사고 이후 추가된 방어 코드)까지 갖춘 프로덕션급 코드였다.
- **정정**: `git checkout HEAD -- scripts/ensure_required_pages.py`로 즉시
  원복. 내가 새로 쓴 버전은 폐기. **다음 세션 규칙: 뭔가 새로 만들기 전에
  반드시 `git log --oneline -- <path>` 또는 `find`로 동일/유사 이름부터
  확인한다.**
- **추가 발견**: `scripts/audit_adsense_sites.py`(이미 존재, ads.txt를
  DNS/IPv4/IPv6 강제조회+robots.txt 차단여부까지 검사하는 정교한 감사 도구)의
  `DOMAINS` 목록 26개에 **kskin365.com이 빠져 있었음** — `site_registry.py`
  정본에는 27개로 있는데 이 감사 도구에서는 한 번도 감사된 적이 없었다는 뜻.
  **이번 세션에서 목록에 추가함 (코드 수정, 커밋 대상).**
- **모순 발견 → 해소됨 (위 2026-09-26 (2차) 항목 참고)**: `audit_adsense_sites.py`의
  `APPROVED_GROUP`에 7개가 "승인됨"으로 잘못 하드코딩돼 있던 것을 Chairman이
  "k-health365.com 1개뿐"이라고 직접 확인해줘서 정정 완료.

### 이번 세션에서 실제로 변경·추가한 것 (커밋 대상)

1. `scripts/audit_adsense_sites.py` — `DOMAINS`에 kskin365.com 추가 (27개로 보정).
2. `.github/workflows/ensure-required-pages.yml` **신규** — 기존
   `scripts/ensure_required_pages.py`(27개 사이트, 4개 필수 페이지 생성)를
   **처음으로 워크플로우에 연결**. `git log`로 확인한 결과 이 스크립트는
   한 번도 워크플로우에서 호출된 적이 없었다 — 코드는 있는데 자동 실행 경로가
   없던 상태. `workflow_dispatch` 수동 트리거만 (스케줄 자동화는 최소 1회
   결과 검토 후).
3. `docs/LONDON_PROJECT_CLAUDE_CHARTER.md` — 이 트랙의 헌장, "새 코드 전에
   기존 코드부터 읽는다" 원칙 추가(이번 실수를 반영).
4. `docs/LONDON_PROJECT_CLAUDE_STATE.md` — 이 문서.
5. `CLAUDE.md`에 이 STATE 문서를 필수 선행 독서 목록 8번으로 추가.

### 아직 확인 못 한 것 (솔직히 — 안 했다고 함)

- `ensure-required-pages.yml`이 실제로 GitHub Actions에서 실행된 적 없음
  (코드만 연결, 트리거는 아직 안 함). 이 세션은 24개 사이트의 WP 비밀번호에
  접근할 수 없어서(로컬 샌드박스에는 GitHub Secrets가 없음) 직접 실행해 볼
  수 없었다.
- `audit_adsense_sites.py`도 이번 세션엔 실행 안 됨 — 위와 같은 이유.
  **다음 세션이 GitHub Actions에서 이 두 워크플로우를 실제로 1회씩 수동
  트리거해서 진짜 결과를 봐야 한다.** 숫자를 추측하지 않는다.
- APPROVED_GROUP 모순 (위 참고) — Chairman 확인 대기.

### 다음 세션이 할 일 (순서대로)

1. GitHub Actions → `AdSense ads.txt — 26-site read-only audit`(이름은 아직
   26이지만 코드는 27개 검사함, 이름 갱신은 후순위) 수동 트리거 → 결과(JSON/CSV/MD
   아티팩트) 확인.
2. 결과에서 FAIL/WARN 사이트와 원인(`issues` 필드: ads_status,
   publisher_line_mismatch, ads_format, robots_blocks_google 등) 확인.
3. GitHub Actions → `Ensure required AdSense pages (27 sites)` 수동 트리거 →
   `ensure_required_pages_results.txt` 아티팩트로 어떤 사이트에 어떤 페이지가
   신규 생성됐는지 확인.
4. ~~Chairman에게 APPROVED_GROUP 재확인~~ → 완료 (2026-09-26 (2차)): 승인은
   k-health365.com 1개뿐으로 확정, 코드 정정 커밋됨.
5. 두 감사 결과를 종합해 "24개 중 몇 개가 요건 충족, 몇 개가 뭐가 부족한지"
   표로 이 STATE 문서에 기록.
6. 이 STATE 문서 맨 위에 새 날짜 섹션 추가해서 기록 이어가기.

### 부록 — 24개 WP 타깃 사이트 (k-health365.com 제외, 신문사 2개 제외)

koreamedicaltour.com, koreainvest365.com, ki-korea.com, koreainsurance365.com,
kfinance365.com, koreataxnlaw.com, koreacrypto365.com, krealestate365.com,
ktech365.com, kskin365.com, oliveyoungkorea.com, kworld365.com, k-trip365.com,
k-visa365.com, koreawedding365.com, kstudy365.com, studyinkorea365.com,
kieca-korea.org, ksa-korea.org, sis-korea.com, jobkorea365.com,
jobinkorea365.com, jobkoreaglobal.com, korea365.org

### 커밋 (이번 세션)

- (이 턴 마지막에 커밋 실행 — SHA는 다음 세션이 `git log`로 확인)
