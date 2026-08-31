# WordPress 발행 등급 (2026-08-31 확정)

사용자 확정, `scripts/set_special_a_tier.py`로 시트에 반영. 이 문서가 최종 기준이며,
시트 값이 이 문서와 어긋나면 이 문서를 기준으로 시트를 다시 맞춘다.

## 특A — 10개 (일 1포, 랜덤 시간)

하루 200명 이상 방문자 확인된 사이트. `group=특A`, `weekly_min=weekly_max=7`
(매일 발행). 발행 시각은 기존 `publish_scheduler.py`의 랜덤 슬롯 로직을 그대로 쓴다
(사이트별 고정 시각이 아니라 매일 다시 무작위 배정 - "네트워크처럼 보이는 신호"를
스스로 만들지 않기 위한 기존 원칙 유지).

| # | site_id | 도메인 | 비고 |
|---|---|---|---|
| 1 | wp_kfinance365 | kfinance365.com | 기존 A |
| 2 | wp_kcrypto365 | koreacrypto365.com | 기존 B → 특A로 승급 |
| 3 | wp_kskin365 | kskin365.com | 기존 A |
| 4 | wp_ktrip365 | k-trip365.com | 기존 A |
| 5 | wp_kvisa365 | k-visa365.com | 기존 A |
| 6 | wp_koreawedding | koreawedding365.com | 기존 A |
| 7 | wp_sis | sis-korea.com | 기존 B → 특A로 승급 |
| 8 | wp_jobkorea365 | jobkorea365.com | 기존 A |
| 9 | wp_jobglobal | jobkoreaglobal.com | 기존 A |
| 10 | wp_kstudy365 | kstudy365.com | 기존 A |

AI 흔적 없애기(자연스러운 문체)는 별도 프롬프트/콘텐츠 정책 과제 - 이 문서는
발행 주기만 다룬다.

## A — 9개 (주 3-4회, 기존 그대로)

특A로 승급한 8개(위 표에서 "기존 A" 8개)를 뺀 나머지.

| site_id | 도메인 |
|---|---|
| wp_korea365 | korea365.org |
| wp_oliveyoung | oliveyoungkorea.com |
| wp_khealth365 | k-health365.com |
| wp_kinsurance365 | koreainsurance365.com |
| wp_koreataxlaw | koreataxnlaw.com |
| wp_medicaltour | koreamedicaltour.com |
| wp_studyinkorea | studyinkorea365.com |
| wp_jobinkorea | jobinkorea365.com |
| wp_kworld365 | kworld365.com |

## B — 6개 (주 2-3회, 기존 그대로)

특A로 승급한 2개(koreacrypto365, sis-korea)를 뺀 나머지.

| site_id | 도메인 |
|---|---|
| wp_kinvest365 | koreainvest365.com |
| wp_krealestate | krealestate365.com |
| wp_ktech365 | ktech365.com |
| wp_kieca | kieca-korea.org |
| wp_ksa | ksa-korea.org |
| wp_kikorea | ki-korea.com |

## NEWS — 2개 (주 21-70회, 변경 없음)

| site_id | 도메인 |
|---|---|
| wp_koreanews | koreanews365.com |
| wp_seouljournal | theseouljournal.com |

## 합계 검산

특A 10 + A 9 + B 6 + NEWS 2 = **27개** (전체 워드프레스 사이트 수와 일치)
