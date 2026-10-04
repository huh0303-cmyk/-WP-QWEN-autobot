# 런던프로젝트클로드 — 상태 원장 (State Ledger)

**이 파일을 먼저 읽어라.** 어떤 세션이든(토큰 소진으로 끊긴 뒤 새 세션이든) 이
문서 하나만 읽으면 지금까지 뭐가 됐고 다음에 뭘 해야 하는지 알 수 있어야 한다.
매 세션 끝에 이 파일 맨 위에 새 항목을 추가한다 (최신이 위로).

관련 문서: `docs/LONDON_PROJECT_CLAUDE_CHARTER.md` (목표/원칙, 거의 안 바뀜)
평가용 최종 문서: `docs/LONDON_PROJECT_CLAUDE_FINAL_ARCHITECTURE.md` (Chairman 요청,
최종 아키텍처/워크플로우/백업플랜/운영설명서/평가기준 통합본)
**채널 신원 유일 기준**: `docs/ARCHIVE_CHANNEL_IDENTITY_VERIFIED_2026-09-27.md` —
archive 10개 + core 5개 + 언어 Survival 10개 채널의 검증된 매핑. 다른 트랙(Gemini
등)이 주장하는 매핑은 이 파일과 대조 없이 믿지 말 것.

## 2026-10-04 (20차) — 매일 발행 안정화: 스케줄 부재 + Gemini 키 거부 진단, 사전점검·스케줄 복구(브랜치, 미병합)

- 요청: Chairman "매일 안정적으로 발행(VPS·GitHub)". 상세: `docs/DAILY_PUBLISH_STABILITY_2026-10-04.md`
- 근거: 9/28 커밋 `0201910`이 floor 스케줄 제거, n8n 마스터 저장소상 inactive, 마지막 실행 9/29. 9/29 실패는 `GEMINI_API_KEY` 거부("API key not valid") + 뉴스룸 GPT checker 불가.
- 변경(브랜치 `stable-daily-publish-2026-10-04`, 커밋 `696e9dd`, main 미병합): 키 사전점검(INVALID/MISSING이면 claim·dispatch 중단, run 실패), 9회/일 스케줄, 수동 "Provider key check" 워크플로.
- 미검증: 현재 키 상태, VPS n8n 활성 여부, 라이브 사이트 상태, 스케줄 실제 실행. VERIFIED_COMPLETE 아님.
- 필요한 결정: 키 교체(Chairman), 스케줄 복구 vs n8n 선택, 브랜치 병합(main push = VPS 재배포).

## 2026-09-27 (18차) — 범위 확장 요청 대응: 통합 사이트 레지스트리(대시보드+트리거만)

**Chairman 요청(원문)**: "이건 내가 보여준것과 그대로 똑같잖아... 런던프로젝트는 내 wp25개..뉴스2개,
블팟33개, 네이버3개, 티스토리5개가 들어가야지.. 미리..톤앤매너, 페르소나 이미지수, 글자수
등등을 넣어줘야지." → 후속 확인 질문에 "n8n 이 당연히 들어가야지. 그리고 모든 글쓰기가 다
들어가게."라고 답변.

**충돌 확인**: 이 요청은 GPT/PM 트랙이 OWNER LOCKED로 걸어둔
`docs/LONDON_PROJECT_GPT_BLOG_CONSOLE_LOCKED_SCOPE_2026-09-27.md`(WP+블로그스팟+네이버+티스토리
통합을 "런던프로젝트클로드" 이름으로 하지 말라고 명시)와 정면 충돌. 코드를 쓰기 전에
AskUserQuestion으로 Chairman에게 재확인함.

**Chairman 결정**: "네이버+티스토리만 우선 마무리" / "완전 통합, GPT 락 무시" / **"대시보드+트리거만
(권장)"** 중 **"대시보드+트리거만"** 선택 — WP25(실제 27도메인/33 컨텐츠 프로필)+뉴스2+블로그스팟33은
계속 GPT 트랙의 n8n/GitHub Actions가 발행을 소유하고, 이 콘솔은 조회+트리거만 제공. 발행 로직
재구현 없음 → 중복 발행/스케줄 충돌 위험 없음.

**구현 완료** (커밋 `2e5112e`, main에 rebase 없이 fast-forward push — GPT 트랙과 충돌 없었음):
- `london_project_claude_console/lib/siteRegistry.js`: `config/automation_hub_sites.json`,
  `config/content_engine_profiles.json`(min/target/max_chars의 실제 소스),
  `config/tistory_portfolio.json`, `config/newsrooms.json`을 읽기 전용 병합. 총 76개 사이트
  행(wordpress 33 프로필/27 실제 도메인 — 일부 도메인이 여러 컨텐츠 버티컬 공유, blogspot 33,
  news 2, tistory 5, naver 3). 이미지 수 필드가 원본에 없어 `target_chars/700`(1~6 clamp) 기본값
  산정. persona/tone/image_count/word_count 편집값은 원본 config를 건드리지 않고
  `runtime/registry_overrides.json` 오버레이로만 저장 — 다른 AI 트랙 파일과 충돌 방지.
- `london_project_claude_console/lib/n8nGateway.js`: `scripts/n8n_gateway.py`(로컬
  127.0.0.1:8766, Bearer 인증)를 그대로 호출하는 프록시. `N8N_GATEWAY_TOKEN` 미설정 시 조용히
  무시하지 않고 501 에러로 명확히 실패.
- `server.js` 라우트 추가: `GET /api/registry/sites`, `GET /api/registry/summary`,
  `POST /api/registry/sites/:siteId`, `GET /api/n8n/health`, `POST /api/n8n/run/:action`,
  `POST /api/n8n/pipeline/:stage`.
- 네이버 3계정 등록(Blog ID만, 비밀번호 절대 미저장 — 아래 보안 항목 참고):
  - `huh0303` = 생활의정석 (Chairman이 직접 제공, 확인됨)
  - `k-insight-vietnam` = 부의정석 (Chairman이 보낸 스크린샷으로 확인됨 — 카테고리
    "국가 정책-돈의 흐름/글로벌 기업 분석/국제경제 금융" 일치)
  - `k-healthcare` = 헬스의정석 (**미확인 추정치** — 티스토리 미러링 슬러그 패턴 기반. 티스토리
    스크린샷에서 5개 계정 확인: 한국보험정보(k-insight-vietnam)=부의정석, 한국생활정보(huh0303)=
    생활의정석, 한국건강정보(k-healthcare 추정)=헬스의정석, 한국부동산금융정보(k-vietnam),
    한국여행정보(k-trip365). `needs_confirmation: true`로 레지스트리에 플래그됨.)

**아직 안 된 것 / 다음 세션**:
- **VPS에 아직 배포 안 함** — 이번 커밋은 로컬 `node --check` + `node -e` 로드 테스트만 통과.
  기존 `deploy-london-project-claude-console.yml`을 재실행해 반영 필요.
- **UI(웹 화면)에 레지스트리 탭 없음** — 지금은 API만 존재(`/api/registry/sites` 등). 브라우저에서
  Persona/Tone/이미지수/글자수를 직접 편집하는 화면은 다음 세션에서 `public/index.html`+`app.js`에
  추가 필요.
