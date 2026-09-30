# 런던프로젝트GPT — 블로그 자동화 콘솔 최종 범위

작성일: 2026-09-27 KST
상태: OWNER LOCKED

## 1. 프로젝트 명칭
- 공식 명칭: 런던프로젝트GPT
- 이전 표현인 "런던프로젝트클로드"는 이 콘솔의 공식 명칭으로 사용하지 않는다.

## 2. 콘솔 범위
기존 Naver + Tistory 콘솔 개념을 확장하여 하나의 콘솔에서 관리한다.
- WordPress 일반 사이트: 24개
- Blogspot: 33개
- Naver Blog
- Tistory
- 신문사 2개는 일반 블로그 자동화 정책과 분리 유지

## 3. 제공 형태
- PC 전용 EXE 여러 개로 나누지 않는다.
- 브라우저 웹앱 하나로 통일한다.
- PC와 모바일에서 동일한 콘솔을 사용한다.
- 기존 Hostinger VPS에 배포한다.
- n8n Community Edition을 오케스트레이션 엔진으로 사용한다.
- GitHub를 소스/버전/감사 기록의 기준으로 유지한다.
- WordPress/Blogspot의 일반 자동화는 PC가 꺼져 있어도 VPS에서 동작해야 한다.
- Naver/Tistory 로그인·CAPTCHA는 사람 확인이 필요한 예외 경로로 둔다.

## 4. 베트남 직원 권한
- 별도 축소판 앱은 만들지 않는다.
- 동일 웹앱을 사용한다.
- 현재 단계에서는 동일 운영 권한으로 충분하다.

## 5. 메인 UI — 4 Agent 고정
### AGENT 1 — 주제·키워드 리서치
- Google 검색/뉴스/트렌드 신호
- Naver 검색/뉴스/데이터랩 신호
- GSC 실제 쿼리·노출 데이터
- 최신 미디어 노출
- 기존 글/사이트 간 중복 방지
- 실제 검색량과 GSC 노출·미디어 언급·Trends 지수를 구분
- 확인되지 않은 절대 검색량을 만들어내지 않는다.

### AGENT 2 — 글쓰기
- 사이트별 페르소나
- 톤앤매너
- 언어
- 글자 수
- 카테고리
- SEO/품질 게이트
- 출처/근거 처리
- WordPress와 Blogspot은 같은 주제를 쓰더라도 문장을 독립 작성한다.

### AGENT 3 — 이미지
- 사이트 정책에 따라 0~1장
- ALT 텍스트
- 대표 이미지 처리
- 임시 URL은 영구 호스팅 확인 후 사용
- 이미지 실패 시 해당 사이트 정책이 허용하면 무이미지 진행

### AGENT 4 — 발행·검증
- WordPress REST / Blogger API / Naver / Tistory 발행
- 선택 카테고리 적용
- post ID / 공개 URL / draft URL 기록
- 공개 발행은 실제 URL 검증 후 성공 처리
- 영수증이 없으면 성공으로 표시하지 않는다.

## 6. 장애 진단 원칙
메인 화면에서 4개 Agent를 각각 독립 박스로 표시한다.
각 박스는 다음 상태 중 하나를 보여준다.
- 대기
- 실행중
- 성공
- 실패

실패 시 반드시 표시:
- site_id
- run_id
- 실패 Agent
- 오류 종류
- 오류 메시지
- 마지막 성공 단계
- 재실행 버튼

한 Agent 실패가 다른 사이트 작업까지 중단시키지 않도록 사이트별 격리한다.

## 7. 운영 원칙
- 사용자는 사이트를 선택하고 카테고리를 선택한 뒤 실행 버튼을 누르는 방식으로 사용한다.
- 사이트별 페르소나·톤앤매너·언어·기본 카테고리는 미리 내장한다.
- 복잡한 설정값을 직원이 직접 입력하지 않게 한다.
- 수동 입력은 최소화하고 클릭 중심으로 운영한다.
- 동일 결정을 다음 세션에서 다시 설계하지 않는다. 이 문서를 단일 기준으로 사용한다.

