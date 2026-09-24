# 런던프로젝트 콘텐츠 파이프라인 및 발행 주기

이 문서는 런던프로젝트의 콘텐츠 생산·검수·발행·실패복구 운영정책 정본이다.
모든 계획형 스케줄은 KST(Asia/Seoul) 기준이다.
모든 작업은 `config/london_activity_policy.json`과 `docs/LONDON_PROJECT_ACTIVITY_LEDGER.md`에 따라 task_id 기반으로 성공·실패·재시도·승계·증거를 기록한다.

## 1. 공통 시간 정책

- 정각 발행 금지.
- 계획된 기준 시각에서 기본 ±60분 범위 안에서 랜덤 오프셋을 적용한다.
- 분 단위는 00/05/10/15/20/25/30/35/40/45/50/55 같은 규칙적 분을 피하고 14, 16, 27처럼 비정형 분을 우선 사용한다.
- 같은 플랫폼/계정군의 게시물은 가능하면 30분 이상 간격을 둔다.
- 여러 사이트/채널이 같은 분에 몰리지 않도록 분산한다.
- 같은 요일·같은 시각 패턴을 반복하지 않는다.
- 뉴스 속보처럼 이벤트 기반 업무는 고정 시각보다 실제 이벤트와 중복검사를 우선한다.

## 2. 플랫폼별 기본 발행 주기

| 플랫폼 | 기본 주기 | 생성/발행 정책 | 검수 |
|---|---|---|---|
| 일반 WordPress | 활성 일반 사이트별 하루 1개 | 사이트별 독립 SEO 글. KST 랜덤 시간. | 발행 후 URL 감사 |
| 인터넷신문 2개 | 각 신문 하루 1건 | 일반 WP와 분리. 검증 가능한 RSS/1차 출처가 없으면 추측 기사를 만들지 않음 | 기사 URL·출처 감사 |
| Blogspot/Blogger | 활성 대상별 하루 1개 공개 | WordPress 복붙 금지. 같은 주제라도 독립 작성 | 게시 ID·URL 확인 |
| Tistory 5개 | 사이트별 하루 1개 공개 | 검색형/정책형 독립 글. 로컬 쓰기 권한 확인 계정만 실행 | URL 감사 |
| YouTube Playlist 5 | 채널별 주 2~3회, 매주 랜덤 요일 | 기존 파이프라인대로 VPS 제작 후 비공개 업로드 | 이사장 검수 후 공개 |
| YouTube Knowledge 5 | 채널별 주 2~3회, 매주 랜덤 요일 | 대본→음성→영상→썸네일→비공개 업로드 | 이사장 검수 후 공개 |
| 10-Language Survival | 자동 스케줄 제외 | 확정 YouTube 10개 외 별도 프로젝트. 별도 승인 전 자동 제작하지 않음 | 보류 |
| Instagram | 게시 권한 검증 계정별 하루 1회 | 원본 콘텐츠를 SNS용으로 재구성 | 게시 ID 확인 |
| Threads | 게시 권한 검증 계정별 하루 1회 | Instagram과 주제 방향은 같되 문구 복붙 금지 | 게시 ID 확인 |
| TikTok | 게시 권한 검증 계정별 하루 1회 | 세로형 숏폼/교육형 콘텐츠 | 게시 ID 확인 |
| Facebook | 게시 권한 검증 계정별 하루 1회 | 카드·링크·숏폼 재구성 | 게시 ID 확인 |

## 3. 이미지 정책

기본 순서:
1. Pexels 등 저작권 안전 무료 이미지
2. Pixabay 등 저작권 안전 무료 이미지
3. 적합한 무료 이미지가 없을 때 SDXL Lightning
4. 실패 시 FLUX Schnell
5. 전부 실패하면 무이미지 허용

무료 이미지도 글 주제와 실제 관련성이 있어야 한다. 뉴스 기사 사진은 원 출처가 허용한 이미지, 퍼블릭 도메인, 명시적 라이선스 또는 저작권 안전 이미지로 한정하며, 다른 언론사의 사진을 무단 복사하지 않는다.

## 4. 10개 언어 × 50강 프로젝트

대상 언어:
- Korean / TOPIK
- English
- Japanese
- Chinese
- Vietnamese
- Spanish
- French
- German
- Italian
- Portuguese

목표:
- 언어별 50강
- 총 500강
- 현재 완료 기준: Lesson 1~2
- 다음 제작: Lesson 3
- 현재 자동 스케줄에서는 제외하며, 별도 승인 후에만 재개
- 10개 언어가 같은 시각에 겹치지 않도록 서로 다른 KST 랜덤 슬롯 사용

운영 순서:
1. CODEX PM이 다음 Lesson 번호와 언어별 작업 묶음을 생성한다.
2. Orchestrator가 언어별 작업을 Gemini/Claude/VPS에 배정한다.
3. Gemini가 기본 대본·현지화·구조화·번역 보조를 수행한다.
4. Claude가 의미·발음·구성·중복·품질을 독립 QA한다.
5. VPS가 음성/영상/자막/썸네일 렌더링과 업로드를 수행한다.
6. YouTube에는 반드시 privacyStatus=private로 업로드한다.
7. Audit Engine이 video_id, channel_id, privacyStatus=private를 확인해 VERIFIED_PRIVATE만 부여한다.
8. Control Korea365에 검수 링크를 노출한다.
9. 이사장 승인 전에는 공개 전환하지 않는다.
10. 이사장 승인 후 공개 전환 작업을 수행하고 YouTube API로 public 상태를 다시 확인한 뒤에만 VERIFIED_COMPLETE로 전환한다.

