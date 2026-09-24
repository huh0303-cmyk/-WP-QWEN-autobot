# 런던프로젝트 — Simple / Light / Fast / Cheap Architecture

Status: CANONICAL — REVISED 2026-09-18
Owner / final decision maker: Chairman
Primary PM: OpenAI / GPT-5.6 Sol
Canonical repository: huh0303-cmyk/-WP-QWEN-autobot

## 1. Mission

런던프로젝트의 운영 원칙은 네 가지다.

**SIMPLER. LIGHTER. FASTER. CHEAPER.**

복잡한 중앙 Orchestrator가 모든 플랫폼을 실행하지 않는다.
각 플랫폼은 독립적으로 작동하고, 한 사이트·채널의 실패가 다른 사이트·채널을 멈추게 해서는 안 된다.
Control Korea365는 실행 엔진이 아니라 결과를 읽는 얇은 관제 화면이다.

## 2. Runtime architecture

### A. WordPress Factory — GitHub
- 일반 WordPress 25개.
- 공통 Publisher 코드 1개 + 사이트별 독립 profile/queue/state.
- 사이트 하나의 인증·API·콘텐츠 오류는 그 사이트만 실패 처리하고 다음 사이트는 계속한다.
- 기본 흐름: Site -> Category -> Golden Keyword -> GPT content -> duplicate check -> WordPress -> Post ID + actual URL.
- Post ID와 실제 URL이 없으면 성공으로 기록하지 않는다.
- WordPress는 News, Blogger, YouTube와 실행 의존성을 갖지 않는다.

### B. News Factory — GitHub
- The Seoul Journal / Koreanews365, 총 2개.
- 일반 WordPress 25개와 완전히 분리한다.
- RSS/검증 가능한 소스 -> duplicate check -> category -> keyword -> article -> source check -> publish -> actual URL.
- 두 신문도 서로 독립한다.
- 필요 이상으로 자주 polling하지 않는다. RSS 확인은 저빈도 또는 event-driven으로 한다.
- 확인할 뉴스가 없으면 API를 호출하지 않고 종료한다.

### C. Blogger Factory — GitHub
- Blogspot 33개.
- 공통 Blogger Publisher 1개 + 33개 독립 profile/queue/state.
- WordPress 발행 여부와 연결하지 않는다.
- Site -> Category -> Golden Keyword -> independent article -> duplicate check -> Blogger draft/post -> Post ID/URL.
- 한 Blogspot 실패가 나머지 32개를 막지 않는다.

### D. YouTube Factory — VPS
YouTube는 웹 발행과 완전히 분리된 별도 영상공장이다.

Playlist 5와 Knowledge 5를 별도 pipeline으로 유지한다.
- Playlist 5: topic -> music/assets -> thumbnail -> FFmpeg -> PRIVATE upload.
- Knowledge 5: topic -> sources -> script -> TTS -> footage -> subtitles -> thumbnail -> FFmpeg -> PRIVATE upload.
- 모든 작업은 순차 queue 방식이며 동시 대량 렌더를 금지한다.
- 신규 영상은 PRIVATE가 기본이다.
- video_id + exact channel_id + privacyStatus=private 확인 전 성공으로 기록하지 않는다.
- Chairman 승인 전 public 전환 금지.
- GitHub에서 영상 렌더링 workflow를 운영하지 않는다.

## 3. Category and Golden Keyword are the content core

WordPress 25, News 2, Blogger 33의 핵심 데이터는 복잡한 orchestration이 아니라 다음 두 가지다.

1. CATEGORY MASTER
2. GOLDEN KEYWORD BANK

각 destination은 category 목록과 category별 golden keyword pool을 가진다.
Golden keyword record의 최소 필드는 keyword, category, search intent, priority, last_used_at, status다.
콘텐츠 생성은 이 bank에서 선택한 키워드로 시작한다.

목표 UX:
**destination 선택 -> category -> golden keyword -> one click create -> actual result URL**

## 4. Failure isolation — mandatory

- destination별 queue/state/log 분리.
- 한 작업 실패 후 다른 destination은 계속 진행.
- 자동 retry는 최대 1회. 같은 실패를 반복 호출하지 않는다.
- 403/429/billing/quota 같은 provider 공통 장애는 해당 provider만 circuit-break하고 다른 플랫폼은 계속한다.
- API 장애가 확인되면 다음 채널/사이트에 동일 유료 호출을 반복하지 않는다.
- 전체 시스템을 한 상태로 묶어 FAILED 처리하지 않는다.

## 5. Cost policy

