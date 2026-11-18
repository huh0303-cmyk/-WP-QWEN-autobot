# London Project — Blogger/Blogspot 33개 일괄 승인 마스터 명세
**승인일:** 2026-11-18
**승인 상태:** OWNER APPROVED — 33개 편집 방향/라벨 및 공통 규칙
**적용 상태:** SPECIFICATION ONLY — 블로그 게시물·설정·API·자동발행·백업은 이 문서 커밋으로 변경되지 않음

## 근거 및 버전
- 이전 등록 목록: `docs/BLOGGER_33_LIST_2026-10-05.md` (33개 URL, 주제, 언어; 당시 공개 피드 기반, 현재 상태 아님).
- 기존 구성: `config/blogger_portfolio.json`; 기존 운영 정책 `docs/BLOGGER_CONTENT_POLICY.md`, `docs/CONTENT_IMAGE_PIPELINE_FINAL.md` 및 현재 실제 코드/설정과 **충돌 시 검토 후 단계적으로 동기화**.
- 사용자 2026-11-18 승인: 아래 33개를 **개별 승인 없이 일괄 확정**, WordPress 유사 이름을 참고하되 기사 중복 방지. 라벨은 각 4개.
- WordPress·플랫폼 확정 명세: `docs/PORTFOLIO_MASTER_PLAN_2026-11-18.md`. WP 실제 사이트/서비스는 Blogger와 별도.
- `skin.k-health365.com`, `glow.k-health365.com`은 기존 33개 등록 목록에 포함된 커스텀 도메인으로 기재되어 있으며 실 Blogger 소유/연결은 검증 필요.

