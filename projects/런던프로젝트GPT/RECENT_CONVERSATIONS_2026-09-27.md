# 런던프로젝트GPT — 최근 대화 통합 기록

기준 시각: 2026-09-27 08:43 KST  
범위: 이 프로젝트에서 확인 가능한 2026-09-02~09-27 대화 요약, 최신 사용자 지시, 기존 프로젝트 문서.  
용도: 다음 작업자가 대화 맥락을 재질문하지 않고 이어받기 위한 기록.

> 이 문서는 대화 원문 전체의 내보내기 파일이 아니다. 현재 접근 가능한 최근 대화의 핵심 지시와 결정사항을 주제·날짜별로 재구성했다. 생략된 대화 원문과 첨부 화면의 세부 내용까지 모두 확보했다고 주장하지 않는다. 사용자의 지시는 **요구사항**, GitHub 파일과 공개 URL은 **기록된 증거**, 이전 AI의 "완료" 발언은 **검증 전 주장**으로 구분한다. 비밀번호·OAuth 토큰·쿠키는 기록하지 않는다.

## 1. 프로젝트 경계와 정본

- 공식명: **런던프로젝트GPT**. GPT가 독립적으로 판단·구현·책임지고, Claude 및 Gemini 프로젝트와 책임을 섞지 않는다. 작업 단계를 GitHub에 남겨 중단 후에도 재개할 수 있게 한다. (09-26)
- 사용자가 최종 평가용 경로를 `projects/런던프로젝트GPT/`로 지정했다. 이전 `projects/LondonProjectGPT/`와 병존하므로 이 한글 경로를 평가·인계의 시작점으로 삼는다. (09-26)
- 이 폴더의 `README.md`, `ARCHITECTURE.md`, `WORKFLOWS.md`, `BACKUP_RECOVERY.md`, `APP_SPEC.md`, `OPERATIONS_MANUAL.md`, `FAILURE_HANDLING.md`, `EVALUATION_CHECKLIST.md`, `STATUS.md`, `HANDOFF.md`, `CONNECTIONS.md`, `manifest.json`을 우선 읽는다. 개별 파일에 적힌 사실도 최신 실행 증거로 재확인한다.
- 기존 `docs/LONDON_PROJECT_BLUEPRINT.md`(09-18)와 09-26 정본은 실행 구조가 다르다. 09-18 문서는 WP/News/Blogger를 GitHub 독립 공장으로, VPS를 YouTube 전용으로 기술한다. 09-26 `README.md`는 VPS 24시간 런타임+n8n 중앙 조율, 기존 Python/systemd 실행기 재사용을 기술한다. **두 설계를 하나의 확정 구현으로 합쳐서 보고하지 않는다.** 현재 운영 상태는 실제 배포와 영수증 기준으로 판정한다.
- `STATUS.md`(09-26)는 Docker, n8n Community 컨테이너와 health, 로컬 gateway/systemd, `WP25_MASTER`와 `BLOGGER33_MASTER` 가져오기, 관련 GitHub Actions 성공을 기록한다. 같은 문서는 WP25·Blogspot33 전체 발행 영수증, 뉴스·티스토리·네이버·유튜브·SNS 마스터, 복구 시험을 미완료로 기록한다. 약 55%라는 추정치를 완료율 증거로 사용하지 않는다.

## 2. 운영 범위와 우선 목표

| 영역 | 최신 운영 수량·역할 | 주의 |
|---|---|---|
| 일반 WordPress | 25개 | AdSense 승인 가능성, 주제 집중, 실제 발행 영수증 |
| 신문사 | 2개: The Seoul Journal, Koreanews365 | 일반 WP와 별도 기준·RSS/출처 검증 |
| Blogspot | 33개 | WP의 복사 글이 아닌 독립 글 |
| Tistory | 5개 | 브라우저 로그인 기반 연결·시험 발행 필요 |
| Naver Blog | 3개 | 브라우저 로그인 기반 연결·시험 발행 필요 |
| YouTube | 23개 채널 구조(플리 5, 지식 5, 언어 10, 건강 2, 쇼핑 1)라는 09-25/27 기록 | 자동 제작의 즉시 범위와 OAuth 대상은 별도 검증 |
| SNS | Instagram, Threads, Facebook, TikTok | 계정별 권한과 게시 URL을 각각 확인 |

