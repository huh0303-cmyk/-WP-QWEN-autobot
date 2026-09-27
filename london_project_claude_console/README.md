# 런던프로젝트클로드 — Naver/Tistory 블로그 자동화 웹 콘솔

Chairman이 제공한 Windows Electron 데스크톱 콘솔(`blogauto-naver-tistory`)을 브라우저 기반 웹 앱으로
포팅한 것입니다. PC/모바일 어디서든 URL + 로그인으로 접속하며, 오너와 베트남 직원이 동일 권한으로
공유 사용합니다.

## 이 트랙의 범위 (2026-09-27 Chairman 확인)

- **범위: Naver + Tistory 콘솔 확장만.** WordPress 24개 / Blogspot 33개는 기존
  `docs/LONDON_4_AGENT_N8N_LOCK_2026-09-27.md`(GPT/PM 트랙 locked n8n 파이프라인)에 그대로 둔다.
- **플랫폼: 브라우저 웹앱 하나**, PC/모바일 겸용, 설치 불필요, 기존 Hostinger VPS에 호스팅.
- **베트남 직원: 오너와 동일 권한**의 공유 로그인 1세트 (별도 언어/권한 계층 없음).
- **아키텍처: Node/Express + WebSocket** (Electron IPC를 HTTP/WS로 대체). n8n을 쓰지 않는다 — 업로드된
  Electron 콘솔의 검증된 코드(특히 `naverPublisher.js`의 로그인/캡챠/세션-복구 로직)를 그대로
  재사용하는 것이 최우선 목표였기 때문.

> ⚠️ **같은 저장소에 "런던프로젝트GPT" 트랙이 별도로 WP24+Blogspot33+Naver+Tistory를 하나의 n8n 기반
> 콘솔로 통합하는 `docs/LONDON_PROJECT_GPT_BLOG_CONSOLE_LOCKED_SCOPE_2026-09-27.md`를 OWNER LOCKED로
> 커밋해 두었으며, 그 문서는 "런던프로젝트클로드"라는 이름을 이 용도로 쓰지 말라고 명시한다.**
> **2026-09-27 Chairman이 직접 확인: 이 클로드 트랙은 별개로 계속 진행, 이름·범위 그대로 유지.**
> 두 트랙이 같은 요구사항(Naver/Tistory 웹 콘솔)에 대해 서로 다른 이름·아키텍처로 병행 개발 중이라는
> 사실을 다음 세션/GPT 트랙도 인지해야 함 — `docs/LONDON_PROJECT_CLAUDE_STATE.md` 16차 기록 참고.

## 디렉토리 구조

```
london_project_claude_console/
  server/
    jobRunner.raw.js     # 업로드된 원본 Electron main.js (build 스크립트 입력, git에는 안 올림)
    build_jobRunner.js   # main.js -> jobRunner.js 변환 스크립트 (재실행 가능, 감사용)
    jobRunner.js         # 변환 결과. safeLog~startJob 구간은 원본과 byte-for-byte 동일
    server.js            # Express + WebSocket 서버, 로그인 세션, ipcMain 채널 -> HTTP 라우트 매핑
  lib/                    # 원본 그대로 포팅 (Electron 의존성 없음, 코드 미변경)
    accountStore.js embedding.js history.js settings.js codexRunner.js
    imageAssets.js naverPublisher.js search.js tistoryPublisher.js
  public/
    index.html styles.css  # 원본 렌더러, 거의 그대로 (샘플이미지 업로드용 hidden <input> 1개만 추가)
    app.js                 # 원본 렌더러 로직 100% 그대로 (window.blogAuto 호출부 변경 없음)
    bridge.js               # 신규: window.blogAuto를 fetch/WebSocket으로 재구현 (원본 preload.js 대체)
    login/index.html        # 신규: 공유 로그인 페이지
  deploy/README.md         # VPS 배포 절차 + Xvfb/x11vnc/noVNC 원격 브라우저 뷰 설정
  runtime/                  # 실행 중 생성되는 계정/설정/히스토리 데이터 (git 미포함)
```