## 8. 2026-09-28 실행 모드 확장
- 사용자 결정: 런던프로젝트GPT 화면에 자동/수동 모드를 둔다. 자동은 기존처럼 Agent 1 키워드 → 2 글쓰기 → 3 이미지 → 4 발행·검증까지 연속 진행한다. 수동은 Agent 1~3의 결과만 자동 준비하고 Agent 4의 공개 발행은 사람이 WordPress에서 수행한다.
- 네 Agent 각각의 카드에 실제 결과를 표시한다. 1번 키워드/근거, 2번 제목/설명/카테고리/본문 HTML, 3번 이미지/URL, 4번 발행 영수증 또는 수동 발행 자료/공개 URL 검증을 둔다. 제목·본문·설명·카테고리·이미지 URL 및 전체 발행 자료를 복사할 수 있다.
- 수동 실행의 `publish_mode=manual`은 Agent 3 완료 후 발행 호출 대신 `manual_required`로 기록한다. 발행 영수증은 만들지 않으며, 수동 실행의 Agent 4 자동 재실행은 거부한다.
- 사람이 공개한 WordPress URL은 선택 사이트와 동일한 HTTPS 호스트인지, 공개 페이지가 HTML 200인지, 작성 글 제목이 본문에 나타나는지 확인한 후 수동 발행 검증 영수증을 기록한다. URL이 없거나 확인 실패 시 성공으로 표시하지 않는다.
- 자동 모드의 기존 초안/즉시 공개 선택은 유지한다. 이미지가 없으면 본문만 복사한다.

## 9. 2026-09-28 플랫폼 선택 확장
- 웹앱의 사이트 선택을 WordPress 27개, Blogspot 33개, Naver 3개, Tistory 5개로 확장한다. 목록은 확인된 저장소 레지스트리에서 읽고, 플랫폼별 목적지와 편집 톤을 보여준다.
- Blogspot 33개는 기존 Blogger API 경로에서 자동/수동 모드를 지원한다. 각 실행의 안정적인 job marker와 발행 영수증을 유지한다. 기존 33개 일일 예약 시스템은 이 화면과 별개이며 이 변경으로 예약을 재실행하지 않는다.
- Naver/Tistory는 로컬 로그인·CAPTCHA 확인 경로이므로 이 웹앱에서 자동 발행을 허용하지 않는다. Agent 1~3의 결과를 준비하고, 사람이 직접 발행한 뒤 공개 URL을 검증한다.
- Naver 로그인 계정과 실제 발행 블로그 ID를 구분한다. 2026-09-29 로그인된 Chrome의 글쓰기 화면으로 확인한 매핑은 N1 계정 `huh0303` → 블로그 `k-insight-vietnam`(부의정석), N2 계정 `huh3` → 블로그 `health-standard`(헬스의정석), N3 계정 `huh4` → 블로그 `sky-only`(생활의정석)이다. 브라우저 로그인은 무인 발행 자격정보가 아니므로 N2/N3의 백그라운드 enabled는 false와 수동 발행 원칙을 유지한다.
- 템플릿 파일을 `file://`에서 직접 열면 Jinja 표시가 그대로 보이는 문제를 줄이기 위해 공식 웹앱 주소로 이동시킨다. 공식 사용 주소는 `https://control.korea365.org/london-gpt`이다.

