# PUBLISHING SAFETY POLICY — 2026-08-25

## 사용자 최종 확정

모든 신규 자동화 콘텐츠는 검증기간 동안 **비공개/초안 상태로만 등록**한다. 최종 공개 발행은 사용자가 직접 수행한다. 신뢰와 품질 검증이 충분히 쌓인 이후에만 별도 사용자 승인으로 완전자동 공개 발행으로 전환한다.

## 강제 안전 규칙

1. WordPress: 신규 글은 `draft`로만 생성한다. 자동화 코드에서 `publish` 금지.
2. YouTube: 신규 영상은 `private`로만 업로드한다. 자동화 코드에서 `public` 및 `unlisted` 금지.
3. Facebook/Instagram/Threads/TikTok 등 SNS: 플랫폼이 비공개 예약/초안 API를 지원할 때만 자동 등록한다. 비공개/초안 상태를 보장할 수 없는 플랫폼은 자동 공개하지 않고 게시 대기 큐/산출물까지만 생성한다.
4. 카드뉴스: 자동 생성 후 검수 대기 상태로 저장한다. 사용자 승인 전 공개 게시 금지.
5. TOPIK/언어 퀴즈: 자동 생성 후 각 연결 플랫폼의 비공개/초안 상태로만 등록한다.
6. 지식채널 Shorts/Long-form: YouTube private 등 검수 가능한 상태로만 등록한다.
7. 블로그 A/B 사이트는 시간차를 두고 순차 처리하며 동일 시각 일괄 발행 금지.
8. 샘플 검증 단계의 완료 기준은 실제 Draft/Private 등록 결과와 해당 콘텐츠 식별자/URL 확인이다.
9. 사용자가 별도로 완전자동 공개 전환을 승인하기 전에는 이 정책을 자동으로 완화하지 않는다.

## 예약/큐 운영 원칙

- A급 사이트 우선, B급 후속, C급은 목적별 별도 운영.
- korea365.org는 A급 최상위 Korea 종합포털로 특별 관리.
- 블로그: Golden Keyword → 검색의도 → 원고 → 이미지 → SEO/EEAT/사실검증 → Draft 등록.
- TOPIK: 검증된 낱말퀴즈 MASTER FORMAT → Shorts/Long-form 파생 → Private 등록.
- 영어 및 기타언어 Survival: MASTER DATA 기반 파생 → Private/Draft 등록.
- 지식채널: 사실검증 → 스크립트 → 영상/TTS/자막 → Private 등록.
- 카드뉴스: MASTER DATA → Canva/그래픽 생성 → 검수 대기.
- 플랫폼별 게시 시각은 정각/30분 고정 패턴을 피하고 시간차를 둔다.

## 공개 전환

현재 모드: `HUMAN_FINAL_PUBLISH = TRUE`
현재 자동 공개: `AUTO_PUBLIC_PUBLISH = FALSE`

AUTO_PUBLIC_PUBLISH 변경은 사용자 명시적 승인 후에만 허용한다.