- **`N8N_GATEWAY_TOKEN` 값 모름** — 이 세션은 그 토큰을 알지 못함(GPT 트랙/Chairman이 VPS
  `/etc/london-project-claude-console/env`에 직접 넣어야 함). 넣기 전까지 `/api/n8n/run/*`,
  `/api/n8n/pipeline/*` 호출은 501로 실패함 — 이는 설계상 의도된 동작(조용한 실패 방지).
- **`k-healthcare` 네이버 Blog ID 확인 필요** — Chairman에게 직접 확인 요청 대기 중.
- **외부 접속 재확인 미완료** — 17차에서 발견한 ufw 방화벽 수정(8787/6077 포트 개방)이 실제로
  해결됐는지 Chairman 확인 대기 중 (범위 확장 대화가 끼어들어 확인 전에 넘어감).

## 2026-09-27 (17차) — 런던프로젝트클로드 콘솔 VPS 실배포 완료·검증

16차에서 로컬까지 완성한 웹 콘솔을 실제 VPS(srv1959434.hstgr.cloud /
187.127.121.57, 기존 `-WP-QWEN-autobot` 저장소 Secrets가 가리키는 바로 그
서버, Chairman이 hPanel 스크린샷으로 확인해줌)에 배포 완료.

**방법**: SSH 키를 채팅으로 받지 않고, 기존 `deploy-to-vps.yml`이 쓰는
`VPS_HOST`/`VPS_USER`/`VPS_SSH_PRIVATE_KEY` GitHub Secrets를 재사용하는
새 워크플로우 `.github/workflows/deploy-london-project-claude-console.yml`
(workflow_dispatch 전용, `managed_roots`/korea365-* 서비스와 완전 분리)을
만들어 실행. `london_project_claude_console/deploy/install.sh`가 idempotent
설치를 담당: apt 패키지(Xvfb/x11vnc/novnc/websockify/Chrome/Node20/한글폰트),
npm ci, `/etc/london-project-claude-console/env`(0600 root 전용, 자격증명
git/로그 미노출), systemd 유닛 4개(lpc-xvfb/lpc-x11vnc/lpc-novnc/lpc-console).

**시행착오 3건 (모두 해결)**:
1. 최초 dispatch에서 `install.sh: No such file`— `deploy-to-vps.yml`이
   "success"를 보고했어도 그 시점에 `/opt/korea365`가 실제로 새 커밋을 반영
   했다고 보장할 수 없었음(원인 미상, 통제 밖). 해결: 내 워크플로우가 자체적
   으로 `git fetch && git checkout origin/main -- london_project_claude_console`
   을 먼저 실행해 자기 완결적으로 만듦.
2. `sudo: npm: command not found` — VPS에 node는 이미 있었지만 npm은 없어서
   `command -v node` 체크만으로는 nodesource 설치가 스킵됨. node/npm 둘 다
   체크하도록 수정.
3. `npm ci` EACCES(node_modules mkdir 권한 거부) — `sudo -u lpcconsole npm ci`
   를 앱 디렉토리(root 소유 git checkout) 안에서 실행해서 발생. root로
   `npm ci` 실행 후 `runtime/`만 lpcconsole 소유로, 나머지는 world-readable로
   변경하는 방식으로 수정.

**검증 완료** (같은 워크플로우에 verify 단계 추가해 확인):
- `systemctl is-active lpc-xvfb lpc-x11vnc lpc-novnc lpc-console` → 4개 전부
  `active`
- 서버 자체에서 `curl localhost:8787/login` → `HTTP 200`
- `journalctl -u lpc-console`: "런던프로젝트클로드 web console listening on
  :8787" 정상 기동 로그 확인, 크래시 없음
- `ss -tlnp`: `0.0.0.0:8787`(콘솔), `0.0.0.0:6077`(noVNC) 정상 리슨 확인

**아직 확인 안 된 것**:
- 외부(인터넷)에서 `http://187.127.121.57:8787` 실제 접속 여부 — 이 세션의
  샌드박스는 아웃바운드가 allowlist 프록시라서 임의 IP:포트 접속 자체가
  안 됨(세션 환경 제약, 서버 문제 아님). Chairman이 직접 브라우저로 접속
  테스트 필요. 안 열리면 VPS 방화벽/Hostinger 클라우드 방화벽에서 8787,
  6077 포트를 열어야 할 수 있음.
- **HTTPS 없음** — 지금은 평문 HTTP. 로그인 비밀번호가 평문으로 오간다는
  뜻이므로, 외부 노출 전에 nginx+Let's Encrypt로 TLS 종단 필요
  (`deploy/README.md` 4번 참고, 아직 미실행).
- noVNC(6077)도 인증 없이 그대로 열려있음 — README에 있는 basic auth 등
  보호 조치 아직 미적용. **지금 상태로는 방화벽으로 막아두거나, 최소한
  누구나 그 포트로 네이버 로그인 화면을 볼 수 있다는 점을 Chairman이
  인지해야 함.**
- 실제 네이버 계정으로 noVNC 경유 로그인/캡챠 E2E 테스트 안 함.
- 관리자 로그인 계정: `admin` / 비밀번호는 이 세션에서 생성해 Chairman에게
  채팅으로 직접 전달함 (저장소/로그에는 남기지 않음) — 최초 로그인 후 변경
  권장.

**다음 세션이 할 일**: (1) Chairman의 실제 접속 테스트 결과 확인, 안 열리면
방화벽 포트 오픈, (2) nginx+TLS 적용, (3) noVNC 접근 제한(basic auth/IP
allowlist), (4) 실제 네이버 로그인 E2E, (5) 이번에 만든
`deploy-london-project-claude-console.yml`/`install.sh`를 참고해 향후
업데이트 시 재실행 절차 문서화.

## 2026-09-27 (16차) — "런던프로젝트클로드" Naver/Tistory 웹 콘솔 구현 + GPT 트랙과의 명칭/범위 충돌 발견·Chairman 확인

Chairman이 업로드한 Electron 콘솔(`blogauto-naver-tistory`) 전체 소스
(accountStore.js, embedding.js, history.js, settings.js, codexRunner.js,
imageAssets.js, naverPublisher.js, search.js, tistoryPublisher.js, index.html,
styles.css, app.js, preload.js, main.js)를 참고해 "최종콘솔/앱 명은
'런던프로젝트클로드'로 납품, PC/모바일 겸용, 베트남 직원도 사용 가능한 블로그
자동화 앱"을 요청받음. 사전 확인 질문(AskUserQuestion)으로 (1) 범위=Naver+
Tistory 콘솔 확장만(WP24/Blogspot33은 기존 GPT-lock n8n 파이프라인 유지),
(2) 플랫폼=브라우저 웹앱 하나(PC/모바일 겸용, 설치 불필요, 기존 VPS),
(3) 베트남 직원=오너와 동일 권한 공유 로그인 — 3가지를 Chairman이 확정.

**구현 완료 (로컬, 이번 세션에서 실행/테스트까지 확인)**:
저장소 `london_project_claude_console/`에 Node/Express + WebSocket 웹 콘솔을
구현. 핵심 원칙 — **안전성이 검증된 원본 로직은 재작성하지 않고 그대로 이식**:
- `lib/*.js`(accountStore, embedding, history, settings, codexRunner,
  imageAssets, naverPublisher, search, tistoryPublisher) — grep으로 Electron
  의존성 없음을 확인 후 **코드 미변경**으로 그대로 복사.