## 10. 2026-09-28 무료 모델 우선 글쓰기·수동 발행 동선
- 사용자 결정: 자동 실행의 글쓰기 기본값은 무료 우선이다. 순서는 Gemini 3.5 Flash → Gemini 3.1 Flash-Lite → Gemini 2.5 Flash → Gemini 2.5 Flash-Lite → Gemini 3.5 Flash-Lite → 로컬 Qwen 2.5 3B다. 429·타임아웃·불완전 응답은 다음 모델로 넘어간다. 품질 검사 실패 시 다른 모델로 원고를 한 번 더 시도한다. GPT-5 mini API는 유료라고 표시하며 사용자가 직접 선택할 때만 시도하고, 잔액 부족 시 무료 체인으로 이동한다. 무료 등급은 사용 한도가 있으므로 성공이나 무과금을 보장한다고 쓰지 않는다. 실제 청구 여부는 연결된 Gemini 프로젝트의 청구 등급에 따른다.
- 글쓰기 지침: 사이트별 목표 본문 길이를 지키되 이는 Google AdSense의 공식 최소 길이가 아니다. 독자 질문에 먼저 답하고, 짧은 단락·의미 있는 제목·원본 분석·검증 가능한 사실을 사용한다. 중복/짜깁기·허위 통계/출처·과도한 키워드 반복·의료/법률 확언을 금지한다. 기존 기계적 품질 점수 70점과 중요 항목 게이트를 유지하며 승인 보증을 하지 않는다.
- 이미지 기본값은 무료 스톡 Pexels → Pixabay이며, 정확한 주제 일치 및 영구 URL을 확보하지 못하면 이미지를 생략한다. 유료 Replicate SDXL/FLUX는 화면에서 유료라고 표시하고 사용자가 직접 선택할 때만 사용한다. Gemini 이미지 생성 API는 공식 가격표상 무료 Standard 등급이 없으므로 무료 옵션으로 표시하지 않는다.
- 수동 모드는 선택한 목적지의 글쓰기/글 관리 화면 링크를 제공하고 제목·본문 HTML·설명·카테고리·이미지 URL·이미지 자체 복사와 이미지 열기를 제공한다. WordPress와 Tistory는 새 글 화면, Naver는 계정별 글쓰기 진입 URL, Blogger는 해당 블로그의 글 관리 화면으로 이동한다. 로그인/서비스 UI에 따라 추가 클릭이 필요할 수 있다. 공개 글 URL 확인 전에는 발행 성공으로 표시하지 않는다.
- 2026-09-28 운영 키 실측: Gemini 2.5 Flash 및 2.5 Flash-Lite는 429, Gemini 3.1 Flash-Lite는 짧은 생성에 HTTP 200/STOP, Gemini 3.5 Flash는 HTTP 200이나 32토큰 샘플에서 MAX_TOKENS, Gemini 3.5 Flash-Lite는 20초 샘플에서 시간 초과. 이는 짧은 샘플이며 장문 품질/한도 증거가 아니다. GPT-5 mini는 별도 실측에서 429 `credit_balance_exhausted`였다. 비밀 키는 기록하지 않았다.
- 후속 운영 검증에서 모델 선택값이 `stage_research`의 초기 상태 재생성으로 사라지는 결함을 발견했다. 기존 실행의 모델·모드·카테고리 선택을 유지하도록 수정한다. 연구 에이전트가 만든 출처 없는 Google/Naver/검색량 숫자와 반복 템플릿은 표시 전에 제거한다.
- 의료·백신·건강 글의 품질 점수는 형식 검사이며 의학적 사실 확인이 아니다. 공식 출처가 검증되지 않은 의료 글은 자동 공개를 중단하고 수동 검토 상태로 전환한다. 글 제목·본문·이미지 복사는 가능하되 공개 URL 영수증이 생기기 전에는 발행 완료로 표시하지 않는다. 이 규칙은 런던프로젝트GPT 앱의 의료 주제에 적용하며 다른 정기 발행기의 정책은 별도다.

