# SeoulMall 자동 삽입 모듈 — 2026-11-04

## 목적
WordPress 글 본문 맨 아래에 SeoulMall 스토어 안내 위젯을 중복 없이 삽입하기 위한 공통 렌더러와 테스트를 추가한다.

- 공개 스토어 주소(현재 확인값): https://influencers.coupang.com/s/seoulshop
- 브랜드명: SeoulMall
- 문구: Beyond BTS, Discover Korea.
- 카테고리: K-Beauty, K-Health, K-Tour, K-Hotels, K-Digitals, K-Life
- 위젯은 실제 상품 개별 카드가 아니라 공식 인플루언서 스토어로 이동하는 CTA다.
- URL 슬러그가 변경되면 SEOULMALL_STORE_URL 환경변수로 교체한다.
- 중복 방지 마커: <!-- seoulmall-store-widget:v1 -->

## 파일
- automation_hub/seoulmall_widget.py — HTML/CSS 렌더러, append_widget(), has_widget()
- tests/test_seoulmall_widget.py — 중복 삽입/하단 삽입 테스트

## 적용 정책
1. 새 WordPress 글을 발행하는 최종 payload의 content에 append_widget(content)를 적용한다.
2. 기존 글은 별도 backfill 실행으로 처리하며, 기본값은 DRY_RUN=true로 둔다.
3. 기존 글 수정 전 REST API에서 context=edit 원문을 가져와야 한다. rendered HTML만 받아 다시 저장하면 shortcode/블록 마크업이 손상될 수 있으므로 raw가 없으면 중단한다.
4. 매 글 업데이트 후 read-back 검증을 한다.
5. 글의 제목, 상태, 발행일, 대표이미지, 카테고리, 태그 등은 변경하지 않는다.
6. 기존 쿠팡 상품 카드 또는 제휴 링크는 삭제/교체하지 않는다.
7. 사이트별 운영 잠금/제외 목록을 준수한다. 이 커밋만으로 라이브 사이트에는 아무것도 삽입되지 않는다.

## 현재 상태
이 커밋은 공통 렌더러와 단위 테스트만 저장한다. WordPress 계정에 접속하거나 기존 글을 변경하지 않았으며, 새 글 발행기 연결과 기존 글 일괄 적용은 별도 통합 및 검증 단계가 필요하다.