- 불필요한 5/10/15/20/30분 polling 금지.
- 새 paid API/SaaS는 Chairman 승인 없이는 활성화하지 않는다.
- paid provider 호출 전 health/preflight를 먼저 수행한다.
- provider 403/429/quota/billing 오류 시 fail-fast.
- retry loop로 비용을 발생시키지 않는다.
- YouTube는 API health, OAuth, FFmpeg, TTS, disk/source readiness를 확인한 뒤 제작한다.
- 썸네일 API 실패만으로 완성 가능한 영상 전체를 폐기하지 않도록 안전한 fallback/review 경로를 둔다.

## 6. Control Korea365 — read-only observability

Control Korea365는 Publisher가 아니다.
콘텐츠 생성, API 호출, queue orchestration, email report를 직접 수행하지 않는다.

표시할 최소 정보:
- platform
- destination/channel
- today success count
- last successful timestamp
- last actual URL/review URL
- current state
- concise failure reason

권장 요약:
- WORDPRESS 25: normal / failed / today published
- NEWS 2: last article per newsroom / failures
- BLOGGER 33: normal / failed / today created
- YOUTUBE 10: queued / rendering / review-required / failed

## 7. Scheduling

자동화는 필요한 순간에만 실행한다.
정각/기계적 패턴은 피하되, 이를 위해 고빈도 polling을 만들지 않는다.
사이트/채널별 schedule은 독립적이다.

현재 기본 방향:
- WordPress: 활성 사이트별 하루 1건, 랜덤 KST 슬롯.
- News: 각 신문 하루 1건. RSS·1차 출처가 검증되지 않으면 숫자를 채우기 위해 만들지 않는다.
- Blogger: 활성 사이트별 하루 1건 공개, 랜덤 KST 슬롯.
- Tistory·Naver·TikTok·Instagram·Threads·Facebook: 게시 권한이 검증된 계정별 하루 1건.
- YouTube Playlist 5: 채널별 주 2~3회, 매주 랜덤 요일, 비공개 업로드.
- YouTube Knowledge 5: 채널별 주 2~3회, 매주 랜덤 요일, 비공개 업로드.
- 위 확정 10개 외 YouTube 채널은 별도 승인 전 자동 제작 스케줄에 포함하지 않는다.

## 8. PM and provider roles

- Chairman: 최종 사업 결정/공개 승인.
- GPT-5.6 Sol: 단독 Primary PM. 구조·코드·비용·품질·상태를 관리한다.
- Claude는 기본 운영 경로에서 제외한다. 별도 명시가 있을 때만 독립 검수에 사용한다.
- 콘텐츠 provider는 교체 가능한 부품이어야 하며 특정 provider 장애가 전체 runtime을 정지시키면 안 된다.
- VPS는 YouTube 장시간 영상 작업 전용 실행면으로 우선 사용한다.
- GitHub는 WordPress/News/Blogger의 가벼운 실행과 source control에 사용한다.

## 9. Completion truth

다음은 완료 증거가 아니다:
- AI가 완료라고 말함
- workflow success
- 파일 생성
- queue 등록

Web 성공:
- exact destination + Post ID + actual URL 검증.

YouTube PRIVATE 성공:
- valid video_id + exact channel_id + privacyStatus=private 검증.

## 10. Current migration order

1. GitHub 불필요 scheduler/workflow 제거 및 자동실행 최소화.
2. WordPress 25를 독립 Factory로 정상화하고 25/25 실제 URL 확인.
3. News 2를 독립 Factory로 정상화하고 2/2 실제 URL 확인.
4. Blogger 33을 독립 Factory로 정상화하고 33/33 실제 ID/URL 확인.
5. YouTube는 VPS에서 Playlist 5 / Knowledge 5를 각각 독립 정상화.
6. 마지막에 Control Korea365를 read-only 관제로 단순화.

## 11. Prohibited architecture

- Control Korea365가 모든 플랫폼을 직접 실행하는 구조.
- WP 성공 여부에 Blogger가 의존하는 구조.
- 일반 WP와 News를 같은 publisher/scheduler에 결합하는 구조.
- GitHub에서 YouTube 장시간 렌더링을 수행하는 구조.
- 고빈도 polling으로 상태를 확인하는 구조.
- 실패한 유료 API를 여러 사이트/채널에서 반복 호출하는 구조.
- 하나의 destination 오류가 전체 batch를 중단하는 구조.

## 12. Change log

- 2026-09-18: 런던프로젝트를 SIMPLER / LIGHTER / FASTER / CHEAPER 원칙으로 전면 개정.
- 2026-09-18: WP25 / News2 / Blogger33를 GitHub 독립 Factory로, YouTube10을 VPS 독립 Factory로 재정의.
- 2026-09-18: Control Korea365를 실행 엔진에서 read-only 관제 역할로 축소.
- 2026-09-18: Claude를 기본 운영 경로에서 제외하고 GPT-5.6 Sol 단독 PM 체제로 단순화.
- 2026-09-18: destination-level failure isolation, max-one retry, provider circuit breaker를 필수 정책으로 추가.