- 09-18에 일반 WP 25, 신문사 2, Blogspot 33으로 수량을 정정했다. Tistory 5와 Naver 3은 핵심 운영 카드에서 제외하라는 09-25 지시가 있었지만, 09-26 프로젝트 README는 별도 로컬 실행 대상으로 포함한다. 카드 UI와 실제 발행 범위를 구분해 최신 화면·설정으로 확정한다.
- `k-health365.com`은 기준 AdSense 승인 사이트. 나머지 WP 24와 Blogspot 33의 핵심 KPI는 단순 발행량보다 AdSense 승인 가능성이다. `oliveyoungkorea.com`도 승인된 것으로 과거 대화에 기록되어 있으므로 승인 현황은 현재 계정에서 재확인한다.
- 사용자는 "총괄 PM으로 미리 판단하고 고치며 실제 방문자를 늘릴 것", "속도·완성·실제 발행까지"를 반복 요청했다. 파일 생성, 큐 등록, workflow 성공만으로 완료 보고하지 않는다.

## 3. WordPress·뉴스·Blogspot 콘텐츠

- 일반 WP 25는 사이트마다 핵심 주제 하나, 대표 카테고리 하나를 원칙으로 하고 필요할 때만 추가 카테고리 하나를 허용한다. 글 없는 카테고리는 25개 사이트에서 정리하라는 09-22 지시가 있다.
- 09-19 정제 계획: 백업과 복구 확인 뒤 보호할 Published 글만 공개 유지, 나머지 공개 글은 Private로 전환, 삭제 0, 페이지 제외, 대표 카테고리 정리, sitemap/Rank Math 점검, 필요할 때만 GSC 제출. 403/429/5xx/Bot/CAPTCHA/URL 불명확은 해당 사이트 `LOCKED`. `k-health365.com`, `krealestate365.com`, `kworld365.com`, `oliveyoungkorea.com`, `ksa-korea.org`는 당시 LOCKED로 기록. 09-19 `jobinkorea365.com` CAPTCHA 보고가 있었다. 잠금 해제의 실증 없이 일괄 변경하지 않는다.
- 09-19 사용자는 미발행 WP 사이트 전부에 글 하나씩 발행하라고 요청했다. 발행 요청과 실제 URL 영수증을 혼동하지 않는다. `CONNECTIONS.md`에는 `kstudy365.com` 공개 글 한 건과 `kstudy365.blogspot.com` 공개 글 한 건의 URL이 기록되어 있으나, 그것만으로 25/33 전체 완료를 뜻하지 않는다.
- Blogspot 33은 WP와 같은 주제어를 쓰더라도 독립적인 글로 작성한다. 기본 영어, 예외 한국어 채널 2개(`k-health365`, `koreanews365`)라는 이전 지시가 있다. About/Contact/Privacy/Terms, 주제 라벨, 정확한 ALT, 슬러그·제목 중복 방지, 승인/미승인 구분을 요구했다. 09-19 후속 정제는 색인된 보호 URL 대조, 초안 후보 분류, 대표 라벨 1개, 추가 비용 금지.
- 뉴스 2개는 짧은 기사 허용, 최신 RSS와 1차 출처를 확인하고 일반 WP와 별도 운영한다. 소스가 없는데 발행 건수를 채우지 않는다.
- 글쓰기 엔진은 09-02 지시에서 GPT-5 Mini로 변경하고 Gemini 글쓰기 중단을 요청했다. 이미지 1차 SDXL Lightning, 실패 시 FLUX Schnell, 다시 실패하면 무이미지. 이후 프로젝트 파일에 다른 provider가 명시되어 있으면 실제 설정과 최신 사용자 지시를 비교한다.
- 제목은 흥미를 끌되 반복 금지, 핵심 키워드 슬러그, H2/H3·표·FAQ·내외부링크·Schema, 이미지 ALT 정확히, KST 랜덤 시간·정각 회피·게시 간격을 요구했다. 09-02 Rank Math 목표는 70점으로 완화되었다.
- 과거 주 2~4회 지시와 09-18 blueprint의 활성 사이트 하루 1건 지시가 충돌한다. 무조건 일괄 발행하지 말고 현재 승인 전략과 계정별 상한·최신 운영 설정을 확인한다.

