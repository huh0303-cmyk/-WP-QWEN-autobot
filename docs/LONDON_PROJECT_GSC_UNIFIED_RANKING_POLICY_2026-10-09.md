# 런던프로젝트GPT — 통합 블로그 통계 기준 고정 정책

- 적용일: 2026-10-09 KST
- 적용 대상: WordPress 25 + Blogspot 33
- 통합 기준: **Google Search Console (GSC) Search Analytics**
- 1차 순위 지표: **GSC clicks (클릭수)**
- 2차 지표: GSC impressions, CTR, average position
- 비교 기준: **모든 대상 사이트에 동일한 기준일(KST 오늘 - 3일)**을 지정해 조회
- 증감: 같은 사이트의 바로 전 달력 날짜 클릭수 대비 (데이터가 없으면 증감은 null)
- 기준일에 행이 없으면 `NO_DATA` 및 null로 표시하며, 사이트별 최신 날짜를 섞지 않는다
- ACCESS_UNAVAILABLE, 인증 오류, 권한 없음은 **0으로 추정하지 않는다**
- WordPress 방문자 위젯, `/wp-json/site-stats/v1/visitors`, Blogger Stats 위젯, GA4 방문자수, 기타 플랫폼 방문자 카운터는 **통합 블로그 순위에서 사용하지 않는다**
- 통합 근거 파일: `data/gsc_unified_ranking.json`
- 대상 58개와 실제 API에서 조회 가능한 GSC 속성 대조표: `data/gsc_target_property_audit.json`
- 실제 권한 기준: 서비스 계정으로 호출한 live `sites.list` 결과만 인정하며 `data/gsc_properties.json`의 저장 기록만으로 권한을 인정하지 않는다
- 수집기는 누락된 URL-prefix 속성에 `sites.add`를 시도한다. 소유권/검증 권한이 없으면 실패 상태로 남기며 정상 등록으로 간주하지 않는다
- 수집 코드: `scripts/gsc_unified_ranking.py`
- 정기 워크플로: `.github/workflows/gsc-unified-ranking.yml`
- Control Center 순위 코드: `control_center/blog_korea365_ranking.py`

## 운영 원칙

앞으로 “WP25 + Blogspot33 블로그 순위”, “어제 숫자”, “증감”, “내림차순”을 요청받으면 이 정책을 기본값으로 사용한다. 별도의 명시적 변경 지시가 없는 한 다른 방문자 통계로 기준을 바꾸거나 다시 기준을 질문하지 않는다.

GSC 공식 Search Analytics API는 클릭수, 노출수, CTR, 평균 게재순위를 반환하며 `dataState=final`은 완료된 데이터만 반환한다. 날짜 기준 조회에서는 데이터가 있는 날짜가 반환되고 날짜순으로 정렬된다.