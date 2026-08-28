# Master Auto-Publish Intent — 2026-08-28 (사용자 지시 박제)

## 사용자 원문 지시

> WP 27개채널 자동발행
> 2.블팟 27개채널 자동발행
> 3.SNS - 유튜브,틱톡,인스타,쓰레드,페이스북, 자동발행
> 4.티스토리5개채널 자동발행
> 5.쇼핑채널, 쇼핑커넥트,쿠파,쇼피,아고다,트립 어필리에이트 연결
> 이걸 하게 해달라니까.

이 5가지가 이 프로젝트의 최우선 목표다. 개별 버그 수정(썸네일/영상 등)에
매몰되어 이 5가지 축이 실제로 안정적으로 돌아가는 상태를 만드는 작업이
지연되어서는 안 된다.

## 5대 축과 2026-08-28 기준 정직한 현황

| # | 축 | 현재 상태 |
|---|---|---|
| 1 | WP 27개 채널 자동발행 | 부분 가동. `scripts/autopost_mega.py` 중심 엔진 존재, Gemini 우선/GPT 에스컬레이션 정책 확정(`automation_hub/content_model_policy.py`). TheSeoulJournal/k-health365 등 개별 사이트는 최근까지 발행 로직 자체가 깨져 있었던 이력 있음 — 27개 전체가 동일하게 안정 가동 중인지 사이트별 재검증 필요. |
| 2 | Blogger 27개 채널 자동발행 | 부분 가동. Gemini를 기본 작가로 쓰기로 확정. k-health365 Blogger는 draft-only 계약(자동 발행 금지, 사람이 최종 검수)로 별도 설계됨 — 이 계약이 나머지 26개 Blogger에도 동일 적용되는지는 미확인. |
| 3 | SNS 자동발행 (YouTube/TikTok/Instagram/Threads/Facebook) | 미완성 상태가 가장 큼. YouTube는 지식/플리 채널 파이프라인 존재(단, 플리 영상 제작은 방금 전면 정지시킴). TikTok/Instagram/Threads/Facebook은 계정 구조 정리만 되어 있고(3개 브랜드 x 5개 플랫폼 로스터) 실제 자동발행 파이프라인은 대부분 미구축. |
| 4 | 티스토리 5개 채널 자동발행 | 미가동. `config/tistory_portfolio.json`상 5개 사이트 전부 `launch_enabled: false`, `lifecycle: inventory_audit` — 아직 정식 런칭 전 단계. 글쓰기 로직(Gemini 기본/GPT 에스컬레이션/Claude는 감사만)은 구현·테스트 완료. |
| 5 | 쇼핑/제휴 연결 (쿠팡파트너스/Shopee/Agoda/Trip.com) | 쿠팡파트너스만 초기 착수(배너 k-health365.com에 injection, ACCESS/SECRET 키 승인 대기 중). Shopee/Agoda/Trip.com 제휴는 아직 설계도 안 됨. |

## 원칙

- 개별 채널의 사소한 결함(썸네일, 캡션 스타일 등) 수정보다 이 5대 축이
  실제로 안정적으로 도는 것이 최우선이다.
- 새로운 유료 API 도입이나 실험적 기능 추가보다, 이미 구축된 것을
  전 채널에 고르게 적용하고 검증하는 쪽을 우선한다.
- 진행 상황은 이 문서를 갱신하며 추적한다 — 축마다 "부분 가동 → 완전
  가동"으로 넘어갈 때 이 표를 업데이트한다.