## 4. Control Korea365와 발행 증거

- 주소: `control.korea365.org`. 사용자 요구: 사이트/계정별 카드, 카드에서 바로 실제 결과로 이동, 현재 상태와 당일 발행량을 쉽게 찾기, WP 순위·이름·당일 방문자·바운스율 네 숫자를 강조, Google 색인 수 전수 조사. (09-02~09-24)
- `바이럴 즉시 발행`은 언급량과 검색량을 혼합해 후보를 고르고 버튼 한 번으로 검토·발행하는 요구였다. 버튼 존재·배포·실제 발행은 별도 확인한다.
- 09-17 새 콘솔 요구: KTrip365/KHealth365 시작 후 WP 25 확대, 페르소나·톤·글쓰기 엔진·이미지 장수·글자 수·카테고리·키워드 5개 이상 순환·예약·트렌드 추천. REST 미디어 업로드와 featured_media/본문 ALT·캡션을 검토했다.
- 09-24에는 계정별 한 카드, 독립 실행·재시도·실제 게시 영수증을 요구. 이전 응답은 94개 카드/84개 일일 발행 대상을 주장했지만 구·신 버전의 수량이 섞여 있었다. 이를 확정 수량으로 승격하지 않는다.
- 성공 판단: 웹은 정확한 대상+post ID+실제 URL, YouTube 비공개 업로드는 video ID+정확한 channel ID+`privacyStatus=private`, SNS는 계정별 공개 게시 URL. `STATUS.md` 미완료 목록을 계속 사용한다.
- 사용자는 UI 오류 반복을 지적하며 다른 채널까지 점검·수정·재발방지 후 GitHub에 기록하라고 09-25 지시했다.

## 5. GitHub·VPS·n8n·로컬 브라우저

- GitHub 저장소: `huh0303-cmyk/-WP-QWEN-autobot`, 기본 브랜치 `main`; 프로젝트 정본 경로는 위 1절. 09-26에는 단계별 결과를 프로젝트명으로 박제하라고 지시했다.
- Render는 완전히 삭제하고 Hostinger VPS로 이관한다는 지시가 반복되었다. 다시 Render를 실행 경로로 제안하지 않는다.
- 09-18 VPS 기록: `korea365-youtube-worker.service` active, 당시 scheduler.service/timer 없음, 큐 pending/running 비어 있음. 비용 중지 플래그를 해제한 뒤 YouTube 큐에서 실패가 다수 발생했다고 보고. 최신 서비스/큐 상태는 다시 실측해야 한다.
- 09-26 `STATUS.md`는 n8n Community 컨테이너·gateway와 WP25/BLOGGER33 마스터 가져오기를 검증 완료로 기록한다. 사용자는 "n8n 몇 개를 실제로 썼고, 몇 개 발행됐는지"를 반복 질문했다. 가져오기 성공 수와 **실제 게시 수**를 각각 보고해야 한다.
- Windows PC의 PowerShell, Desktop Commander, `londonPM` 한 번 실행, Aside/Chrome 설치 및 로그인 세션을 Naver 3·Tistory 5의 안정적 브라우저 작업에 활용해 달라는 09-25~26 지시가 있었다. 기존 설치 실패와 연결 실패가 보고되었다. `CONNECTIONS.md`는 로컬 bridge가 마지막 확인 시 offline이었고 Naver/Tistory 실발행 URL 영수증이 필요하다고 적는다.
- `CONNECTIONS.md`에는 WP·Blogspot·Instagram·Facebook 공개 URL 각 1건과 YouTube 비공개 Studio URL 1건이 기재되어 있다. TikTok·Threads는 쓰기 권한/영수증 미검증으로 기록. Metricool은 생산 경로에서 제외, 신규 결제·이중 예약 금지.
- 새 유료 API/SaaS 무단 활성화 금지, 비용 0원 기준, 무한 재시도 금지, 실패 사이트 분리, provider 403/429/quota/billing에서 추가 호출 중단. GitHub Actions의 불필요한 10/15/30/60분·일일 실행과 Render 알림·외부 메일 삭제 요구는 실제 현황을 살핀 뒤 안전하게 반영한다.