## 33개 블로그 개별 운영 명세
| # | 등록 블로그 | 등록 주소 | 언어 | 확정 라벨 4개 (표시명/영어 슬러그는 적용 시 조정) | 운영 역할·주의 |
|---:|---|---|---|---|---|
| 1 | K-Trip365 | https://k-trip365.blogspot.com | en | 여행지 / 음식·문화 / 숙박·교통 / 투어·체험 | K-trip365 WordPress 여행 정보와 차별화한 검색 유입 및 원문·예약 연결 |
| 2 | KWorld365 Seoul | https://kworld365seoul.blogspot.com | en | K-POP 신곡 / 아티스트 / 공연 / 차트·산업 | 32번과 제목/기사 중복 방지, 글로벌 뉴스 중심 |
| 3 | JobKorea365 | https://jobkorea365.blogspot.com | en | 산업별 채용 / 구직 준비 / 취업비자 / 급여·근로조건 | WordPress JobKorea365 실제 온라인 지원 기능으로 연결, Blogger 자체 지원서 수집 금지 |
| 4 | KStudy365 | https://kstudy365.blogspot.com | en | 대학 검색 / 입학조건 / 장학금 / 온라인 지원 안내 | 실제 입학지원은 KStudy365.com, Blogger는 안내·유입 |
| 5 | Korea Insurance365 | https://koreainsurance365.blogspot.com | en | 의료보험 / 자동차보험 / 여행보험 / 기타 보험 | 보험 안내, 법규 및 판매·중개 자격 확인 |
| 6 | KFinance365 | https://kfinance365.blogspot.com | en | 은행·저축 / 대출·신용 / 송금·환율 / 금융정책 | 금융정보 검증, 상업성 최소화 |
| 7 | Korea Medical Tour | https://koreamedicaltour365.blogspot.com | en | 성형·피부 / 건강검진 / 병원정보 / 의료관광 | 의료광고·환자유치 관련 법적 등록 확인 |
| 8 | K-Visa365 | https://k-visa365.blogspot.com | en | 비자 종류 / 신청·연장 / 체류·영주 / 정책 | 공식 출입국 정보 확인 |
| 9 | KoreaNews365 | https://koreanews365daily.blogspot.com | ko | 정치·국회 / 정치 속보 / 사회·경제 / 국제·스포츠 | 한국어 정치 중심, 사실검증·출처, 뉴스 광고 제외 |
| 10 | Korea Invest365 | https://koreainvest365.blogspot.com | en | 한국 주식 / ETF·펀드 / 채권 / 투자전략 | 투자 위험 고지, 상업성 최소화 |
| 11 | Olive Young Korea | https://oliveyoungkorea.blogspot.com | en | 스킨케어 / 메이크업 / 헤어·바디 / 쇼핑·상품 비교 | 승인된 제휴만, 공식 브랜드로 오인 금지 |
| 12 | Korea Crypto365 | https://koreacrypto365.blogspot.com | en | 한국 코인시장 / 주요 코인 / 거래소·규제 / 블록체인 | 시세·규제·투자 위험 검증 |
| 13 | Job in Korea365 | https://jobinkorea365.blogspot.com | en | 직종별 취업 / 근로제도 / 급여·복지 / 취업 가이드 | 외국인 취업정보, 3·21번과 주제 차별화 |
| 14 | Korea Wedding365 | https://koreawedding365.blogspot.com | en | 언어교류 / 한국문화 / 커뮤니티 행사 / 국제문화 소통 | 기존 국제 데이팅 콘텐츠 재검토, 결혼중개 우회 금지 |
| 15 | The Seoul Journal | https://theseouljournal.blogspot.com | en | 한국 정치 / 한국 경제 / 사회 현안 / 국제 뉴스 | 영어 뉴스 분석 블로그, 기존 제외 도메인 TheSeoulJournal.com 재활성화 의미 아님 |
| 16 | KTech365 | https://ktech365.blogspot.com | en | AI / 반도체·전자 / 한국 기술기업 / 혁신·스타트업 | 한국 기술/산업 전문 |
| 17 | KIECA Korea | https://kieca-korea.blogspot.com | en | 국제교육 / 문화교류 / 교육협력 / 국제 프로그램 | 실제 기관 명칭·협약·프로그램 검증 |
| 18 | KI Korea | https://ki-korea.blogspot.com | en | 외국인 투자 / 한국 기업환경 / 투자제도 / 사업 진출 | 기존 제외된 KI-korea.com 도메인과 별개, 유지 여부 실사 |
| 19 | KSA Korea | https://ksa-korea.blogspot.com | en | 한국 유학 / 학생지원 / 교육 네트워크 / 문화 적응 | 교육 지원 정보, 운영 주체 검증 |
| 20 | Korea Tax & Law | https://koreataxnlaw.blogspot.com | en | 한국 세금 / 법률·권리 / 사업·노동법 / 실무 안내 | 법률·세무 최신성 검증 |
| 21 | Job Korea Global | https://jobkoreaglobal.blogspot.com | en | 해외 구직 / 취업비자 / 급여·근로조건 / 지원 준비 | 해외 거주 외국인, 취업 3사이트 연말 통합 평가 |
| 22 | Study in Korea365 | https://studyinkorea365.blogspot.com | en | 대학·입학 / 장학금 / TOPIK / 유학생활 | 정보 콘텐츠, KStudy365.com 실제 지원과 구분 |
| 23 | Korea365 Guide | https://korea365guide.blogspot.com | en | 유학·취업·비자 / 금융·생활 / 여행·문화 / 건강·쇼핑 | 전문 사이트 원문 링크 중심 허브, 중복 전문 복제 금지 |
| 24 | SIS Korea | https://sis-korea.blogspot.com | en | 국제학교 / 한국어·TOPIK / 유학 경로 / 학생생활 | 기존 제외 SIS 관련 도메인과 혼동 금지, 소유·유지 여부 별도 검증 |
| 25 | Korea Real Estate365 | https://krealestate365.blogspot.com | en | 임대 / 매매 / 주거법 / 부동산시장 | 법적·가격정보 최신성 |
| 26 | K-Health365 연구소 | https://k-health365.blogspot.com | ko | 건강·질병 / 영양·식단 / K-뷰티 / K-헬스 제품 | WordPress K-health365.com AdSense/기존 글 보호, 블로그와 별개 |
| 27 | KSkin365 | https://skin.k-health365.com | en | K-Beauty 스킨케어 / 피부 고민 / 성분 / 제품 리뷰 | K-Beauty SEO, 제휴상품 검증; 커스텀 도메인 여부 확인 |
| 28 | K-Wellness Lab | https://glow.k-health365.com | en | 웰니스 / K-Beauty / 건강습관 / 제품 비교 | 27번과 중복 최소화; 커스텀 도메인 여부 확인 |
| 29 | K-Medical Job Center | https://k-health365-edu.blogspot.com | ko | 의료직 취업 / 자격증 / 보건·돌봄 / 교육·채용 | 공식 자격요건 검증 |
| 30 | 한국생활지원정보 | https://korea-life-support365.blogspot.com | ko | 정부지원금 / 복지혜택 / 주거지원 / 생활지원정책 | 정부 지원 정책과 신청 자격·기간 확인 |
| 31 | Korea Daily Mix | https://koreamedicaltour1.blogspot.com | en | 한국 생활 / 문화·트렌드 / 여행 / 실용정보 | 도메인과 현재 브랜드 주제 불일치 점검 |
| 32 | KWorld365 | https://kworld365.blogspot.com | en | K-POP 아티스트 / 신곡 / 글로벌 팬덤 / 공연·차트 | 2번과 중복 방지, 팬덤 중심 |
| 33 | Seoul International School Guide | https://seoulintlschoolguide.blogspot.com | en | 국제학교 / 입학·학비 / 교육과정 / 학교생활 | 학교 공식 소속 오인 금지, 모집정보 검증 |

