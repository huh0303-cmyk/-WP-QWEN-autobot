# GSC 등록 확인 (2026-10-05, 읽기 전용, 서비스계정 시점)
- WP 27/27 등록 (sc-domain). k-health365.com=siteOwner, 나머지 26=siteFullUser.
- Blogspot 33 중 서비스계정에서 보이는 것 3개: k-trip365.blogspot.com(siteUnverifiedUser = 미확인 상태), skin.k-health365.com·glow.k-health365.com(siteOwner, 커스텀 도메인).
- 나머지 30개 blogspot.com 블로그는 서비스계정에서 안 보임 = 미등록이거나 허정윤 개인 계정에만 등록. 서비스계정 시점이라 "미등록 확정"은 아님.
- 증거: Actions workflow gsc-registration-check, artifact gsc_registration.json. 
- 다음: 사용자가 GSC UI(search.google.com/search-console)에서 속성 목록 확인 후, 없으면 URL접두어 속성 추가(Blogger는 같은 구글계정이면 자동 인증 가능) + 서비스계정 huh... 사용자로 추가.