## 6. YouTube 23채널, 계정 선택, 충돌

- 09-25 사용자 구조: Survival 언어는 한 채널에 10개 언어를 섞지 않고 **1언어=1채널**. 건강은 Health Clinic USA(영어권)와 Health_Clinic_Japan(일본어권). `Seoul_Jisoo1`은 건강이 아니라 건강기능식품·호텔예약·여행/생활 상품 등 쇼핑·예약형으로 전환.
- 09-07~18 구상: 플레이리스트 5, 지식 5, 언어 10, 건강 2, 쇼핑 1. 플레이리스트는 약 60~80분, 썸네일은 인기 채널의 분위기·배치 참고 후 원본 사진·폰트/글씨 조정, 저작권 검수, 우선 비공개 업로드. 영상 제작은 VPS에서 순차 큐로, 승인 전 공개 금지. Lyria/Gemini 직접 연결 요청과 비용 상한 설정 필요.
- 09-26 사용자가 계정 선택 화면에서 제공한 15개 키→보이는 계정명 매핑은 아래와 같다. **선택 화면 이름은 실제 채널 ID가 아니다.** 괄호 속 순서와 `Studio_K3`/`K-pop Studio` 구별을 유지한다.

| 키 | 계정 선택 화면의 사용자 지정 항목 |
|---|---|
| globalmusic | Studio_K3 (2번째) |
| healing | K-ISSUE |
| starbucks | Chinese Survival |
| mbb | Mozart-Bach-Beethoven |
| kpop | Studio_K3 (1번째) |
| nasa | K-RELAX |
| history | Spanish Survival |
| science | K-health 365 |
| classical | 비영리한국유학협회KSA |
| myth | Arabic Survival |
| invention | K-pop Studio |
| american_archive | AMERICAN_ARCHIVE_TIMES |
| silent_era | SILENT_ERA_TIMES |
| retro_reels | RETRO_REELS_TIMES |
| classic_reads | CLASSIC_READS_TIMES |

- `config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json`에는 23개 목표 채널의 title/handle/UC ID와 selector 별칭이 정리되어 있다. 이 파일은 15개 선택 대상 중 `science`, `classical`, `myth`, `american_archive`, `classic_reads`를 현재 23개에서 제외된 과거 키로 기록한다. **사용자가 직접 제시한 15개 선택 목록과 충돌**하므로 자동으로 해당 다섯 키를 제거하거나 OAuth 연결·게시 대상으로 채택하지 않는다. 정확한 UC ID와 현재 채널 소유권을 확인해 실제 목표를 갱신해야 한다.
- 09-27 오전, 사용자는 Claude의 주장(한국어 Survival 핸들 표기 차이, 4개 브랜드 핸들이 프랑스 Survival UC ID와 겹친다는 주장)을 직접 확인해 달라고 했다. 해당 주장은 여기서 독립 검증된 사실로 적지 않는다. 서로 다른 핸들이 같은 UC ID를 가리키면 발행/OAuth 연결을 보류하고 각 채널 관리자 화면의 UC ID로 확인한다.
- 사용자는 `huh0303@gmail.com`으로 로그인한 예전 **개인 YouTube 채널**이 Studio 계정 선택 화면에서 보이지 않는다며 찾아 달라고 09-26~27 요청했다. 채널 위치·소유 여부는 이 문서의 자료로 확정되지 않는다. 이메일 주소만으로 공개 채널을 특정했다고 주장하지 않는다.
- 09-26 사용자는 GitHub Actions secret 두 개(`YOUTUBE_OAUTH_REFRESH_TOKEN_AMERICAN_ARCHIVE_TIMES`, `YOUTUBE_OAUTH_REFRESH_TOKEN_CLASSICAL_JOURNAL`)를 바로 제거해 달라고 요청했다. 이 기록은 **삭제 지시**이며 삭제 완료 증거가 아니다. 다른 secret은 추측해서 삭제하지 않는다.

## 7. SNS와 기타 범위

