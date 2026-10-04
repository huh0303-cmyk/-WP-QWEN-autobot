# 2027 포트폴리오 계획 — 분야별 1사이트 집중

**상태: 확정 (Chairman, 2026-10-04 18:20 KST — "큰 이견 없으면 이 계획대로 간다")**. 이견 제기 시 갱신.

근거: docs/GSC_12M_SITE_PERFORMANCE_2026-10-04.md. 원칙: 분야당 1사이트, 나머지는 콘텐츠 통합(301) 후 도메인 만료. 목적 = AdSense 승인(전부 무료 운영).

## 유지 12 (역할)
| 분야 | 사이트 | 근거 |
|---|---|---|
| 유학(핵심) | studyinkorea365.com | 포털 구축 결정됨(4개국어, 베트남 에이전시 신청). kstudy365(19클릭)·k-visa365 통합 |
| 취업 | jobkoreaglobal.com | 45클릭/28일 노출 385. jobkorea365·jobinkorea365 통합 |
| 한국 대표 포털 | korea365.org | 허브: 각 분야 사이트로 연결 |
| 여행(수익 엔진) | k-trip365.com | 871클릭=네트워크 70% |
| 건강 | k-health365.com | 98클릭, 평균순위 9.7. koreamedicaltour 통합 |
| 뷰티 | oliveyoungkorea.com → kskin365.com | 트래픽 86이나 상표 위험: 2027 중 kskin365로 이전·301 |
| K-pop | kworld365.com | Chairman 지정 |
| 웨딩 | koreawedding365.com | 신규 성장(28일 7클릭) |
| 금융 | kfinance365.com | insurance/invest/crypto/tax/realestate 통합 |
| 신문 | koreanews365.com | 인터넷신문 등록 대상 |
| 대학 | sis-korea.com | 서울국제대학교 공식 홈 |
| 협회 | kieca-korea.org | 협회(사단법인 준비) 공식 홈 |

## 정리
- 버림: ki-korea.com, ksa-korea.org, ktech365.com, theseouljournal.com(Gabia hold)
- 통합 후 만료: kstudy365, jobkorea365, jobinkorea365, k-visa365, koreamedicaltour, koreainsurance365, koreainvest365, koreacrypto365, krealestate365, koreataxnlaw
- 도메인 연장은 301 이전 완료 시점까지만 1회 연장, 이후 만료.

## 주의
- 통합 = 글 이전/리다이렉트 작업 필요(미착수). 색인된 글 우선 보존(wp-adsense-pruning 방식).
- sis-korea·kieca-korea는 기관 홈 성격 → AdSense 대상에서 분리 여부 별도 결정.

## 발행 유지 원칙 (Chairman, 2026-10-04)
- 정리 대상 사이트도 도메인 만료 7일 전까지는 기존과 동일하게 1일 1포스팅 유지(상황 변화 대비). 워크플로우 변경 없음.
- 품질·출처 게이트 통과 못 한 글은 발행하지 않음(박제 원칙 유지) — 양 채우기 금지.
- 중단일 = 만료일 − 7일. 만료·hold 도메인(theseouljournal)은 발행 불가.
- 통합 대상 사이트의 새 글도 이전 대상이므로, 중단 시점에 색인된 글 목록을 함께 확정.

## 확정 운영
- WP 25: 1일 1포스팅 유지. daily-publication-floor 스케줄(WP 전용, 11/29/47분) 10/4 복구됨.
- Blogger 33: 1일 1포스팅 유지. VPS 타이머 소유(10/2~10/4 정상 확인), GitHub 스케줄과 이중 발행 금지.
- 만료 7일 전 재확인(예약됨): kstudy365·jobkorea365 → 2026-11-11, ktech365·krealestate365 → 2027-02-12. 나머지 정리 대상은 만료일 확인 후 추가 예약.
- 임박분(oliveyoungkorea 10/6, ki-korea·sis-korea 10/12, ksa-korea 10/14)은 위 결정대로 처리: 앞의 둘+sis 연장, ki·ksa 버림.
