# 27개 사이트 종합상황실 일일 수집 기준

## 실행

- 대상: `scripts/daily_site_traffic.py`의 활성 WordPress 사이트 27개
- 주기: 하루 1회, 매일 05:20 KST
- 저장 위치: Google Sheet `27개사이트_트래픽`
- 원본 증거: `daily_site_traffic_result.json`

## 사이트 방문자

- 푸터에 보이는 `오늘 방문 / 누적`과 같은 WordPress option을 읽기 전용 REST API
  `/wp-json/site-stats/v1/visitors`에서 가져온다.
- 수집기가 홈페이지 HTML을 직접 열면 방문자 수를 스스로 증가시킬 수 있으므로
  푸터 문자를 화면 스크래핑하지 않는다. REST 값이 푸터 표시의 원본값이다.
- 일일 비교에는 수집 도중 변하는 `오늘 방문`이 아니라 전날 00:00~23:59 KST
  확정값인 `yesterday_count`를 사용한다.
- 함께 기록: 전날 방문자, 전전일 대비 증감, 누적 방문자, 오늘 실시간 값(JSON).

## Google Search Console

- Search Analytics API의 가장 최근 확정 일자를 사이트별로 자동 선택한다.
- GSC 데이터 지연을 고려해 KST 현재일 기준 3일 전까지 조회한다.
- 함께 기록: 클릭, 노출, CTR(%), 평균순위, GSC 기준일.
- Sitemaps API에서 색인 URL 수와 제출 URL 수도 함께 기록한다.
- URL-prefix 속성과 `sc-domain:` 속성을 모두 지원한다.
- GSC 권한이 없는 사이트는 추정값을 만들지 않고 빈 값과 상태로 남긴다.

## 안전 원칙

- GSC는 읽기 전용 범위만 사용한다.
- 한 지표의 실패가 나머지 27개 사이트 수집을 막지 않는다.
- 방문자와 검색 클릭은 서로 다른 지표이며 합치거나 대체하지 않는다.
- CTR과 평균순위는 Google Search Console 값이지 AdSense 승인 점수가 아니다.