## 왜 이렇게 포팅했나 (안전성 우선순위)

`naverPublisher.js`의 README/코드 주석에 명시된 원칙 — **네이버 ID/비밀번호 자동입력과 로그인 버튼
자동클릭은 의도적으로 제거되어 있고, 로그인/캡챠 화면이 뜨면 사용자가 열린 Chrome 창에 직접 입력해야
한다** — 는 실제 서비스에서 계정 잠금/이상탐지를 피하기 위해 검증된 안전장치입니다. 이 로직을
재작성하지 않고 **그대로 재사용**하기 위해:

1. `lib/*.js`는 전부 원본 그대로 복사 (grep으로 Electron 의존성 없음을 사전 확인).
2. `server/jobRunner.js`는 원본 `main.js`의 `safeLog(...)`부터 `startJob(...)`까지(작업 오케스트레이션
   전체 — 키워드 리서치 레인 플래닝, 소스 품질 검증, 세션 복구, 발행 순서 등) **한 글자도 수정하지
   않고** 그대로 옮겼습니다. `server/build_jobRunner.js`를 실행하면 원본에서 다시 생성할 수 있어
   감사(audit) 가능합니다.
3. `public/app.js`(렌더러 UI 로직)도 원본 그대로이며, `window.blogAuto` 인터페이스를 구현하는
   `bridge.js`만 신규 작성했습니다.
4. 유일하게 손댄 UI 파일은 `index.html`의 샘플 이미지 업로드 버튼 옆에 숨김 `<input type="file">` 1개
   추가 — 데스크톱의 네이티브 파일 선택 다이얼로그(`dialog.showOpenDialog`)를 브라우저에서 대체하기
   위함이며, 클릭 동작은 `bridge.js`에서만 처리하고 `app.js`는 건드리지 않았습니다.

## 실행 (로컬 개발)

```bash
cd london_project_claude_console
npm install
LPC_USER=admin LPC_PASS=<strong-password> node server/server.js
# http://localhost:8787 (없는 계정으로 로그인 시도하면 /login으로 리다이렉트됨)
```

Naver/Tistory 실제 발행을 로컬에서 테스트하려면 화면이 있는 환경(맥/윈도우/리눅스 데스크톱)이어야
Chrome 창이 뜹니다. 헤드리스 서버(VPS)에서는 `deploy/README.md`의 Xvfb+noVNC 설정이 필요합니다.

## 아직 안 된 것 / 다음 세션 확인 사항

- **VPS 실배포는 아직 안 함** — SSH 접근 권한이 없어 systemd 유닛 설치/활성화를 이 세션에서 직접
  실행하지 못했음. `deploy/README.md` 절차를 Chairman 또는 GitHub Actions workflow로 실행 필요.
- **noVNC 화면에서 실제 Naver 로그인/캡챠 E2E 테스트 미실시** — Xvfb 해상도(1366x900)와
  `naverPublisher.js`의 좌표/DOM 탐색 로직이 실기에서 잘 맞는지 확인 필요.
- **동시 작업 큐잉 미구현** — 원본과 동일하게 `activeJob` 단일 슬롯 (한 번에 한 작업만); 베트남
  직원과 오너가 동시에 다른 계정으로 발행을 시도하면 뒤에 요청한 쪽이 "이미 실행 중" 에러를 받음.
  여러 명이 동시에 쓸 경우 큐/대기열 UI 추가가 필요할 수 있음 — Chairman 확인 필요.
- **GPT 트랙과의 이름/범위 충돌은 Chairman 확인 완료** (위 경고 박스 참고) — 다만 GPT 트랙이 이후
  세션에서 이 사실을 모른 채 같은 저장소에 계속 다른 방향으로 커밋할 수 있으므로, 상태 문서를 통해
  지속적으로 동기화 필요.
- **LPC_PASS 등 자격증명은 아직 GitHub Secrets/서버 환경변수로만 존재해야 함** — 이 리포지토리
  어디에도 평문으로 커밋하지 않았음 (확인 완료).