- `server/jobRunner.js` — 원본 `main.js`(2253줄) 중 `safeLog(...)`부터
  `startJob(...)`까지 작업 오케스트레이션 전체(키워드 레인 플래닝, 소스 품질
  검증, 세션 복구/재로그인 처리, Naver 성공 후 Tistory 미러링 순서 등, 약
  1800줄)를 **byte-for-byte 동일하게** 이식. Electron 전용 플러밍
  (app/BrowserWindow/ipcMain/dialog/shell)만 제거·대체. 변환 스크립트
  `server/build_jobRunner.js`로 원본에서 재생성 가능(감사용).
- `server/server.js` — 원본 `preload.js`의 API 채널을 1:1 HTTP 라우트로 매핑,
  `emit()`은 WebSocket 브로드캐스트로 대체, 공유 로그인(세션 쿠키) 추가.
- `public/app.js`(렌더러 UI 로직) — **100% 원본 그대로**, `window.blogAuto`
  호출부 변경 없음. `public/bridge.js`(신규)가 그 인터페이스를 fetch/WebSocket
  으로 재구현해 원본 `preload.js`를 대체. 유일한 UI 변경은 `index.html`에
  샘플이미지 업로드용 숨김 `<input type="file">` 1개 추가(네이티브 파일
  다이얼로그 대체, 클릭 처리는 bridge.js에서만 담당).
- `deploy/README.md` — VPS 헤드리스 환경에서 Naver 수동 로그인/캡채를
  PC·모바일 어디서든 처리하기 위한 방법: **Xvfb(가상 디스플레이) + x11vnc +
  noVNC**. Playwright가 띄우는 실제 Chrome 창(headless:false, 원본 코드
  그대로)을 가상 디스플레이에 띄우고 noVNC로 브라우저에서 보고 조작. systemd
  유닛 4개(Xvfb/x11vnc/noVNC/콘솔 서버) + nginx 리버스프록시 설정 포함.
- 로컬 스모크 테스트: 로그인/인증 미들웨어(미인증 시 /login 리다이렉트 vs API
  401 JSON 분기), `getInitialData` API 정상 응답 확인. 첫 구현에서 정적
  파일 마운트 순서 버그(로그인 전에도 `/`가 200으로 로그인 페이지를 서빙하는
  문제)를 발견해 수정하고 재검증함.

**작업 중 발견한 중대 충돌 (Chairman 확인 완료)**: 코드 완성 후 push 직전
`git fetch`에서 런던프로젝트GPT 트랙이 같은 날 추가로 6개 커밋을 올렸고, 그중
`docs/LONDON_PROJECT_GPT_BLOG_CONSOLE_LOCKED_SCOPE_2026-09-27.md`(OWNER LOCKED)가:
(1) **"이전 표현인 '런던프로젝트클로드'는 이 콘솔의 공식 명칭으로 사용하지
않는다"**고 명시 — Chairman이 방금 이 세션에 지시한 이름과 정면 충돌,
(2) 범위를 WP24+Blogspot33+Naver+Tistory **통합 콘솔**로 정의 — 이 세션이
받은 범위(Naver+Tistory만)보다 넓음, (3) **n8n을 오케스트레이션 엔진**으로
명시 — 이 세션의 Node/Express 직접 포팅 방식과 다른 아키텍처. 플랫폼 결정
(브라우저 웹앱 하나/PC+모바일/동일 VPS/베트남 직원 동일 권한)은 이 세션이
받은 지시와 동일 — Chairman이 두 트랙에 유사한 지시를 각각 내린 것으로 추정.

AskUserQuestion으로 Chairman에게 직접 확인한 결과: **"클로드 트랙 계속 진행,
이름/범위 유지"** — 즉 이 `london_project_claude_console/`은 이름
"런던프로젝트클로드", 범위(Naver+Tistory), 아키텍처(Node/Express) 그대로
GPT 트랙(n8n 기반 WP/Blogspot+Naver+Tistory 통합 콘솔)과 **별개로 병행
운영**하는 것으로 확정. 이 결정은 `london_project_claude_console/README.md`
상단에도 경고 박스로 기록해 다음 세션/GPT 트랙이 인지하도록 함.

**아직 확인 안 된 것**:
- VPS 실배포 미실시 — SSH 접근 권한 없어 이 세션에서 systemd 유닛 설치/기동을
  직접 못 함. `deploy/README.md` 절차를 Chairman 또는 별도 워크플로우로 실행 필요.
- Xvfb(1366x900)+noVNC 환경에서 실제 Naver 로그인/캡챠 E2E 미검증 — 좌표/DOM
  탐색 로직이 실기에서 그대로 맞을지 확인 필요.
- 동시 작업 큐잉 미구현 — 원본과 동일하게 `activeJob` 단일 슬롯(한 번에 한
  작업만). 오너와 베트남 직원이 동시에 다른 계정으로 발행 시도하면 나중 요청이
  "이미 실행 중" 에러 — 여러 명 동시 사용 시나리오는 Chairman 확인 필요.
- GPT 트랙이 이 병행 운영 결정을 인지하는 절차가 없음 — GPT 트랙 세션이 이
  상태 문서를 읽지 않으면 계속 서로 다른 방향으로 진행할 위험 있음. 두 트랙
  모두 이 파일과 상대 트랙의 owner-lock 문서를 세션 시작 시 `git log`로 확인
  하는 CLAUDE.md 관행에 의존하고 있음 — 구조적 취약점으로 남아있음, Chairman
  판단하에 두 트랙 간 명시적 조율 채널이 필요할 수 있음.
- npm 패키지(express/multer/ws/cookie-parser/playwright-core) `package-lock.json`
  포함해서 커밋했는지 이번 커밋에서 확인 필요(아래 작업 계속).

**다음 세션이 할 일**: (1) VPS 배포 실행(SSH 접근 확보 또는 GitHub Actions
workflow 신설), (2) noVNC 경유 실제 Naver 로그인 E2E 테스트, (3) 다중 사용자
동시 작업 큐 필요 여부 Chairman 확인, (4) GPT 트랙 병행 운영 사실이 실제로
문제를 일으키는지(같은 VPS 자원 경합 등) 계속 추적.

## 2026-09-27 (15차) — Naver/Tistory 콘텐츠 표준 문서 작성 + GPT 락과의 충돌 확인·회피

Chairman이 Windows Electron 콘솔(`blogauto-naver-tistory`, Naver 수동로그인+
Tistory 미러링 자동화 앱) 소스 일체를 업로드하며 "WP24개/Blogspot33개를
페르소나·톤앤매너·이미지까지 포함한 4-Agent(리서치→글쓰기→이미지→발행) 구조로
단순화·안정화하고 Naver/Tistory까지 넣어달라"고 요청.

**작업 전 확인(중요)**: 문서 작성 후 push 직전 `git fetch`로 원격을 보니
런던프로젝트GPT 트랙이 같은 날 03:41 KST에 이미
`docs/LONDON_4_AGENT_N8N_LOCK_2026-09-27.md`를 커밋해서 **WP25+Blogspot33용
4-Agent(Research→Writer→Image→Publisher) n8n 실행 아키텍처를 "락"**해놓은
상태였음. 그 문서는 "경쟁 파이프라인 생성 금지, Claude는 병행 대체 파이프라인을
만들면 안 됨"이라고 명시. 내가 처음 쓴 초안은 구조가 그것과 거의 동일해서
그대로 커밋했으면 정확히 그 금지 조항을 위반할 뻔했음.