## 5. YouTube Playlist / Knowledge 공통

- Playlist 5채널과 Knowledge 5채널은 각각 채널별 주 2~3편을 생산하며, 매주 2일 또는 3일을 무작위로 고른다.
- 채널 간 동일 시각 충돌을 피한다.
- 같은 채널의 연속 실행 시각이 반복되지 않도록 한다.
- 모든 신규 영상은 비공개 업로드를 기본값으로 한다.
- `video_id + exact channel_id + privacyStatus=private` 확인 후에만 VERIFIED_PRIVATE.
- 이사장 검수 후 공개 전환, 이후 public API 재검증 후 VERIFIED_COMPLETE.

## 6. Agent 역할

### CODEX — Primary PM
- 전체 주간/일간 발행량 계산
- 랜덤 스케줄 생성 및 충돌 방지
- 작업 분해와 Agent 배정
- 사이트/채널/언어별 진행률 관리
- 모든 작업에 task_id 생성 및 작업원장 기록 보장
- 감사 실패 시 재작업 지시
- 사용자 보고
- 직접 VERIFIED_COMPLETE 판정 금지

### Claude — Independent QA + Plan B Acting PM
- 대본/기사/메타데이터 품질 QA
- 10개 언어 의미·구성·중복·오류 감사
- 실제 발행 증거 검토
- CODEX/OpenAI 장애 시 현재 handoff packet을 이어 받아 Acting PM
- 전략을 새로 만들지 않고 기존 우선순위와 스케줄을 이어감
- 성공·실패·재작업 결과를 작업원장에 남김

### Gemini — Production + Plan C Continuity
- Blogspot 독립 콘텐츠 생산
- 10개 언어 Survival 대본·현지화·구조화의 기본 생산 엔진
- 대량/반복 콘텐츠 작업
- 멀티모달/이미지 프롬프트 보조
- Claude 감사 결과 2차 교차검증
- CODEX와 Claude 모두 불가할 때 승인된 작업만 Plan C로 계속 수행
- 결과와 오류를 작업원장에 남김

### VPS Workers
- 24시간 Queue/Scheduler
- 랜덤 발행시각 실행
- 영상/TTS/자막/썸네일 렌더링
- YouTube 비공개 업로드
- RSS/장기 작업
- SQLite + append-only JSONL 영속 기록

### Deterministic Audit Engine
- 웹: 실제 URL/호스트/HTTP/제목·작업 식별
- YouTube: video_id/channel_id/privacyStatus/API 조회
- VERIFIED_COMPLETE 또는 VERIFIED_PRIVATE 판정의 유일한 권한
- 감사 결과와 증거를 task_id에 연결하여 보존

## 7. Plan A / B / C / SAFE HOLD

### Plan A — CODEX 정상
CODEX PM → Orchestrator → Claude/Gemini/VPS → Audit.

### Plan B — CODEX/OpenAI 장애 또는 API 토큰·쿼터 고갈
트리거: quota/rate limit/timeout/provider outage/auth failure/PM lease expiry.
Orchestrator가 durable handoff packet을 생성하고 Claude를 Acting PM으로 승계한다.
Claude는 열린 작업, 스케줄, 최근 결정, 완료 기준, 오류와 감사 실패를 그대로 이어받는다.
전환 자체도 FAILOVER 이벤트로 작업원장에 기록한다.

### Plan C — CODEX와 Claude 모두 사용 불가
Gemini가 continuity 역할을 맡는다.
이미 승인된 생산/예약/감사 보조만 계속한다.
새 유료 서비스, 전략 변경, 사이트 추가·삭제, 되돌리기 어려운 작업은 하지 않는다.
전환과 결과를 작업원장에 기록한다.

### SAFE HOLD — 세 AI 모두 사용 불가
VPS는 상태와 Queue를 보존한다.
새 콘텐츠 생성과 신규 공개 발행은 중지한다.
이미 생성·검증·승인된 예약 작업만 정책상 안전한 범위에서 실행한다.
YouTube는 승인 없는 public 전환을 절대 하지 않는다.
복구 시 마지막 handoff packet부터 재개한다.

## 8. 랜덤 스케줄 규칙

- 기준 시각은 운영 캘린더가 제공한다.
- 실제 실행시각 = 기준 시각 + random(-60분, +60분).
- 실제 minute 값은 규칙적인 5분/10분 단위를 피한다.
- 동일 대상은 직전 발행시각과 패턴을 비교해 반복을 피한다.
- 같은 사이트/채널에 중복 task_id가 있으면 재발행 금지.
- YouTube 10채널과 10개 언어 채널은 서로 가능한 한 겹치지 않는 슬롯으로 분산한다.
- 발행량 목표는 지키되 시간은 기계적으로 보이지 않게 분산한다.

## 9. 승인과 완료 상태

- 웹 실제 공개 확인 전: READY_FOR_AUDIT
- YouTube 비공개 업로드 확인: VERIFIED_PRIVATE
- 이사장 검수 대기: REVIEW_REQUIRED
- 이사장 승인 + public API 검증: VERIFIED_COMPLETE
- 실패/증거 부족: NEEDS_ATTENTION 또는 REWORK_REQUIRED

AI의 성공 문구, GitHub Actions success, 파일 생성만으로 완료 처리하지 않는다.
