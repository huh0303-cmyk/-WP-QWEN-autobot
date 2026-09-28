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
- 2026-09-28 10:10 KST — PR #131을 GitHub `main`의 `1c518628`로 병합했다. 운영 서버 HEAD도 같은 commit이며 이번 대상 코드 4개 파일은 Git 기준 수정 없음, control/gateway 서비스 active, 수동 UI/API 파일 존재를 재확인했다. 병합 후 일반 VPS deploy run `36364918940`은 배포된 commit `1c518628`과 내부 배포 요청의 오래된 target `2ec27ce3`가 달라 실패로 끝났다. 운영 배포 자체는 현재 commit에 도달했으므로 이 실패는 배포 요청 target 경합이다. 전체 테스트 run은 기존 41건 실패를 이어받았다. 별도 `Deploy London n8n` run `36364918967`은 성공했다.
- 2026-09-28 10:24 KST — 사용자 요청으로 Codex 연결 구성을 점검했다. 맞춤형 MCP에는 공식 read-only OpenAI Docs 서버 `openaiDeveloperDocs`를 전역 추가하고 CLI에서 enabled/streamable HTTP를 확인했다. GitHub, WPVibe, Google Drive/Gmail/Calendar는 이미 설치된 것으로 확인했으며 WordPress 개별 사이트 연결 여부는 확인하지 않았다. GSC Wizard는 Search Console/연결된 GA4 분석 후보로 추천했으나 사용자의 Google 로그인 전이므로 연결되지 않았다. AdSense 전용 적합한 플러그인과 n8n 플러그인은 검색에서 확인되지 않았다. 반복 운영용 `london-blog-ops` 스킬을 저장소와 Codex 개인 스킬 디렉터리에 같은 내용으로 추가했고 SHA256 일치 및 validator 통과를 확인했다. 상세 연결 상태와 근거 구분은 `docs/LONDON_PROJECT_CODEX_INTEGRATIONS_2026-09-28.md`에 기록했다. 비밀정보는 저장하지 않았고 운영 서버/발행 흐름은 변경하지 않았다.
- 2026-09-28 10:25 KST — 연결 구성과 운영 스킬 문서 PR #132를 `main` commit `a098047`로 병합하고 fetch-back으로 확인했다. Codex 전역 문서 MCP는 재확인 시 enabled였고 개인 `london-blog-ops` 스킬 validator도 재통과했다. GSC Wizard는 마지막 연결 상태 확인에서 여전히 미설치였으므로 사용자 Google 로그인 이후 다시 확인해야 한다.
- 2026-09-28 11:04 KST — 런던프로젝트GPT 글쓰기 한도·이미지 fallback·4번 발행검증을 점검했다. Gemini→유료 GPT-5 mini API→로컬 Ollama 순서이며 월간 budget guard는 추정 비용만 다뤄 할당량 초과를 보증하지 않는다. 운영 환경에는 Pexels/Pixabay 키가 있지만 stock 활성화 플래그, Replicate 토큰 및 GH asset 토큰이 없어 이미지 제공은 현재 보장되지 않는다. 일반 글에 Google Indexing API를 사용하는 것은 공식 제한에 맞지 않아, 공개 발행 직후 GitHub Actions에서 기존 GSC 서비스 계정으로 해당 사이트맵을 제출하는 경로를 구현했다. 중복 발행 방지, GSC 상태 표시, 실패 영수증을 포함한다. 로컬 표적 테스트 5개 통과, Python 구문·workflow YAML·diff 검사 통과, jobkorea365.com sitemap HTTP 200 확인. 실제 운영 dry run/배포 결과는 후속 항목에 기록한다. 상세: `docs/LONDON_GPT_GSC_AFTER_PUBLISH_2026-09-28.md`.
- 2026-09-28 11:10 KST — GSC 자동 제출 PR #133을 GitHub `main` commit `a341d55`로 병합하고 fetch-back 확인. `Deploy London n8n` 성공, VPS HEAD 동일. 일반 deploy job은 이미 새 commit이 적용된 상태에서 이전 target `a098047`을 요구해 target mismatch로 실패했으며 control service를 수동 재시작해 active 확인. GitHub Actions GSC dry run `36368595932` 성공: 공개 글, sitemap, GSC property `sc-domain:jobkorea365.com` 확인. 기존 발행 글 영수증으로 VPS의 자동 dispatch를 시험해 실제 제출 run `36368699807` 성공, 사이트맵 `https://jobkorea365.com/sitemap_index.xml` 제출 및 `lastSubmitted=2026-09-28T02:09:26.656Z` 확인. 운영 서버에 `submitted` 영수증이 도착했다. 새 글은 발행하지 않았으며 개별 글의 Google 색인 완료를 뜻하지 않는다. 로그인 보호된 control API의 실제 UI 렌더는 별도 세션 검증이 필요하다.
- 2026-09-28 KST — 사용자 지적: `control_center/templates/london_gpt.html`을 로컬 `file://`로 열면 Jinja 코드가 보이고, 웹앱 선택은 WP에 한정됐다. 로컬 파일은 공식 웹앱 URL로 이동시키고, 저장소 레지스트리에서 WordPress 27·Blogspot 33·Naver 3·Tistory 5 목적지를 제공하도록 확장했다. 사용자가 Naver N2=`huh3`, N3=`huh4`를 직접 제공했다. 두 주소는 HTTP 200 확인; 로그인/발행 검증 전이므로 백그라운드 자동화는 비활성 유지. 네이버/티스토리 웹앱 실행은 수동 발행으로만 허용한다. Blogspot 기존 API 경로는 자동/수동 실행 가능하다. 로컬 표적 테스트 7개, Python 구문, inline JS 구문, diff 검사 통과. 운영 배포/화면 확인은 후속 항목에 기록한다.
- 2026-09-28 11:32 KST — 플랫폼 선택 PR #134를 `main` commit `8f42f99`로 병합, fetch-back 확인. `Deploy London n8n` run `36370103683` 성공, VPS HEAD 동일, control/gateway 서비스 active. 일반 deploy run `36370103690`은 이미 새 commit 배포 후 구 target `8675c4d`와 비교한 target mismatch로 실패했고 control service를 재시작했다. 시작 직후 502 한 번은 302 로그인 응답으로 회복. 로그인된 실제 웹앱 탭을 새로고침해 플랫폼 WordPress/Blogspot 33/Naver 3/Tistory 5와 N2 `huh3`, 티스토리 카테고리, Naver 자동 모드 비활성·수동 모드를 확인했다. 기존 전체 관련 테스트 확대 시 4개 실패는 Blogger의 과거 draft 정책 기대값과 이미 누락된 YouTube workflow 경로에서 발생했고 이번 변경 파일과 무관하다. 이어서 플랫폼별 드롭다운이 다른 플랫폼 항목을 포함하지 않게 DOM 옵션을 실제 필터링하고, 의료 자격 블로그의 기존 전문 페르소나를 UI에도 적용하는 보완을 시작했다. 보완 표적 테스트 8개와 JS 구문 검사 통과; 후속 commit/배포 결과는 다음 항목에 기록한다.
- 2026-09-28 11:37 KST — 후속 PR #135를 `main` commit `c90434f`로 병합·fetch-back 확인. 일반 VPS deploy run `36370466452` 성공. 로그인된 실제 `https://control.korea365.org/london-gpt` 화면을 새로고침해 플랫폼별 사이트 드롭다운이 해당 플랫폼만 포함하는 것을 확인: WordPress 27, Blogspot 33, Naver 3(`huh0303`/`huh3`/`huh4`), Tistory 5. Naver/Tistory에서는 자동 라디오 disabled, 수동 준비 버튼과 카테고리 표시를 확인했다. 템플릿 `{{ ... }}`는 실제 화면에 보이지 않는다. 테스트 과정에서 새 글 발행/예약 워크플로는 실행하지 않았다. 네이버 N2/N3 로그인 및 사람 발행 뒤 공개 URL 검증, Blogger 33개의 개별 실발행은 이번 변경에서 수행하지 않았으므로 운영 연결 완료로 오인하지 않는다.
- 2026-09-28 13:37 KST — 사용자 지시로 런던프로젝트GPT 글쓰기의 무료 모델 다중 fallback, AdSense 적합성 지침, 모델 선택 드롭다운, 무료 이미지 기본값, 수동 복사/글쓰기 링크를 구현했다. 실패 실행 `lgpt-20260928-034822-377038`에서 Gemini 429, GPT API 잔액 부족 429, 로컬 75초 시간 초과가 관찰됐다. 공식 Gemini API 가격표/모델/한도 문서를 확인하고 운영 키에서 3.1 Flash-Lite의 짧은 생성 성공을 확인했다. 모델 가격과 프로젝트 실제 청구 등급은 별개이므로 무과금·무실패 보증은 하지 않는다. 표적 테스트 14개, 관련 기존 테스트 15개 통과; 최종 배포 및 장문 실측은 후속 결과에 기록한다. 발행은 실행하지 않았다.
- 2026-09-28 13:43 KST — PR #136을 `main` commit `2ec9e8d`로 병합하고 fetch-back 확인. VPS HEAD 동일, control/gateway 서비스 active. GitHub 전체 CI는 기존 타 영역 계약 불일치/누락 파일 등 30 failed·620 passed로 실패했으며 이번 수정의 표적 테스트는 모두 통과했다. Windows 전체 테스트 수집은 기존 Linux 전용 `fcntl` import 때문에 중단되었다. 실패했던 `blogger_koreanews` 실행의 Agent 2만 재검증했다. Gemini 3.5 Flash가 503이었으나 3.1 Flash-Lite가 원고를 반환했고, 2.5 Flash/Flash-Lite는 429, 3.5 Flash-Lite도 원고를 반환했다. 두 원고 모두 메타 설명의 100~119자 후처리에서 거절돼 발행 없이 종료됐다. 짧은 영어/한국어 메타 설명을 주제에 맞춘 완성 문장으로 고치는 후속 패치를 진행한다. 재검증 전 상태는 Agent 2 실패이며, Agent 3/4는 호출하지 않았다.
- 2026-09-28 13:56 KST — 메타 설명 보완 PR #137을 `main` commit `25671fd`로 병합·fetch-back 확인. VPS HEAD도 동일. 동일 실행 `lgpt-20260928-034822-377038`의 Agent 2만 재실행해 Gemini 3.5 Flash 원고, 기계적 품질 점수 100, 메타 설명 102자, 본문 가시문자 1,434자, H2 세 개를 확인했다. Agent 3/4는 실행하지 않았고 발행 영수증이 없다. 원고를 사람이 읽어보니 2026년 코로나 백신 접종 대상·예약 방법·동시 접종을 공식 출처 없이 현재 사실로 단정하는 부분이 있어 의학적 사실 확인 전 공개하면 안 된다. 또한 최초 Agent 1 결과의 검색량 `10000+`, `2000+`는 출처가 없어 허위 수치로 간주한다. 연구 숫자 정리, 모델 선택 상태 보존, 의료 주제 자동 공개 차단·수동 검토 전환을 후속 패치로 진행한다. 표적 테스트 36개 통과; 배포 결과는 후속 기록한다.
- 2026-09-28 14:03 KST — 모델 선택 상태 보존·검색량 정리·의료 글 검토 게이트를 PR #138 `main` commit `67b4fae`로 병합했고, 기존 실행도 보호하는 보완 PR #139 `main` commit `80e9ce0`을 병합·fetch-back 확인했다. 운영 서버 HEAD `80e9ce0`, control/gateway 둘 다 active, gateway health HTTP 200. 실패 실행 `lgpt-20260928-034822-377038`에서 Agent 3만 실행했고 민감한 백신 주제라 이미지 없음으로 완료. Agent 4를 실행하자 출판자 호출 없이 `manual_required`, 빈 URL/post ID로 전환됐다. 연구 증거의 근거 없는 검색량을 `unavailable (수치 출처 미확인)`으로 정리하고 `receipt` 없음·수동 검토 이유를 확인했다. 실제 공개 글은 만들지 않았다. 로그인된 웹앱 새로고침에서 Gemini 무료 등급 5종/로컬 Qwen, 유료 GPT 명시, 무료 스톡 이미지 기본값/유료 Replicate 선택 옵션이 보임을 확인했다. 표적 테스트 36개 통과, JavaScript 구문 통과. 이 의료 원고는 공식 출처 검토·수정 전까지 발행 금지다.
- 2026-09-28 23:50 KST — Blogspot 33개 일일 발행 감사(`blogger33-daily-2026-09-28`). VPS `187.127.121.57`의 `korea365-blogger33-daily.timer`는 enabled/active이며 00:05 KST 예약 서비스가 성공 종료했다. `/opt/korea365/data/blogger33-schedules/2026-09-28.json`은 설정의 자동화 대상 33개와 정확히 일치하고 사이트·unit 중복 및 누락 없음, 33개 모두 scheduled. 각 transient service는 한 번씩 시작됐다. journal 기준 공개 성공 15개, 실패 18개이며 실패 모두 Gemini HTTP 429 할당량 초과(각 3회 시도). 실패 키: `kworld365_kpop`, `ktrip365`, `koreawedding`, `korea365`, `kstudy365`, `sis`, `oliveyoung`, `kfinance365`, `kinvest365`, `jobglobal`, `jobkorea365`, `kikorea`, `krealestate`, `koreanews`, `kwellness_lab`, `jobinkorea`, `kskin365`, `kmedical_job_center`. OAuth/Blogger API 실패나 중복 공개 증거는 없었다. `/opt/korea365/artifacts/blogger-33-public-results.json`은 해당 run key이나 마지막 `kmedical_job_center` 실패 한 건만 담아 전체 일일 결과로 사용할 수 없다. GitHub Actions `publish-blogger-33-now.yml` 실행·수동 재발행·선택 재시도는 하지 않았다. 다음 조치: Gemini 무료 할당량/프로젝트별 사용량과 fallback 적용 상태를 조사하고 할당량 회복 후 각 실패 키의 publication marker/공개 URL을 먼저 확인한 뒤 미발행 건만 선택적으로 복구한다.
- 2026-09-29 KST — `task_id=control-media-consolidation-20260929`. 사용자 최종 결정으로 외부에 보이는 운영 주소를 CONTROL / BLOG / YOUTUBE+SNS 세 개로 단순화한다. `youtube.korea365.org`는 삭제하지 않고 기존 북마크 호환용으로 `sns.korea365.org` 통합 미디어 화면에 이동시킨다. CONTROL 첫 화면은 블로그와 YouTube+SNS 두 표를 같은 시각 비중으로 배치하고, 각 행에 수익 연결 상태·방문/조회 지표·실제 최근 발행일시·기존 발행 워크플로로 이동하는 즉시발행 버튼을 둔다. 블로그 버튼은 기존 London GPT 4-Agent 화면을 대상 사이트·자동·즉시공개 상태로 미리 선택하며 자동 실행 자체는 추가 클릭 전 시작하지 않는다. 신규 파이프라인이나 데이터 저장소는 만들지 않는다. 최근 발행 스냅샷은 날짜만 자르지 않고 KST 분 단위 시각을 보존하도록 보완한다. 코드 검증·배포 결과는 후속 항목에 기록한다.
- 2026-09-29 KST — 같은 작업의 모바일·속도 방향을 사용자와 재확정했다. 상세 YOUTUBE+SNS 화면도 카드 나열을 제거하고 가로 스크롤 가능한 엑셀형 계정 표로 단순화했으며, 모바일에서는 요약 상자를 숨기고 필터 탭과 표를 우선한다. YouTube와 Instagram/Threads/TikTok/Facebook은 `통합` 필터 하나에서 함께 보이고 플랫폼별 필터는 보조 탐색으로만 남긴다. 표적 테스트 20개 통과, Python 구문 검사 통과. Windows 전체 구형 테스트는 기존 Linux 전용 `fcntl` import 때문에 수집 단계에서 중단되어 운영 Linux/CI에서 별도 확인한다. 실제 발행은 실행하지 않았다.
- 2026-09-29 KST — 사용자 지시로 London GPT Agent 3 이미지 경로를 유료 생성 없이 A=Pexels, B=Pixabay, C=Wikimedia Commons 순서의 3단 무료 fallback으로 확장했다. Wikimedia는 키 없는 공식 API를 사용하되 CC0/Public Domain/PDM만 허용하고, 주제 단어 일치·가로 1000px 이상·원본/출처 도메인·영구 호스팅 검증을 기존과 동일하게 거친다. London GPT 화면과 API에서 Replicate 유료 선택을 제거했다. 세 무료 소스 모두 안전한 일치 이미지를 찾지 못하면 무관하거나 권리 불명 이미지를 넣지 않고 이미지 없음으로 중단한다.
- 2026-09-29 KST — 사용자 확정 IA에 따라 2면 `blog.korea365.org`를 블로그 발행 화면으로 재구성했다. 사이트/공개·초안 드롭다운과 기존 London GPT 4-Agent 진입 버튼을 첫 영역에 두고, Agent 1의 검색량·Google/Naver 신호·미디어 언급량 주제 선정을 가장 강조했다. 아래에는 68개 블로그를 카드가 아닌 모바일 가로 스크롤 표로 배치하고 행별 즉시발행을 연결했다. 3면 `sns.korea365.org`는 YouTube+SNS 통합 발행 표를 유지한다. 신규 발행 엔진을 만들지 않고 기존 n8n 4-Agent 경로를 재사용한다.
- 2026-09-29 KST — PR #141을 `main` commit `4e1bfee5`로 병합하고 VPS deploy run `36491823242` 성공을 확인했다. 표적 테스트 28개, Python 구문, Blog/Control inline JavaScript 구문, Jinja 템플릿 로드, diff 검사가 통과했다. VPS IP를 고정한 HTTPS 점검에서는 `blog.korea365.org`와 `sns.korea365.org`가 각각 올바른 로그인 URL로 HTTP 302를 반환해 서버/vhost 배포는 확인됐다. 그러나 공개 DNS에는 `control.korea365.org` A 레코드만 있고 `blog.korea365.org`와 `sns.korea365.org` 레코드가 없어 일반 브라우저는 `ERR_NAME_NOT_RESOLVED` 상태다. 저장소에는 DNS 제공자 API 권한이 없어 레코드 생성은 미실행이며, 두 A 레코드를 `187.127.121.57`로 추가한 뒤 실화면 재검증이 필요하다. 실제 글·영상·SNS 발행은 실행하지 않았다.
- 2026-09-29 KST — 사용자 질문을 반영해 3면 명칭을 `YOUTUBE + SNS 생산·발행 통제실`로 명확화하고, YouTube core 10채널의 모호한 `제작·업로드 연결 완료`를 `비공개 제작·업로드 가능 · 공개는 별도 승인`으로 교체했다. 미디어 계정 중 게시 연결이 완료되지 않은 항목을 모아 보는 `로그인·권한 필요` 전용 필터와 개수를 추가했다. 브라우저 세션 존재는 API/write 권한 완료를 의미하지 않으며 공개 발행은 계정별 권한과 영수증 검증 전까지 차단한다.
- 2026-09-29 KST — 사용자 지시로 YOUTUBE+SNS 생산·발행 표의 맨 왼쪽에 `번호` 열을 추가했다. 번호는 현재 선택한 필터에서 보이는 행 기준으로 1부터 연속 표시한다.
- 2026-09-29 KST — SNS 전용 화면의 혼동을 없애기 위해 과거 모든 플랫폼을 뜻하던 `전체`와 미디어만 뜻하던 `통합`을 합쳤다. 이제 `전체`는 YouTube/TikTok/Instagram/Facebook/Threads 전체만 의미하며 WordPress/Tistory/Naver 필터는 제거했다. 표 마지막 열은 `생산·발행 트리거`로 명시하고, YouTube 연결 채널의 버튼은 생산→비공개 업로드까지이며 자동 공개는 아니라는 설명을 화면에 고정했다.
- 2026-09-29 KST — YOUTUBE+SNS 표의 플랫폼 식별성을 높이기 위해 같은 플랫폼의 행 전체를 같은 연한 배경색으로 고정했다. YouTube=연한 빨강, TikTok=연한 회색, Instagram=연한 분홍, Facebook=연한 파랑, Threads=연한 중성 회색이며 플랫폼 배지는 더 진한 동일 계열 색으로 표시한다.
- 2026-09-29 KST — 사용자 화면 피드백에 따라 상단 요약 카드와 하단 필터 버튼도 행 색상과 같은 플랫폼 팔레트로 통일했다. 카드/버튼 여백·글자·모서리를 줄이고 숫자와 `개`를 한 줄에 배치해 모바일과 데스크톱 모두 더 촘촘하게 표시한다.
- 2026-09-29 KST — YouTube 인벤토리를 언어 Survival 10 → 플레이리스트 5 → 지식 5 → 헬스 2 → 쇼핑·예약 1 순서로 정렬했다. 확인된 언어 채널 7개 외 중국어·베트남어·포르투갈어 3개는 누락시키지 않고 `채널 생성·선택 필요` 자리표시 행으로 노출한다. 표는 `번호 | 플랫폼 | 구분 | 채널/계정 | 채널 주제 | 운영 역할 | 연결 상태 | 생산·발행 트리거 | 계정 ID`로 재구성해 계정 ID를 맨 끝으로 이동했다. 모든 열은 드래그로 42~460px 사이에서 조절할 수 있고 브라우저 localStorage 키 `k365-social-column-widths-v2`에 마지막 폭을 저장한다.
- 2026-09-29 KST — YOUTUBE+SNS 생산표에 `구독자·팔로워(증감) | 방문·조회수(증감) | 콘텐츠수(증감)` 열을 추가하고 기존 `/api/control/social-ranking` 실제 지표를 5분마다 갱신해 행의 채널 ID/핸들/이름으로 매칭한다. YouTube 콘텐츠 증감은 `situation_room_history.json` 최신/이전 videos 차이로 계산하고, SNS 콘텐츠 값은 실제 audience metrics에 값이 있을 때만 사용한다. 연결되지 않은 값은 0으로 만들지 않고 `미집계`로 표시한다. 전체 정책 계정 24개가 API에서 제외되지 않도록 과거 3개 역할 필터를 제거했고 목표 인벤토리를 YouTube 20 + SNS 24 = 44로 바로잡았다. 새 12열 폭 저장 키는 `k365-social-column-widths-v3`다.
- 2026-09-29 KST — YOUTUBE+SNS 생산표에 `$ 수익`과 `채널/페이지 생성일` 열을 추가했다. 운영 기록에서 수익화 승인이 확인된 서울국제대학-TOPIK센터 1개 행은 금박 테두리로 표시한다. YouTube 수익 OAuth가 아직 없어 금액은 만들지 않고 `수익 OAuth 필요`로 표시한다. 생성일은 opening snapshot의 실제 YouTube 채널 날짜 20개만 `YYYY-MM-DD`로 표시하고 원본이 없는 SNS 계정은 `미확인`으로 둔다. 표적 테스트 10개, Python/JavaScript 구문, 44행 API 빌드 검증 통과. 새 14열 폭 저장 키는 `k365-social-column-widths-v4`다. 실제 발행은 실행하지 않았다.
- 2026-09-29 KST — 사용자가 제공한 YouTube 최종 목록을 공개 피드와 재대조했다. 중국어 `UCGTd7RhfaUaGGbVRsNPUN6Q`, 포르투갈어 `UCKvKhETLGPaRV3qfWv2bM2g`, 베트남어 `UCRZ0uc_bxKDMwz3noBBi9KQ`를 실제 채널명·최신 영상과 확인해 인벤토리에 연결했다. 구성은 플리 5 + 지식 5 + 언어 Survival 9 + 기타 5 = 24개이며, `SIS-Language Center/@sis_languagecenter`만 공개 주소가 HTTP 404라 UC ID 미확인으로 유지한다. 통합 API 목표는 YouTube 24 + SNS 24 = 48로 갱신했다. 표에는 `최근 발행일`을 `YYYY-MM-DD`로 추가하고 새 15열 폭 저장 키를 `k365-social-column-widths-v5`로 올렸다. TOPIK은 수익화 승인 상태만 금박 표시하며 수익 OAuth/금액은 아직 미연결이다. 실제 영상·게시물 발행은 실행하지 않았다.
- 2026-09-29 KST — 사용자 정정에 따라 `서울국제대학-TOPIK센터`를 Korean Survival 언어 채널로 분류했다. 최종 YouTube 구성은 `언어 Survival 10 + 플레이리스트 5 + 지식 5 + 헬스 2 + 쇼핑 2 = 24`다. 언어 표 순서는 Korean/TOPIK → German → French → Italian → Spanish → Chinese → Portuguese → Vietnamese → English → Japanese다. 헬스는 Japan/일본어권과 USA/영어권으로 분리하고, 쇼핑은 `Seoul_Jisoo1/@rosiespicks`와 `SIS-Language Center` 전환 예정 채널 두 개로 정했다. SIS 채널은 정확한 UC ID가 아직 없어 실제 이름·핸들·API 변경 전 확인 필요 상태를 유지한다. TOPIK의 수익화 승인·수익 OAuth 미연결 상태와 금박 표시는 그대로 유지한다. 실제 영상 발행은 실행하지 않았다.