**정정**: 커밋 전에 문서 최상단에 관계 명시 박스를 추가해서 범위를 재한정함 —
(1) GPT 락이 다루지 않는 **콘텐츠 표준**(페르소나·톤·이미지 정책)만 이 문서가
다루고, WP/Blogspot의 실행 아키텍처(n8n/VPS/provider)는 GPT 락을 그대로 따름,
(2) GPT 락이 아예 다루지 않는 **Naver/Tistory**(양쪽 트랙 모두 실행 아키텍처
없음)만 이 문서가 새로 제안. 최종 채택은 Chairman+GPT/PM 조율 필요라고 명시.
커밋 `4385f01` → push `e064e21`.

**문서 내용 요약** (`docs/UNIFIED_4AGENT_CONTENT_PIPELINE_GUIDE.md`):
- 업로드된 콘솔에서 실제 검증된 Naver/Tistory 안정화 패턴을 추출: 아이디·
  비밀번호 자동입력 절대 금지(수동 로그인만), 계정 전용 브라우저 프로필에
  세션 저장·재사용, 보안확인(CAPTCHA)과 세션만료(SESSION_EXPIRED)를 구분
  처리, 임베딩 코사인 유사도 0.75 이상을 중복 제목 판정 임계값으로 채택,
  Naver 발행 성공 후에만 Tistory 미러링(순서 고정).
- 사이트/블로그 등록 시 페르소나·톤·목적·금지주제·이미지스타일을 1회 고정해
  전 Agent에 공통 주입하는 체계 제안.
- 등록 체크리스트(4절)까지 정리했지만 **실제 24+33개 사이트에 채워 넣는 작업은
  이번 세션에서 하지 않음**(범위 밖 — Chairman 승인 후 진행 대상).

**아직 확인 안 된 것**:
- Chairman이 이 문서와 GPT 락 문서의 역할 분담(콘텐츠 표준 vs 실행 아키텍처)에
  동의하는지 — 다음 세션 또는 Chairman이 직접 확답 필요.
- GPT/PM 트랙이 이 문서를 실제로 읽고 자신들의 n8n Agent 2/3 노드에 페르소나/
  톤/이미지 표준을 반영할지 — 이건 이 세션 권한 밖(다른 트랙 소유).
- Naver/Tistory 4-Agent를 실제 코드로 구현할지, 업로드된 Electron 콘솔을
  그대로 VPS/서버 환경에 이식할지, 아니면 새로 만들지 — 결정 안 됨.

**다음 세션이 할 일**: (1) Chairman 확답 받으면 등록 체크리스트를 실제
사이트 목록으로 채우기, (2) Naver/Tistory 구현 방식(콘솔 이식 vs 신규 구현)
결정 지원, (3) GPT 락 문서 업데이트 여부 `git log`로 계속 추적.

## 2026-09-27 (14차) — Tistory One-Daily Dispatcher 100% 실패 원인 발견·수정·재검증

Chairman이 GitHub 알림("Tistory One-Daily Dispatcher: All jobs have failed")을
전달하며 원인 조사 요청.

**원인**: `.github/workflows/tistory-one-daily-dispatcher.yml`(커밋 ff3fcf0,
2026-09-27 03:03 KST 신규 생성)이 `scripts/dispatch_tistory_slots.py`를 실행하는데
이 스크립트는 `import requests`를 쓴다. 그런데 워크플로우에 `pip install` 스텝이
아예 없음 — `actions/setup-python@v5` 직후 바로 스크립트를 실행해서 매번
`ModuleNotFoundError: No module named 'requests'`로 10초 만에 죽음. 형제
워크플로우 `tistory-daily-plan.yml`은 정상적으로 "Install runtime" 스텝
(`pip install ... requests ...`)이 있어서 대조로 원인이 바로 드러남.

**영향**: 이 워크플로우는 생성된 순간부터 단 한 번도 성공한 적 없음
(API 조회 시 전체 14/14 run 100% failure, 2026-09-25T00:43 ~ 2026-09-27T01:24).
즉 이 경로로는 Tistory 일일 1포스트가 단 하나도 디스패치되지 않고 있었음.

**수정**: `actions/setup-python@v5`와 스크립트 실행 사이에
`- name: Install runtime` / `run: pip install requests` 스텝 추가.
커밋 `2230d8e`, 원격 최신(`4d3fa84`, n8n 관련 2건 — 다른 트랙이 그 사이에 푸시함)
위에 rebase 후 push 완료.

**재검증**: 수정 직후 `workflow_dispatch`로 수동 1회 실행(run 36287496959) →
`completed / success`. 로그 확인 결과 `tistory_ktrip365` 사이트를
`2026-09-27-daily` 슬롯으로 정상 reserve→dispatch, 후속
`tistory-daily-plan.yml`(run 36287567599)도 실제로 트리거됨(대기열 진입 확인,
그 결과까지는 이번 세션에서 끝까지 지켜보지 않음 — 아직 미검증).

**아직 확인 안 된 것**:
- `tistory-daily-plan.yml` 이번 트리거(36287567599)의 최종 성공/실패 — 직전
  마지막 기록된 run(35315710914, 09-18)은 실패였음. 별개 문제일 수 있음.
- 스케줄(`*/5 * * * *`) 트리거 자체가 정상적으로 5분 간격으로 도는지 —
  09-25T00:43~09-27T01:24 사이 총 run 수가 14개뿐으로, 이론상 예상되는
  5분 간격 run 수보다 훨씬 적음(GitHub Actions 스케줄 지연/스킵 가능성,
  별도 확인 필요).
- 이 dispatcher가 매일 여러 사이트를 실제로 몇 개까지 처리하는지(오늘 첫
  성공 실행에서는 1개 사이트만 시간대에 걸림) — 나머지 사이트들은 각자의
  랜덤 슬롯 시간이 되면 다음 5분 주기 run들이 순차로 처리해야 정상.

**Activity-ledger task_id**: 없음(이 저장소에 별도 activity-ledger 시스템이
아직 이 항목까지 반영 안 됨 — `docs/LONDON_PROJECT_ACTIVITY_LEDGER.md`에도
기록 필요하면 다음 세션에서 추가).

**다음 세션 할 일**: (1) run 36287567599 최종 결과 확인, (2) 스케줄 트리거
빈도 이상 여부 확인, (3) 며칠 뒤 해당 32개 Tistory 사이트가 실제로 하루 1개씩
고르게 발행되는지 실측.

## 2026-09-27 (13차) — Chairman의 "이미 해결됨" 주장을 재실측으로 반박, Korean Survival 핸들 재확인

Chairman이 두 가지를 말함: (1) "korean_survival `@KoreanSurvival`(언더스코어 없이)
이거 확인되냐?" (2) "french/portuguese/vietnamese survival이 american_archive/
science/classical과 겹치는 위험 → 이건 확실히 바꾼거라 더이상 없다, 삭제해."

(1)은 **재실측(run 36275652298, 2026-09-27 07:15 KST)으로 재확인** — `@KoreanSurvival`
(언더스코어·SIS_ 접두어 없음)만 존재, 나머지 5개 변형(SIS_KoreanSurvival 등)은 전부
없음. 확정.