## 공통 발행·정비·수익화 규칙 (전체 승인)
1. **백업 선행:** Blogger API/실제 계정에서 소유 블로그 ID·URL·제목·언어·기존 라벨·게시물·이미지·테마/설정 확인. 게시물·테마/설정 내보내기 및 복구 테스트 후 변경. 33개 목록과 현재 소유 목록을 대조하고 누락/이름 변경/중복/커스텀 도메인 기록.
2. **4개 라벨:** Blogger는 WordPress 카테고리가 아니라 라벨을 사용한다. 기존 게시물은 새 라벨로 점진적 매핑, 관련 없는 오래된 라벨 정리 전 검색/내부 링크 영향을 점검. 기사별 라벨은 필요한 범위에서 부여.
3. **기존 글 정비:** 중복 제목·주제·본문, 잘못된 라벨, 깨진 이미지, 대표/본문 중복, ALT 누락, 짧은 본문, 오래된 정책/가격/비자/금융·건강 정보, 잘못된 링크·SEO를 진단하고 수정. 기존 URL은 원칙적으로 유지. **WP K-health365.com 기존 글은 일괄 재작성 금지**.
4. **콘텐츠 형식:** 사이트 언어 준수 (위 표 한국어 4개, 나머지 영어), 일반 2,500–4,000자 목표, H2/H3, 요약, 짧은 단락, FAQ, 사이트별 색상 강조 박스, 사실/출처 검증. 정치 뉴스 속보는 분량 예외. 제목에 연도 불필요 삽입 금지.
5. **글 엔진:** 기존 London Project의 언어별 Gemini 무료 6단계 폴백을 따르되 실제 사용 가능한 모델명/쿼터를 사전 검사. 같은 제목·키워드·문장·본문의 WP/다른 Blogger 재게시 금지. 블로그별 고유 관점·독자·검색어 유지.
6. **이미지:** Pexels/Pixabay 랜덤 선행 → SDXL Turbo → FLUX Schnell, 권리 확인. 이미지 14일 중복 사용 금지(URL/해시/파일명), 대표·본문 중복 금지, ALT 필수. 필수 이미지 확보 실패 시 정상 완료/발행 성공 처리하지 않고 복구 대기.
7. **발행:** 승인된 블로그별 하루 1회 기준, 정각이 아닌 랜덤 시간(실행 환경/쿼터 고려). Blogger OAuth 범위·refresh token·블로그 쓰기 권한 사전 검사. API 403 및 성공표시-실제 미게시 이력 점검. 발행 성공은 Blogger의 실제 게시물 ID/URL·공개 상태 확인으로만 인정. 실패 원인·재시도·중복 발행 방지·로그 기록.
8. **제휴:** 승인된 쿠팡·OliveYoung·Trip 등 실제 프로그램만 사용. 해당 기사 본문 맥락 상품 2~3개와 하단 K-Beauty 5 + K-Health 5 (주 1회 갱신) 기본; 금융/법률/보험/투자에서는 상업성 최소화, 정치 신문에는 광고 배너 제외. 제품 링크·품절·가격·국가별 배송/구매 가능 여부·제휴 고지 확인. Blogger의 자체 광고/AdSense 승인 상태를 WP 승인과 혼동 금지.
9. **대시보드:** 블로그별 게시물 수·증감, 전일 페이지뷰·증감, 누적 조회수·증감, GSC 색인수·증감, 최근 발행시간·경과 신호등(1일 녹색/2일 노랑/3일 이상 빨강), 즉시발행 및 진행상세 5단계(주제→글→이미지→업로드→게시 검증), 하단 엔진/글자수/제목/URL/한국시간. 실제 데이터 미확인 시 '미확인'으로 표시.
10. **안전·규정:** 실제 법률·의료·비자·투자·지원금 정보의 최신성/출처, 의료관광 환자유치 등록, 결혼중개 등록, 학교/기업 공식 관계, 저작권, 개인정보 처리 여부 확인. 뉴스는 허위 인용·확인되지 않은 정치적 대립/여론 수치 금지.
11. **연말 평가:** 33개 **전체**를 2026 연말 성과 비교(트래픽/색인/수익/품질/발행/중복) 후 유지·확대·통합·폐쇄 검토. 2+32 KWorld365, 3+13+21 취업, 27+28 뷰티/웰니스, 23번 허브 등 중복 위험 특별 점검. 평가 전 임의 삭제·통합 금지.
12. **실행 순서:** (a) 읽기 전용 실사·등록 33개 검증 (b) 계정·API 인증 및 백업 (c) 라벨/기사 소규모 샘플 적용 (d) 이미지·SEO·상품·내부링크 (e) Blogger 게시 테스트 및 ID/URL 검증 (f) 전체 확장 및 통제실 연동 (g) 연말 평가. 배포·발행 전후 기록과 롤백 수단 필수.

## 검증 체크리스트 — 각 블로그에 개별 적용
- [ ] 현재 블로그 소유·ID·URL 확인
- [ ] 백업 완료 및 복원 가능성 확인
- [ ] 확정 라벨 4개 적용·기존 글 분류
- [ ] 콘텐츠 품질/중복/정확성 정비
- [ ] 이미지·ALT·링크·SEO 검사
- [ ] Blogger OAuth·게시 API 테스트
- [ ] 실제 발행 ID·공개 URL 검증
- [ ] 통제실 실측 지표 반영
- [ ] 변경·오류·롤백 기록

**주의:** 이 커밋은 정책/계획의 영구 기록이며 33개 Blogger 실시간 운영 변경, 발행, 백업 완료를 의미하지 않는다.
