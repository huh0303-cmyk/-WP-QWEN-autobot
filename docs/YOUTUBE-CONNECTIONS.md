# YouTube 연결 운영 기록

최종 확인: 2026-09-23. 사용자 지시: 연결을 보존하고 매번 재연결을 요구하지 않는다.

## 다음 작업 시작 순서
1. 이 문서 및 VPS `/opt/korea365/data/YOUTUBE-CONNECTION-PROGRESS-20260923.md`를 먼저 읽는다.
2. 기존 저장 연결로 읽기 전용 조회를 먼저 시도한다. 브라우저 탭이 닫힌 것은 인증 해제가 아니다.
3. 만료된 접근 토큰은 기존 갱신 토큰으로 갱신한다. 사용자 동의를 자동 반복하지 않는다.
4. 권한 철회, invalid_grant, 새 권한 필요 등 실제 근거가 있을 때만 정확한 채널과 이유를 알린다.
5. 채널명과 Google 브랜드명이 다르므로 실제 channel_id를 검증한다. 이름만 보고 기존 매핑을 덮어쓰지 않는다.

## 직접 연결: 확인 완료
- 로맨틱: `UCbJfEtsffpgI5MsKkB7BYvQ`, Analytics HTTP 200, 2026-08 조회수 67.
- 힐링: `UC7yEsLM-HoXudngrD-4FIqg`, Analytics HTTP 200, 2026-08 조회수 85.
- YouTube Analytics API 활성화 확인. 전날 값이 아직 응답에 없으면 0으로 만들지 않는다.
- VPS `korea365-channel-metrics.timer` 활성, service Result=success 확인.
- 인증 보관: VPS `/etc/korea365/youtube-runtime.json` (비밀 값은 저장소에 금지).
- 수집 결과: `/opt/korea365/data/account-audience-metrics.json`.
- 그 외 기존 8개 직접 연결은 조회 권한 오류 상태이며 이 문서로 완료 처리하지 않는다.

## Windsor.ai: 연결 및 선택 저장 확인
Google 브랜드 선택 이름 기준 4개:
- Mozart-Bach-Beethoven
- K-pop Studio
- RETRO_REELS_TIMES
- SILENT_ERA_TIMES

Windsor 미리보기 실제 응답으로 확인된 채널:
- RETRO_USA1: `UCwh49EokdWFJqYFE_zA6XDQ`, 2026-08-26 영상별 조회수 3, 3, 1.
- INVENTION_STORY1: `UCgNj-yS93A_fOHXXvG49fww`, 2026-08-26 영상별 조회수 1, 2, 27, 1.

주의: 위 브랜드 4개와 실제 채널 간 개별 대응은 아직 확정하지 않았다. 브랜드 이름으로 클래식/K팝 신원이 검증됐다고 보고하지 않는다. 나머지 계정 연결, 최근 일별 통계, VPS 자동 수집 연결은 진행 중이다. Windsor 연결이 기존 VPS 인증 토큰을 갱신한 것은 아니다.

Windsor 인증은 해당 서비스가 보관한다. OAuth code, access/refresh token, API key, client secret, 전체 인증 URL을 GitHub에 올리지 않는다.
계정 화면은 2026-10-23까지 체험판, 10 sources / 15 accounts로 표시됨. 영구 무료라고 약속하지 않고 별도 승인 없이 결제하지 않는다.

## 발행 승인과 분리
조회 연결은 업로드 또는 공개 승인이 아니다. YouTube/SNS 공개는 콘텐츠별 사용자 최종 승인 후 실행한다.