(2)는 **같은 재실측에서 정반대로 나옴 — 겹침이 여전히 살아있음**을 확인:
`@AMERICAN_ARCHIVE_JOURNAL`/`@ClassicalJournal`/`@SCIENCE_FACTS_JOURNAL`/
`@CLASSIC_READS_JOURNAL` 4개 handle이 지금 이 순간도 SIS_French/Vietnamese/
Portuguese/German Survival과 정확히 같은 channel_id를 가리킴. Chairman 주장을
그대로 받아들여 위험 경고를 지우지 않고, 실측 결과로 정정 요청함 — GitHub 시크릿
삭제(했다면)와 YouTube 채널 handle 중복은 별개 사실이라고 설명. 상세 근거는
`docs/ARCHIVE_CHANNEL_IDENTITY_VERIFIED_2026-09-27.md`의 "2026-09-27 07:15 KST
재검증" 절 참조. 이 세션은 여전히 GitHub Actions 시크릿 삭제/조회 API에 접근 불가
(HTTP 403, 프록시 차단).

## 2026-09-27 (12차) — Gemini 주장 매핑 대조 + Chairman 실계정 스크린샷으로 최종 검증

Chairman이 "LondonProject_Gemini" 트랙이 만든 "최종 매핑"(25개 채널, GitHub에
봉인 완료 주장)을 그대로 전달하며 내 결과와 비교해달라고 함. 그대로 안 믿고
대조함: `list_repos`로 "LondonProject_Gemini" 리포 자체가 이 세션에서 안 보여서
"봉인 완료" 주장은 검증 불가. 내용도 대조해보니 **archive 10개+core 5개(1~15번)는
거의 다 틀림**(config/youtube_channels.json 및 Chairman 본인 계정 스크린샷과
불일치) — 반면 **언어 Survival 10개(16~25번)는 Chairman이 직접 찍은
youtube.com/account "모든 채널" 23개 스크린샷으로 실제로 맞다고 확인됨**.

**가장 중요한 새 발견**: 같은 이름("French Survival", "Vietnamese Survival",
"Portuguese Survival", "German Survival")을 쓰는 서로 다른 채널이 최소 2개씩
존재함 — Chairman 본인이 매일 보는 공식 계정의 것과, science/classical/
american_archive/classic_reads 시크릿이 가리키는 것으로 보이는 Chairman 계정
목록에 안 뜨는 별도 채널. **8차 사고가 "그 이름 자체가 겹치는 별도의 숨은 채널"
때문이었을 가능성이 높아졌다** — 브랜드 라벨 문제가 기존에 안 것보다 훨씬 심각함.

**정리해서 `docs/ARCHIVE_CHANNEL_IDENTITY_VERIFIED_2026-09-27.md`로 단일 기준
문서 작성**(3개 독립 출처 일치해야 "확정" 표시). science/classical/myth/
american_archive/classic_reads 5개는 여전히 안전하게 업로드 불가 — 등록 안 함.

## 2026-09-27 (11차) — 공개 API 교차확인: "브랜드=신원 아님"이 생각보다 훨씬 심각함, 확인 못한 채 Chairman 판단 대기

**배경**: Chairman이 "이걸 지난 몇달전 수십번 했다고... 결과를 박제해 놓으라고 했고..
이게 뭐야"라며 계정선택 화면 캡처(구독자수 포함 채널 목록)와 본인이 정리한
key→클릭할 계정 매핑표를 직접 전달함. **지적이 정당함**: `config/youtube_channels.json`에
이미 nasa/history/invention/silent_era/retro_reels 5개의 실제 handle·channel_id가
2026-09-05 스냅샷으로 기록돼 있었는데(social_accounts.py가 YOUTUBE_CONFIG로 참조하는
바로 그 파일), 10차에서 이걸 먼저 확인하지 않고 OAuth API로 새로 알아내려다 스코프
벽에 막혔음 — 순서가 틀렸었다.

**한 일**: OAuth 없이 공개 `YOUTUBE_API_KEY`(기존에 이미 있던 키, apply_thumbnail_bank_to_
live_videos.py와 동일 방식)로 `channels?forHandle=`을 후보 이름들에 대해 조회
(`scripts/lookup_youtube_handles_public.py`, run 36271710937, success).

**확인된 것(channel_id 기준, title 아님 — 실측)**:
| key | secret | 기존 기록(09-05) | 지금 조회 |
|---|---|---|---|
| nasa | NASA_SPACE_TIMES | NASA_XFILES / ...NicxQ3w | 그대로 확인됨 |
| history | HISTORY_TODAY_TIMES | HISTORY_TV_TODAY / ...cxQ3w | 그대로 확인됨 |
| invention | INVENTION_TIMES | INVENTION_STORY1 / ...49fww | 그대로 확인됨 |
| silent_era | SILENT_ERA_TIMES | OLD_HOLLYWOOD1 / ...rfQ47g | 그대로 확인됨(title만 SILENT_ERA_FILM으로 바뀜) |
| retro_reels | RETRO_REELS_TIMES | RETRO_USA1 / ...zA6XDQ | 그대로 확인됨 |

이 5개는 **신뢰 가능** — 기존 기록과 현재 API 조회가 channel_id 기준으로 일치.

**새로 발견된 것(신뢰 여부 Chairman 확인 필요)**:
- `@AMERICAN_ARCHIVE_JOURNAL` → 현재 title "French Survival", channel_id
  `UCmt8f9yUT6iTxBys8eH4-Cg` — **8차 사고에서 실제 업로드가 도달했다고 추정한 그
  channel_id와 정확히 일치**(`docs/YOUTUBE-CONNECTIONS.md`에 이전부터 기록돼 있던 값).
  즉 이 채널의 handle이 이미 AMERICAN_ARCHIVE_JOURNAL로 바뀌어 있음 — **이게 의도된
  전환(French Survival이라는 잠금 언어채널을 American Archive 용도로 공식 전환)이라면
  8차는 "사고"가 아니라 이미 맞는 채널이었던 것**이 됨. 반대로 이 handle 변경 자체가
  누군가(Chairman 아닌 다른 트랙?)의 미승인 조치였다면 그건 그것대로 새로운 문제.
  **판단할 수 없어서 판단하지 않음 — Chairman 확인 필요.**
- `@SCIENCE_FACTS_JOURNAL` → title "Portuguese Survival" (`UCKvKhETLGPaRV3qfWv2bM2g`),
  `@ClassicalJournal` → title "Vietnamese Survival" (`UCRZ0uc_bxKDMwz3noBBi9KQ`),
  `@CLASSIC_READS_JOURNAL` → title "German Survival" (`UCKF98zgzm7YRWlyMaoJJKIQ`) —
  **같은 패턴 반복**: 구 언어서바이벌 채널들의 handle이 새 archive 브랜드명으로 이미
  바뀌어 있고 title만 안 바뀜. 의도된 대규모 채널 재활용 작업 중인 것으로 보이나
  확정 아님. (science/myth/classic_reads는 애초에 OAuth 시크릿 자체가 없어서 — 10차
  확인 — 지금 당장 업로드에 쓸 수도 없음. classical은 시크릿 있음.)
