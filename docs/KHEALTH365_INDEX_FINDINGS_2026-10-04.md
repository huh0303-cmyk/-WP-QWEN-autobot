# k-health365.com 사이트맵 정리 (2026-10-04, Chairman 승인)
- Rank Math noindex 메타는 REST로 반영 불가(REST 400, updateMeta 200이나 미반영) → Code Snippets 필터 방식으로 전환.
- 스니펫 id=39 "LP: exclude redirected posts from Rank Math sitemap"(rank_math/sitemap/entry, 40개 ID 제외, 캐시 1회 무효화). 글·리다이렉트·상태 불변. 롤백 = 스니펫 비활성화.
- 검증(Actions run, 공개 sitemap_index 직접 조회): post 사이트맵 324 → 284, 40개 대상 URL 잔존 0.
- 미완: Site Kit ↔ Google 재연결(Google 로그인 사용자 클릭 필요). GSC 사이트맵 재제출은 site-health-guardian(2일 주기)이 처리.
- 근본 원인(색인 947 미색인: 품질/신뢰 217+192, noindex 제외 471, 404 57)은 별도 — 미해결.