- Instagram 4계정, 동일 주제의 Threads 3~4계정, TikTok 4채널 등은 09-08 계획 기록. 계정 핸들은 `..._365` 형식으로 맞추고, 쇼핑/판매 관련 짧고 흥미로운 글, 대상별 팔로워·기존 게시 수 확인 후 운영하라고 요청했다. Threads는 Instagram의 주제·운영 방향을 그대로 따르게 한다. 시험 글은 계정별 실제 URL로 확인해야 한다.
- SNS 24개 권한 연결 0/24라는 09-24 이전 응답은 당시 관찰 또는 추정으로만 취급한다. `CONNECTIONS.md`에는 Instagram/Facebook 각 한 건의 게시 영수증이 있으므로 "전체 0건"으로 다시 단정하지 않는다.
- HHT 사업권 양수도계약(09-22)은 교육·대학 관련 별도 사업 문서다. 런던프로젝트GPT 발행/자동화 실행 범위에 넣지 않는다. 프로젝트 대화에 함께 나타났다는 이유만으로 운영 요구에 섞지 않는다.

## 8. 날짜별 최근 지시 색인

| 날짜(KST) | 사용자 지시·문제 제기 | 현재 기록 상태 |
|---|---|---|
| 09-02 | WP 네 숫자·GSC 색인, Blogspot 연결, GPT-5 Mini와 이미지 fallback | 요구사항; 전수 숫자는 별도 증거 필요 |
| 09-03~04 | 바이럴 즉시 발행 단일 버튼, 통제실 수정 현황 | UI·실발행 별도 검증 |
| 09-07~09 | VPS 영상 제작·Render 삭제, Lyria/Gemini, YouTube 비공개·SNS 주제/핸들 | 설계/지시 |
| 09-17~19 | WP 콘솔 사양, VPS 상태, AdSense 정제, LOCKED 보호, WP 미발행 사이트 발행 | 일부 상태 기록; 전수 게시 영수증 없음 |
| 09-22 | WP 빈 카테고리 삭제 | 요청; 완료 여부 검증 필요 |
| 09-24~25 | 카드별 운영·방문자 증가, 반복 UI 오류 수정, 23채널 분리·계정 ID 확인 | 요구사항; 숫자/ID 충돌 재검증 |
| 09-25~26 | PC PowerShell/Aside·Naver/Tistory, n8n 실제 발행 수, 공식 프로젝트명·GitHub 박제 | n8n import/health 기록; 로컬 브라우저 발행 미검증 |
| 09-26~27 | YouTube 15개 계정 선택 목록, 개인 채널 찾기, 겹친 핸들 검증, secret 2개 삭제, Render 제거 | 지시; 소유권/삭제/현재 UI 실측 필요 |
| 09-27 | 최근 런던 프로젝트 대화를 이 프로젝트 파일 폴더에 모두 모으기 | 이 통합 기록 작성 |

## 9. 다음 세션에서 바로 확인할 것

1. `STATUS.md`의 미완료 항목과 게시 영수증을 대조해 WP25·Blogspot33 실제 성공 수를 각각 산출한다.
2. n8n에 가져온 workflow 수, 활성화 수, 실행 성공 수, 실제 게시 URL 수를 분리해 보고한다.
3. Naver 3·Tistory 5는 로컬 bridge와 Aside 세션을 확인한 뒤 계정별 시험 게시 URL을 확보한다.
4. YouTube는 15개 selector 목록과 23채널 UC ID 마스터의 충돌을 정리하고, 개인 채널 및 브랜드 핸들 겹침을 채널 관리자 화면으로 검증한다. OAuth 대상이 확정될 때까지 잘못된 채널에 업로드하지 않는다.
5. secret 두 개의 현재 존재 여부를 확인하고, 삭제 요청이 미처리라면 두 이름만 삭제한 후 이름/시각/결과를 기록한다.
6. GitHub 정본과 VPS/runtime 상태가 다르면 runtime 영수증을 우선하며 `STATUS.md`를 수정한다.

관련 정본: [프로젝트 README](README.md) · [상태](STATUS.md) · [연결 영수증](CONNECTIONS.md) · [인계](HANDOFF.md) · [YouTube 23채널 마스터](../../config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json)