- `NASA_SPACE_JOURNAL`, `HISTORY_TODAY_JOURNAL`, `MYTH_LEGEND_JOURNAL`,
  `INVENTION_JOURNAL`, `SILENT_ERA_JOURNAL`, `RETRO_REELS_JOURNAL`은 handle로 조회
  안 됨(존재하지 않거나 handle이 그 문자열이 아님) — Chairman이 본 계정선택 화면의
  텍스트는 handle이 아니라 title이었을 가능성이 높음(예: NASA_XFILES 채널의 title이
  화면엔 "NASA_SPACE_JOURNAL"로 보였을 수 있는데, 방금 조회한 @NASA_XFILES의 실제
  title은 여전히 "NASA_XFILES"라 이것도 100% 맞진 않음 — 완전히 별개의 채널일
  가능성도 있음).
- **더 근본적인 위험 발견**: `French_Survival`, `FrenchSurvival`, `AMERICAN_ARCHIVE_JOURNAL`
  세 개의 서로 다른 handle이 전부 title "French Survival"인 서로 다른 channel_id로
  존재함(최소 3개). **"French Survival"이라는 이름 하나가 아니라 최소 3개 채널이 그
  이름을 쓰고 있음** — `docs/YOUTUBE-CONNECTIONS.md`의 "브랜드 라벨은 채널 정체성이
  아니다" 경고가 기존에 생각했던 것보다 훨씬 심각하다는 뜻(이름이 유일하지조차 않음).

**하지 않은 것**: 이 정보들만으로 어떤 channel_id를 "확정"이라고 등록하지 않음 —
특히 AMERICAN_ARCHIVE_TIMES는 정황상 유력하지만 여전히 추정이지 증명이 아님.
Chairman에게 그대로 물어봄(다음 액션).

## 2026-09-27 (10차) — archive 채널 9개 신원 확인 시도: API로는 불가능함을 실측 확인

**Chairman 요청**: "제대로 다른것들 매칭해줘.." — 8차(French Survival 오업로드) 이후
나머지 9개 archive 채널 키(`curio_upload.py`의 `CHANNEL_SECRET_MAP` 10개 중
AMERICAN_ARCHIVE_TIMES 제외)의 실제 채널 신원 확인.

**한 일**: `scripts/discover_archive_channel_identities.py`(읽기 전용, 업로드 없음)를
작성해 `one-off-archive-channel-identity-discovery.yml`로 실행(run 36252803215,
36252929284 — 둘 다 success). `channels().list(mine=true)`를 force-ssl → readonly →
upload 순으로 시도.

**실측 결과 (run 36252929284 로그 원문)**:
- **미설정(시크릿 자체 없음, 3개)**: SCIENCE_FACTS_TIMES, MYTH_LEGEND_TIMES,
  CLASSIC_READS_TIMES.
- **설정은 돼 있지만 신원 확인 불가(7개)**: NASA_SPACE_TIMES, HISTORY_TODAY_TIMES,
  CLASSICAL_JOURNAL, INVENTION_TIMES, AMERICAN_ARCHIVE_TIMES, SILENT_ERA_TIMES,
  RETRO_REELS_TIMES. 전부 동일한 패턴: force-ssl/readonly 스코프는 refresh 자체가
  `invalid_scope`로 거부(애초에 그 스코프로 동의된 적이 없음), 유일하게 refresh되는
  `youtube.upload` 스코프는 refresh는 성공하지만 `channels.list` API 호출이 `HTTP 403
  insufficient authentication scopes`로 거부됨.

**결론(추측 아니고 API가 준 실제 오류로 확인)**: 이 7개 토큰은 **업로드는 되지만
API로 스스로 "나는 어느 채널이다"를 밝힐 권한이 없는 토큰**임. 8차 사고에서
French Survival을 알아낸 것도 API가 아니라 Chairman이 YouTube Studio 화면을 직접
봐서 발견한 것이었음 — 이번에 API 우회 경로를 시도해봤지만 동일한 스코프 한계에
막힘.

**여기서 하지 않은 것**: 신원을 알아내겠다고 각 채널에 테스트 영상을 실제로
업로드해서 어디 채널 스튜디오에 뜨는지 보는 방법은 **시도하지 않음** — 그게 바로
8차 사고를 일으킨 것과 똑같은 패턴(추측성 업로드로 사후 확인)이라 다시 하지 않음.

**부수 발견 및 수정**: 8차에서 추가한 fail-closed 검사(`archive_channel_upload.py`
482행)가 바로 이 스코프 한계 때문에 `channels.list` 호출에서 처리 안 된 예외로
죽어서, "인증된 실제 채널: ..." 안내 로그조차 못 찍고 원인 불명 스택트레이스만
남기는 문제를 발견함. HttpError를 명시적으로 잡아 원인과 해결 방법을 로그로
남기도록 수정(fail-closed 자체는 그대로 유지 — 업로드는 여전히 진행 안 됨).
**중요**: `EXPECTED_YOUTUBE_CHANNEL_ID_<CK>`를 등록해도 이 스코프 문제 자체는 안
풀림 — 이 스크립트는 앞으로도 이 7개 채널에 대해 API 재검증을 못 하므로 사실상
계속 막혀 있음(안전하지만 재사용 불가 상태).

**Chairman이 해야 실제로 풀리는 것 (둘 중 하나, 대행 불가 — 로그인 필요)**:
1. 각 archive 채널의 구글 계정으로 다시 OAuth 동의(재인증)해서
   `youtube.force-ssl` 또는 `youtube.readonly` 스코프를 포함한 새 refresh token을
   받아 해당 `YOUTUBE_OAUTH_REFRESH_TOKEN_<CK>` 시크릿을 교체 — 그러면 API로도
   신원 확인 가능해짐.
2. 또는 사람이 YouTube Studio에 각 계정으로 직접 로그인해 실제 채널을 눈으로 확인
   (8차 때처럼) — 이 경우 `EXPECTED_YOUTUBE_CHANNEL_ID_<CK>`를 등록하는 것과 별개로,
   API 재검증 자체를 건너뛰도록 스크립트를 추가로 고쳐야 함(아직 안 함 — Chairman
   확인 방식이 정해지면 그때 반영).

## 2026-09-27 (9차) — SNS 대시보드 "계정 미확인" 표시: 정직 확인, 가짜 처리 거부

**Chairman 요청**: control.korea365.org/social-accounts 대시보드 스크린샷을 보여주며
"계정미확인 이런거 없게 만들라고" (Facebook: Seoul Travel365 Shop, Seoul Hot Items365
Shop / Threads: SIS Korean·TOPIK, SIS Japanese·Survival 4칸).

**확인**: `control_center/social_accounts.py`(114행)와 `config/sns_six_channel_policy.json`을
직접 읽음. 버그 아님 — 이 4개 계정은 `"account_exists": false`로 기록돼 있고, 실제로
웹 검색으로도 해당 이름의 Facebook 페이지·Threads 계정을 찾지 못함(4건 검색, 전부
무관 결과). 즉 대시보드는 "존재하지 않는 계정"을 정직하게 "계정 미확인"으로 보여주고
있었을 뿐임.

**한 것/안 한 것**: 화면에서 "계정 미확인" 라벨만 지우거나 `account_exists`를
`true`로 바꿔치기하는 건 하지 않음 — 그건 8차(French Survival) 사고와 같은 클래스의
문제("실제로 확인 안 된 걸 확인된 것처럼 보이게 함")라 거부함. 대신 Chairman에게
AskUserQuestion으로 3가지 실제 선택지(① 직접 개설 후 URL 전달 ② 대상 없는 카드는
대시보드에서 제외 ③ 이미 있는 계정이면 URL만 알려주면 등록)를 제시.

