# 수익 극대화 일일 운영 계획 (2026-10-01, 런던프로젝트클로드)

## 현황 (근거)
- 애드센스 계정: 최근 7일 $0.02, 28일 $0.25, 잔고 $7.85(지급기준 $10 미달, 은행정보 미등록 → 사용자 조치).
- GSC 28일: 27개 사이트 클릭 17 / 노출 2,734, 20곳 클릭 0.
- k-health365: 공개 322, GSC 색인 1 / 미색인 947 (크롤링됨-미색인 217, 발견됨-미색인 192).
- 연결 블로그스팟: k-health365.blogspot.com(6), glow.k-health365.com(4), k-health365-edu.blogspot.com(5).
- Site Kit 25/27 연결. 미연결: koreacrypto365, kskin365 (사용자 Google 로그인 필요).

## 원칙
1. 본진=애드센스 승인 워드프레스. 블로그스팟은 본진 유입 보조(관련 글 링크).
2. 글 수보다 색인되는 글. 기존 글 중 검색수요 주제 보강 우선.
3. 블로그별 주제 분리: k-health365(ko 건강) / edu(ko 의료·돌봄 자격·취업) / glow(en K-웰니스·뷰티). 중복 제목 금지.
4. 건강 글 E-E-A-T: 작성자, 출처, 의료 면책 문구.
5. 연도는 2026만 사용하거나 생략.

## 매일 자동 (GitHub Actions, PC 꺼져도 동작)
| 작업 | 워크플로 | 주기 |
|---|---|---|
| 글 발행 | daily-network-publish / daily-publication-floor / newsrooms-daily-publisher | 매일 |
| 방문·색인 현황 | daily-site-traffic | 매일 07:07 KST |
| 건강 점검+안전 자동수정 | site-health-guardian | 2일마다 06:17 KST |
| 주간 추이(7일 vs 직전 7일) | site-health-guardian 리포트 | 2일마다 |

## 발행 실패·타임아웃 폴백
- 작성 타임아웃/실패 → 최대 3회 재시도(시도당 1200초, 30·60초 백오프; scripts/retry_run.py, daily-network-publish에 적용 완료). 모델 전환은 GPT-5 mini 고정 정책과 충돌해 보류(회장 결정 필요).
- 예약시각 초과 글(future overdue)은 guardian이 자동 발행(GUARDIAN_FIX=1, 예약 실행).
- 공개 전환 승인·삭제·비공개 전환은 자동화하지 않음.

## 사용자만 할 수 있는 것
- AdSense 은행 세부정보 등록(지급 $10 도달 시).
- koreacrypto365.com, kskin365.com Site Kit Google 재연결.

## 미해결
- k-health365 noindex 40개: Rank Math 일괄동작 3회 미반영. 대안=Code Snippets 사이트맵 제외 필터(승인 필요, 아직 미적용).
- 얇은 글 보강/제목 교체/면책 문구: 미착수.
- 애널리틱스 방문자 수 미확인.