## 11. 2026-09-29 수익 극대화·무료 전용·발행 주기 최종 원칙
- 최종 목표는 게시물 수가 아니라 **검증된 최종 수익의 극대화**다. 1단계는 블로그별 Google AdSense 승인 준비와 승인 후 방문자 확대, 2단계는 YouTube·SNS 방문자/조회수/구독자 확대, 3단계는 쇼핑 채널·쿠팡파트너스 등 정책을 준수하는 제휴 전환과 실제 수익 확대다.
- 성과 판단은 실제 연결 소스만 사용한다. AdSense 보고서, GSC 클릭·노출·색인, 검증된 방문자, YouTube Analytics, 플랫폼 인사이트, 제휴 클릭·전환·커미션을 구분한다. 연결되지 않은 값은 `미연결/미확인`으로 두고 0이나 추정치로 만들지 않는다.
- 초기 생성 비용은 **무료만** 허용한다. Gemini 무료 등급과 로그인된 Claude 무료 사용 범위를 우선 활용하되, 무료 한도 소진·429·세션 만료 시 유료 API나 유료 이미지 모델로 자동 전환하지 않는다. 작업은 대기/재시도/사람 확인 상태로 남긴다. Claude 무료 웹 세션은 자동 API 연결로 간주하지 않으며 실제 자동화 연결이 확인되기 전에는 수동 보조 경로다.
- 발행 주기는 채널·사이트·계정별로 고정한다. YouTube는 모든 채널이 주 2~3회이며 요일과 시각은 허용 범위 안에서 무작위로 분산한다. WordPress·신문사·Blogspot·Naver·Tistory와 Instagram·Threads·TikTok·Facebook 등 나머지 블로그/SNS는 각 활성 목적지마다 하루 1회이며 시각을 무작위로 분산한다.
- 무작위 배치는 중복 실행을 뜻하지 않는다. 동일 목적지의 같은 날짜/주차 영수증과 예약 상태를 먼저 확인하고, 기존 예약기와 겹치면 새 예약을 만들지 않는다. 무료 할당량 부족이나 품질·출처·권한 검증 실패를 목표 수량을 채우기 위한 저품질 발행으로 우회하지 않는다.
- YouTube 제작물은 2026-09-30 소유자 변경 결정에 따라 정확한 OAuth 채널 ID와 업로드 결과를 검증한 뒤 즉시 공개한다. 채널 ID 불일치·쓰기 권한 미연결·품질 실패는 공개하지 않고 실패로 기록한다. 의료·법률·금융 등 민감 주제와 공개 발행 권한이 확인되지 않은 목적지는 자동 공개하지 않는다. AdSense 승인, 검색 순위, 방문자, 수익은 보장 표현을 금지한다.
- 운영 권한은 이 목표 안에서의 진단·준비·예약·검증으로 한정하며, 계정 로그인/OAuth·공개 발행·제휴 고지 등 기존 승인 및 영수증 규칙을 계속 따른다.
- 수동 모드는 직원용 복사 패키지를 제공한다. 글마다 제목/SEO 제목, 본문 HTML, 검색설명/메타 설명, 포커스 키워드, 키워드·태그, 카테고리, 이미지 URL과 ALT를 함께 준비하고 항목별 복사와 전체 복사를 모두 제공한다. 네이버·티스토리는 사람이 먼저 해당 계정에 로그인하고 CAPTCHA·추가 인증을 처리한 뒤 붙여넣으며, 로그인 우회나 비밀번호 저장은 하지 않는다.

## 12. 2026-10-01 Naver cadence and monthly keyword override

- The owner superseded the one-post-per-day Naver cadence: N1 부의정석 and N2 헬스의정석 each target 3–4 reviewed posts per KST day; N3 생활의정석 targets 8–10.
- This exception applies only to the three Naver rooms. It does not change WordPress, Blogspot, Tistory, YouTube, or SNS cadence.
- Daily times are randomized and persisted before the first post. Minimum same-account gaps are 180 minutes for N1/N2 and 75 minutes for N3. A missed slot is not recovered by bulk posting.
- A January–December candidate calendar feeds current Naver DataLab relative trends, Naver News freshness, existing entry queries, and official sources. Absolute volume, rank, visits, and revenue are never invented or guaranteed.
- General Naver blog articles do not use Google Indexing API. Search Console actions require verified property ownership; publication is followed by exact public-URL and Naver visibility checks.

## 13. 2026-10-01 Naver morning trend and wake override

- The three-account Naver operation prepares a same-day evidence brief from 07:07 to 07:50 KST; public publishing slots begin at 08:17.
- Every month has exactly 100 prepared candidate queries in `config/naver_monthly_keyword_100.json`. The catalog is a research queue, not verified absolute search volume or a ranking guarantee.
- Same-day evidence may promote current sports, politics/policy, film/culture, military/public-safety, support-program changes, and regional transport topics. Primary-source, non-duplication, brand-fit, and public-URL gates still apply.
- The local Windows host may wake from sleep at 06:55 through `Korea365_오전운영_깨우기`; a fully powered-off machine is outside this guarantee. The desktop app and authenticated browser sessions must remain available.