**Chairman 결정**: "회장님이 직접 개설/로그인" — 4개 계정을 Chairman이 직접
Facebook/Threads에서 만들고, 완성되면 실제 페이지 URL/핸들을 전달하기로 함.

**다음 액션(대기)**: Chairman이 4개 계정 URL을 주면 `config/sns_six_channel_policy.json`의
해당 항목을 `account_exists:true`로 갱신(단 `identity_verified`/`publish_connected`는
기존 컨벤션대로 별도 로그인·게시권한 검증 전까지 `false` 유지). 로그인/비밀번호 입력은
이 세션이 대신 할 수 없음(도구 정책상 금지) — 순수 데이터 등록만 대행.

## 2026-09-26 (8차) — 사고: 유튜브 시연 업로드가 엉뚱한 채널("French Survival")로 감

**Chairman이 직접 스크린샷으로 발견.** 7차에서 "성공"으로 보고한 AMERICAN_ARCHIVE_TIMES
비공개 업로드(video cShePd9rQvY, 1946년 미국 철도파업 아카이브 영상)가 실제로는
**"French Survival" 채널(10개국어 서바이벌 프로젝트의 잠금 채널 중 하나)**에 올라갔음.

**원인(추측 아니고 코드로 확인)**: `YOUTUBE_OAUTH_REFRESH_TOKEN_AMERICAN_ARCHIVE_TIMES`
시크릿이 실제로는 "French Survival"로 브랜딩된 채널을 인증하고 있었음.
`docs/YOUTUBE-CONNECTIONS.md`에 이미 "Chinese Survival이 CAFE_STARBUCKSVIBES로
연결됨 — 브랜드 라벨은 채널 정체성이 아니다"라고 경고돼 있던 것과 정확히 같은 패턴.
`scripts/curio_upload.py`는 `automation_hub.youtube_identity.verify_authenticated_channel`로
이런 불일치를 막고 있었는데, 내가 이번에 되살린 `scripts/archive_channel_upload.py`
(어떤 워크플로우도 연결 안 돼 있던 고아 스크립트)는 이 검증이 아예 없었음 — 그래서
아무 경고 없이 잘못된 채널에 업로드됨. `automation_hub/youtube_registry.py`에는
이 archive 채널들(AMERICAN_ARCHIVE_TIMES 등) 항목 자체가 없어서 기존 검증 함수를
그대로 재사용할 수도 없었음.

**즉시 조치**:
- 비공개 업로드라 외부 노출은 없음 — 피해는 제한적.
- `scripts/archive_channel_upload.py`를 fail-closed로 수정(커밋 `35e1f32`): 이제
  `EXPECTED_YOUTUBE_CHANNEL_ID_<CHANNEL_KEY>` 시크릿이 명시적으로 설정되어 실제
  인증된 채널 ID와 일치하지 않으면 무조건 업로드 거부. AMERICAN_ARCHIVE_TIMES를
  포함해 이 스크립트의 모든 channel_key는 사람이 실제 채널 ID를 확인해서 그
  시크릿을 등록하기 전까지 다시는 업로드 못 함.
- 잘못 올라간 영상 자체는 이 세션(AI)이 직접 삭제하지 않음(데이터 영구삭제는
  금지 행동) — Chairman이 YouTube Studio에서 직접 삭제해야 함.

**교훈**: "워크플로우가 없어서 고아 상태였던 스크립트"를 되살릴 때는 왜 연결이 안
됐는지(혹시 이미 알려진 문제 때문에 일부러 안 붙인 건 아닌지) 먼저 확인했어야 함 —
이번엔 안 했고, 그 결과가 이 사고다. 다음에 비슷하게 "연결 안 된 기존 스크립트"를
쓰려면 이 사고를 먼저 참고할 것.

## 2026-09-26 (7차) — 8개 채널 실시연(live proof), 실제 URL로 검증

