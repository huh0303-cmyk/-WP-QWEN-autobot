# WordPress 발행 주기 (2026-09-02 확정)

이 문서는 WordPress 27개 목적지의 발행 수량 단일 기준이다. 과거 특A/A/B 등급별
발행 빈도는 폐지하며, 성장 우선순위 등급은 발행 수량을 변경하지 않는다. Google Sheet
`자동화_사이트설정`과 `config/automation_hub_sites.json`이 이 기준과 다르면 아래 값으로
복구한다.

## 일반 WordPress — 25개

모든 일반 WordPress 사이트에 동일하게 적용한다.

- `daily_min=1`
- `daily_max=1`
- `weekly_min=7`
- `weekly_max=7`
- 발행 시각은 2주 캘린더의 사이트별 분산 슬롯을 따르며, 지난 시각은 `PASS` 처리한다.

| site_id | 도메인 |
|---|---|
| wp_kfinance365 | kfinance365.com |
| wp_kcrypto365 | koreacrypto365.com |
| wp_kskin365 | kskin365.com |
| wp_ktrip365 | k-trip365.com |
| wp_kvisa365 | k-visa365.com |
| wp_koreawedding | koreawedding365.com |
| wp_sis | sis-korea.com |
| wp_jobkorea365 | jobkorea365.com |
| wp_jobglobal | jobkoreaglobal.com |
| wp_kstudy365 | kstudy365.com |
| wp_korea365 | korea365.org |
| wp_oliveyoung | oliveyoungkorea.com |
| wp_khealth365 | k-health365.com |
| wp_kinsurance365 | koreainsurance365.com |
| wp_koreataxlaw | koreataxnlaw.com |
| wp_medicaltour | koreamedicaltour.com |
| wp_studyinkorea | studyinkorea365.com |
| wp_jobinkorea | jobinkorea365.com |
| wp_kworld365 | kworld365.com |
| wp_kinvest365 | koreainvest365.com |
| wp_krealestate | krealestate365.com |
| wp_ktech365 | ktech365.com |
| wp_kieca | kieca-korea.org |
| wp_ksa | ksa-korea.org |
| wp_kikorea | ki-korea.com |

## 뉴스룸 — 2개

뉴스룸은 일반 WordPress 수량에서 제외하고 적격 RSS 건수에 따라 각각 독립 운영한다.

- `daily_min=3`
- `daily_max=10`
- `weekly_min=21`
- `weekly_max=70`
- 적격 RSS가 없으면 허위 기사를 만들어 최소 수량을 채우지 않는다.

| site_id | 도메인 |
|---|---|
| wp_koreanews | koreanews365.com |
| wp_seouljournal | theseouljournal.com |

## 합계 검산

일반 WordPress 25 + 뉴스룸 2 = **27개**.
