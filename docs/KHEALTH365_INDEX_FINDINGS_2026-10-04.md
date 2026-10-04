# k-health365.com 사이트맵 정리 (2026-10-04, Chairman 승인)
- Rank Math noindex 메타는 REST로 반영 불가(REST 400, updateMeta 200이나 미반영) → Code Snippets 필터 방식으로 전환.
- 스니펫 id=39 "LP: exclude redirected posts from Rank Math sitemap"(rank_math/sitemap/entry, 40개 ID 제외, 캐시 1회 무효화). 글·리다이렉트·상태 불변. 롤백 = 스니펫 비활성화.
- 검증(Actions run, 공개 sitemap_index 직접 조회): post 사이트맵 324 → 284, 40개 대상 URL 잔존 0.
- 미완: Site Kit ↔ Google 재연결(Google 로그인 사용자 클릭 필요). GSC 사이트맵 재제출은 site-health-guardian(2일 주기)이 처리.
- 근본 원인(색인 947 미색인: 품질/신뢰 217+192, noindex 제외 471, 404 57)은 별도 — 미해결.

## Site Kit 재연결 확인 (2026-10-04 21:44 KST, Chairman 스크린샷)
- Site Kit↔Google 연결 복구됨(Key metrics/Traffic/Search Console 패널 정상 표시). 증거=사용자 제공 스크린샷(제3자 검증 아님).
- 최근 28일: 방문자 60 / 방문 63 · 유입 Direct 75.4%, Organic Search 21.3%(검색 고유방문 13) · 방문 길이 55초.
- Search Console 패널: 노출 0 · 클릭 0(이전 기간 대비 −100%) · "Top performing keywords: Search에 아직 나타나지 않음".
- 광고 수익(Top earning pages): 3개 페이지 US$0.05 / 0.02 / 0.01 (28일).
- 해석: 구글 검색 노출이 28일간 0 → 색인 문제가 수익 정체의 핵심. Direct 비중이 커 실사용자 여부 불명(자동화·내부 접속 포함 가능).
- Analytics 그래프는 9/18경부터 데이터 시작 → 그 이전 방문자 통계는 없음.