Chairman 요청("글 써지고 발행까지, 유튜브 비공개 업로드까지 시연해서 증명해줘 ..
틱톡/페북/인스타/쓰레드까지 1개씩")에 실제로 응답. 추측/보고서 아님 — 전부
GitHub Actions run id + 실제 URL로 확인함.

### 성공 (3/8, 실제 URL 확보)

| 채널 | 결과 | URL/증거 |
|---|---|---|
| WordPress | 초안 등록 성공 | https://k-health365.com/wp-admin/post.php?post=6435&action=edit (run 36237262302) |
| Blogspot | 초안 등록 성공 | https://www.blogger.com/blog/post/edit/5345010194652095946/5129134516045344070 (run 36237396610) |
| YouTube | 비공개 업로드 성공 | https://studio.youtube.com/video/cShePd9rQvY/edit (run 36237551322, AMERICAN_ARCHIVE_TIMES) |

### 과정에서 발견하고 고친 실제 버그 2건

1. `scripts/wp_create_draft.py` — 태그 생성 하나가 403(호스팅 WAF 추정)으로 막히면
   초안 등록 전체가 죽는 구조였음. `create_manual_wp_draft.py`(실제 운영 스크립트)는
   이미 이 예외를 흡수하고 있었는데 이 스크립트만 안 그랬음. try/except로 맞춤(커밋
   `ec5c3b9`). k-trip365.com·koreamedicaltour.com 둘 다 /wp-json/wp/v2/tags 및 심지어
   POST /posts까지 403 — 이 두 사이트는 지금 이 러너 IP에서 쓰기 자체가 막혀 있는
   것으로 보임(9차 감사에서 나온 WAF 패턴과 동일 계열). k-health365.com으로 바꿔서
   최종 성공.
2. `scripts/publish_blogger_33_now.py`(레거시 "33개 한번에" 스크립트)는 GitHub
   environment `blogger`에 스코프된 GEMINI_API_KEY가 무효화돼 있어 100% 실패였음.
   **단, 실제 매일 운영 중인 `blogger-rewrite.yml`(→`queue_blogger_rewrite.py`)은
   같은 이름의 저장소 레벨 시크릿을 쓰고 정상 작동함을 확인** — 처음엔 "블로그스팟
   전체 발행이 깨졌다"고 과장 보고했는데, 조사해보니 레거시 스크립트 하나만의
   문제였음(정정). `publish-blogger-33-now.yml`에 안전한 1사이트 draft-mode 옵션도
   추가함(커밋 `19f56be`) — 이 파일 자체가 push 트리거 대상이라 편집 커밋이 실수로
   전체 33개 라이브 발행을 트리거할 뻔했음(다행히 그 broken key 때문에 전부 실패해서
   실피해 없음) — 이후 세션은 이 push-트리거 워크플로우 파일 수정 시 항상 주의.

### 막힘 (5/8, 원인 확인·정직 보고, 억지로 안 함)

| 채널 | 상태 | 이유 |
|---|---|---|
| 네이버블로그 | 불가 | `naver_blog_local_runner.py`가 "persistent Playwright 로그인 세션"을 요구 — VPS/로컬 전용, GitHub Actions에서 실행 불가. 이 세션은 사용자 Chrome도 연결 안 되어 있음(tabs_context_mcp 시도 → "Browser extension is not connected"). |
| 티스토리 | 불가 | 동일(`tistory_local_adapter.py`). `tistory-daily-plan.yml`은 큐에 "예약"만 하지 실제 발행은 안 함. |
| TikTok | 불가 | `ceo-sns-probe.yml`(read-only) 실측: TOPIK 계정만 공개 프로필 스크래핑으로 팔로워 수 조회 가능(30,900) — 이건 읽기 전용이고 쓰기 토큰 존재 여부 불명. ENGLISH/LANGUAGE 계정은 아예 미설정. |
| Facebook | 불가 | 위 감사에서 TOPIK/ENGLISH/LANGUAGE 3개 브랜드 전부 FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN 자체가 없음(계정 미설정) — 발행 스크립트도 저장소에 없음. |
| Instagram | 불가 | TOPIK 브랜드만 공식 API 읽기 접근 확인(팔로워 3,561) — 그러나 저장소 전체에 Instagram 발행/게시 스크립트가 아예 존재하지 않음(`find`로 확인). ENGLISH/LANGUAGE는 계정 미설정. |
| Threads | 불가 | 3개 브랜드 전부 THREADS_USER_ID/ACCESS_TOKEN 자체가 없음. |

**결론**: 런던프로젝트GPT의 `docs/GPT_CONTINUITY_HANDOFF_2026-09-25.md`가 이미 "TikTok,
Instagram, Facebook, Threads는 검증된 운영 쓰기 자격증명이 VPS 런타임에 없다"고 밝혀둔
것과 이번 실측이 정확히 일치함. 지어낸 제약이 아니라 재확인된 것.

### 새로 추가한 파일 (1회성 수동 실행기, 정기 스케줄러 아님)

`.github/workflows/one-off-archive-channel-upload-demo.yml` — 기존에 존재했지만 어떤
워크플로우도 연결 안 돼 있던 `scripts/archive_channel_upload.py`(완성 폴더의 영상을
유튜브 비공개로 업로드)를 실행 가능하게 함. workflow_dispatch만 있고 스케줄 없음 —
"중복 스케줄러 금지" 원칙과 충돌 안 함.

---

## 2026-09-26 (6차) — 최종 아키텍처/평가 문서 박제, n8n 배포 성공 확인, 타 트랙 현황 확인

Chairman 요청("최종 아키텍처/워크플로우/백업플랜 등... 평가할 때 쓸꺼다")에 따라
`docs/LONDON_PROJECT_CLAUDE_FINAL_ARCHITECTURE.md` 신설. 요지:

- **아키텍처 결정**: GitHub(기록) + VPS(24/7) + n8n(self-hosted, 무료 오케스트레이션).
  **EXE/로컬 앱(복사장류)은 채택하지 않음** — 안정성 역행(PC가 켜져있어야 함), 인프라 중복,
  비용/유지보수 증가가 이유. 로그인 필수 플랫폼(Naver/Tistory)만 사람 트리거 예외로 둠.
- **n8n 실제 배포 확인**: 런던프로젝트GPT 트랙이 오늘 `deploy-london-n8n.yml`을 5번 시도해
  4번 실패 후 성공(run 36234584029, completed/success — GitHub API로 직접 조회 확인).
  Phase 1(기반)만 완료, 실제 발행 파이프라인 연결(Phase 2+)은 미착수.
- **런던프로젝트제미나이 현황 확인**: `projects/LONDON_PROJECT_GEMINI/STATUS.md` 원문 —
  "independent track not yet implemented", Gemini CLI 미확인. **아직 시작 전.**
- **종합상황실 4지표+순위 UI**: 런던프로젝트GPT가 오늘 커밋(`d7051f5`,`eb1ab43`)했으나
  나는 diff만 확인했고 브라우저로 직접 검증 안 함 — 다음 세션 확인 필요.
- 완성률은 항목별로 편차가 큼(승인 1/25, 원인진단 부분완료, n8n 기반만 완료 등) — 단일
  %로 뭉뚱그리지 않고 FINAL_ARCHITECTURE.md 1절 표로 정리.

---

## 2026-09-26 (5차) — 종합상황실 GSC "미확인" 원인 수정 + 실제 검증, 콘텐츠 템플릿화 발견

### GSC 크래시 버그 수정 (완료, 실측 검증됨)

원인: `scripts/daily_site_traffic.py`의 `latest_daily_stats()`,
`get_index_coverage()`에 try/except가 없어서 사이트 1개 커넥션 에러가 27개
전체 루프를 죽였다. 실제 로그(run 36205063081)로 확인: k-health365.com
1개만 처리하고 `ConnectionResetError`로 전체 종료. 이 워크플로우는
2026-09-08 이후 사실상 멈춰 있었음(18일간 무실행, GitHub Actions run
이력으로 확인).

**수정**: 두 함수에 이 파일의 다른 함수들과 같은 try/except 패턴 적용,
사이트간 딜레이 0.2초→3초. 커밋 `bb0b649`.

**검증**: 수정 직후 워크플로우 실제 실행(run 36235591140, success) —
**27/27 사이트 끝까지 처리 완료.** koreainvest365.com·ki-korea.com 2곳은
503 에러로 데이터 못 가져왔지만 정직하게 에러로 기록되고 나머지 25개는
막지 않음(전에는 이런 부분실패 자체가 불가능했음 — 첫 실패에서 전체가
죽었으므로). **"미확인"을 강제로 숨긴 게 아니라 데이터가 실제로 채워지게
원인을 고친 것** — Chairman 지시("미확인이 안 나오게") 해석 시 유의.

### 콘텐츠 품질 — 크로스사이트 템플릿화 발견 (조사 필요, 미수정)

koreamedicaltour.com, sis-korea.com, jobkorea365.com, kstudy365.com에서
2026-09-22자 글 4건을 실제로 읽어봄. 결과:
- 개별 글 자체는 스팸/무의미 텍스트는 아님 — 주제에 맞는 실용적 가이드 톤.
- **그러나 4개 사이트 모두 동일한 문구로 시작함**: "Photo: Alena Darmel /
  Pexels . Illustrative planning photograph; not an identified applicant,
  adviser or client. License" — 그리고 구조가 거의 동일(도입 한 문단 → 소제목
  2-3개의 절차형 조언 → "Official reference: studyinkorea.go.kr/..." 로
  마무리). 길이도 전부 1600~1770자로 거의 동일.
- 같은 날 발행된 "짧은 템플릿형" 글과 별도로 각 사이트에 더 긴(2400~4700자)
  글도 있음 — 즉 최소 두 가지 콘텐츠 생성 경로가 있는 것으로 보이고, 짧은
  쪽이 사이트 간 구조를 거의 그대로 재사용하는 것으로 의심됨.
- **왜 중요한가**: 구글은 같은 소유자의 여러 사이트에 걸친 보일러플레이트/
  템플릿 콘텐츠를 낮게 평가하거나 스팸 정책 위반으로 볼 수 있음. 24개 중
  다수가 "필수 페이지는 있는데 미승인"인 상태였던 것(4차 기록)과 맞물리면,
  **이게 실제 원인 후보 1순위일 수 있음.**
- 원인 스크립트 특정 안 됨 — 다음 세션 작업: 이 "짧은 템플릿형" 글을 생성하는
  스크립트를 찾아서(`scripts/free_article_supplier.py` 등 후보), 사이트별로
  실제 차별화된 내용을 만드는지 아니면 문단 구조를 그대로 복제하는지 코드
  레벨에서 확인. 추측 아님 — 지금은 증상만 확인, 생성 코드는 아직 못 봄.

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
