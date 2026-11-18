# London Project — 사이트 포트폴리오 운영·개편 마스터 명세
확정 기준일: 2026-11-18
상태: **사용자 승인된 설계 명세 / 사이트 변경·발행·배포 완료 아님**
대상: WordPress 및 별도 서비스 플랫폼, SeoulMall. 도메인 목록은 실사로 재확인한다.
원칙: 이 문서가 자동으로 WordPress 설정을 바꾸지는 않는다. 백업·검증 없이 대량 수정 금지.

## A. 전 사이트 공통 정책
- 모든 사이트는 2026년 연말에 방문량, 검색 유입(GSC), 광고/제휴 매출, 전환율, 콘텐츠 품질, 자동발행 성공률, 중복도를 평가하여 유지·확대·통합·폐쇄 결정. **특정 사이트만 연말 평가 대상이 아님.** 평가 전 임의 통합·삭제 금지.
- 기존 글: 사이트별 예외를 제외하고 전체 실사 후 카테고리 재배치, 누락/깨진 이미지 복구, 대표/본문 이미지 분리, ALT, 중복 제목 및 유사 글 정비, 정보 갱신, 내부링크/SEO, 잘못된 카테고리, 짧은 본문 보강. 기존 URL 보호, 필요한 변경 시 301 리디렉션 및 인덱싱 점검.
- 일반 기사: 2,500–4,000자 기준, H1/H2/H3, 요약, 짧은 문단, FAQ, 사이트별 강조색. 제목에 연도 기계적 삽입 금지. 실제 정보·출처 확인. 뉴스 속보는 길이 예외. K-health365 기존 글은 대량 재작성 예외.
- 이미지: Pexels/Pixabay 랜덤 선행, 실패 시 SDXL Turbo → FLUX Schnell; 저작권·사용권 확인, ALT 필수, 대표/본문 중복 금지, 14일 내 이미지 재사용 금지. 이미지 없는 글은 발행 보류하고 오류 기록·복구.
- 생성: 무료 Gemini 언어별 6단계 폴백 구성은 기존 런던 프로젝트 규칙 유지; 실제 API 모델 유효성 점검 후 사용. 각 사이트별 편집 페르소나/언어/주제 분리. 중복 제목·키워드·본문 방지.
- 자동발행: 각 WP 사이트 1일 1회 목표, 정각 고정 대신 랜덤 시각. API 인증 사전검사, 재시도, 멱등성, 성공 시 실제 post_id/URL/공개 상태 확인; 단순 실행 성공을 발행 성공으로 표시하지 않음. 실패 원인·로그·통제실 표시.
- 상품: 관련 기사 본문 2~3개 제품, 하단 공통 K-Beauty 5 + K-Health 5 = 10개 상품 카드, 주 1회 교체·품절/링크 확인. 금융·법률·보험·투자에는 상업성 최소화, KoreaNews365는 광고·상품 배너 제거. 승인된 제휴 링크만 사용하고 광고/제휴 고지 표시. 국가별 배송·판매 가능 여부 확인.
- 안전·규정: 의료·법률·금융·비자·취업 등 민감 정보는 공식 출처와 최신성 검증, 허위 보장·오인 표현 금지. 개인정보·신분증·지원서 등 최소 수집/권한 통제/보존·삭제 정책. 실제 사업 중개·알선·등록 필요성 별도 법적 확인.
- 공통 실행 단계: (1) 전체 실사/백업 (2) GitHub 설정 명세/버전관리 (3) 콘텐츠·이미지 정비 (4) 수익화·지원기능 개발 (5) 자동발행 정상화 및 공개 URL 검증 (6) 연말 전체 평가.
- 검증 체크: 카테고리 적용 / 게시물 재분류 / 이미지·ALT / SEO·내부·제휴링크 / 자동발행 테스트 / 실제 URL·ID / 통제실 지표. 증거 없는 완료 표시 금지.

## B. 사이트별 확정 방향
### 01 Kworld365.com
- 영어 글로벌 K-POP 전문 매체. 5개 카테고리 예외: Comebacks & New Releases; K-POP Artists & Groups; Concerts & World Tours; Charts & Music Awards; K-POP Industry News.
### 02 Kfinance365.com
- 외국인 대상 한국 금융. 4: Banking & Savings; Loans & Credit; Remittance & Exchange; Personal Finance & Policy.
### 03 KoreaInvest365.com
- 한국 주식·ETF·채권·투자전략 정보, 4개 카테고리. 구체적 기존 확정 명칭은 이전 설정/실사 대조 후 반영; 임의 확정 금지.
### 04 KoreaCrypto365.com
- 한국 암호화폐 중심 + 주요 글로벌 코인, 4개 카테고리. 세부 명칭은 이전 확정 기록 대조.
### 05 KoreaInsurance365.com
- 외국인 대상 한국 보험정보, 4개 카테고리. 세부 명칭은 이전 확정 기록 대조.
### 06 KoreaTaxnLaw
- 외국인 대상 한국 세무·법률정보, 4개 카테고리. 세부 명칭은 이전 확정 기록 대조.
### 07 K-visa365.com
- 외국인 대상 한국 비자·출입국 정보, 4개 카테고리. REST 403 등 인증 문제 점검.
### 08 StudyinKorea365.com
- 대학·장학금·TOPIK·유학생활 **정보 매체** (실제 입학 지원 기능 아님), 4개 카테고리.
### 09 JobinKorea365.com
- 외국인 대상 한국 취업정보·가이드 **정보 매체**, 4개 카테고리.
### 10 JobKorea365.com
- 영어 실제 채용공고 및 온라인 지원 플랫폼. 호텔·관광, 요식·조리, 전기·전자, 제조, 건설·기술, IT·엔지니어링, 물류, 보건 등 **직종/산업별 탐색**. 4개 상위 그룹 안에 직종별 하위 분류 가능. Apply Online은 카테고리가 아닌 전역 기능. 공고별 고용주, 급여, 지역, 자격, 비자 적격성, 마감, 숙소/복지, 지원 버튼. 이력서 업로드·고용주 심사·지원상태 조회. 취업정보 사이트들과 연말 비교.
### 11 Krealestate365.com
- 외국인 대상 한국 임대·매매·주거법·부동산시장 정보, 4개 카테고리.
### 12 KoreaWedding365.com
- **A안: 실제 문화·언어교류 클럽**, 결혼중개를 문화교류로 위장하지 않음. 4: Korean Language Exchange; Korean Culture & Lifestyle; Community Events & Activities; Relationships & Cross-Cultural Communication.
- 무료 회원가입, 언어교류·문화행사 신청, 유료 행사/강좌/멤버십 검토. 성인확인·동의·신고/차단·프라이버시. 결혼 상대 소개·수수료 사업은 별도 법적 적합성/등록 검토 전 시행 금지.
### 13 KoreaMedicalTour.com
- 외국인 대상 의료관광·병원 상담 플랫폼. 4: Plastic Surgery & Aesthetics; Health Checkups & Clinics; Hospitals & Medical Services; Medical Travel & Patient Guide.
- 병원정보→진료 선택→상담신청→진행상태; 병원/의료진/가격/효과 검증, 개인정보 보호. 실제 환자 유치·알선 및 수수료는 등록요건 검토 후.
### 14 Kskin365.com
- **K-Beauty를 주요 검색 키워드**로 하는 영어 스킨케어 전문 매체 + 쿠팡 파트너스 판매. 4: K-Beauty Skincare; Skin Concerns & Solutions; K-Beauty Ingredients; K-Beauty Products & Reviews.
- 기사 관련 제품 2~3, 하단 10개 카드, 해외 배송 가능성 표시. 정보/성분/루틴 중심, OliveYoungKorea와 역할 분리.
### 15 OliveYoungKorea.com
- K-Beauty 쇼핑·제휴 판매 플랫폼. 4: K-Beauty Skincare; Korean Makeup & Cosmetics; Hair, Body & Personal Care; K-Beauty Deals & Shopping Guides.
- 쿠팡/승인된 올리브영 제휴/SeoulMall 링크, 가격·품절·배송 검증. 공식 올리브영과의 관계 오인 금지, 상표·로고 검토.
### 16 K-trip365.com
- 영어 한국 여행정보 + 예약 제휴 플랫폼. 4: Korea Destinations & Attractions; Korean Food & Culture; Hotels, Transport & Travel Tips; Korea Tours & Experiences.
- **상단 여행 이미지 5장 슬라이더, 3열 카드형 레이아웃**, 승인된 Trip.com·Booking.com 등 호텔/투어 제휴. 가격/예약 가능 여부 검증.
### 17 KoreaNews365.com
- **한국어 정치 중심 디지털 신문**, 정치 약 70%(정치·국회 50 + 정치 속보·쟁점 20), 사회·경제 20, 국제·스포츠 10은 편집 목표. 4: 정치·국회; 정치 속보·쟁점; 사회·경제; 국제·스포츠.
- 신문형 헤더 '한국신문 Korea Newspaper', 민족정론지, 발행인 Chris Huh, 창간 2020.11.02(표시 내용 확인). **광고·상품 배너 제거**. 속보 글자수 예외, 실제 사진/저작권, 날짜·출처·정정, 사실과 논평 분리. 대치/격돌 등은 확인된 사건일 때만.
### 18 Korea365.org
- **전체 전문 사이트 통합 허브**. 4: Study, Work & Visa; Finance, Law & Living; Travel, Culture & Lifestyle; Health, Beauty & Shopping.
- 전문 사이트별 최신 글·로고·통합 검색·원문 연결, 중복 전문기사 복제 금지. JobKorea365 채용 지원, KStudy365 입학 지원 연결.
### 19 K-health365.com
- **한국어 100%**. 사용자가 현재 운영 포트폴리오에서 **유일하게 AdSense 승인받은 사이트**라고 명시. AdSense 코드·광고 설정 및 기존 URL/검색 유입 보호. **기존 게시물 대량 재작성 금지**(명백한 오류·깨진 이미지 등 선별 수정만).
- 4: 건강·질병 예방; 영양·건강식품; K-뷰티·피부관리; K-헬스·건강용품.
- 신규 한국어 건강정보·K-Beauty/K-Health 상품 비교·판매 강화. 본문 2~3개, 하단 K-Beauty 5 + K-Health 5 쿠팡 상품 카드. 의료효능 과장 금지, AdSense와 제휴 수익 병행.
### 20 JobKoreaGlobal.com
- 해외 거주 외국인 대상 영어 한국 취업정보 사이트, JobinKorea365와 유사하지만 해외 구직 준비에 차별화. 4: Korea Jobs & Industries; Work Visa & Employment Rules; Salary & Working Conditions; Job Application & Career Guide.
- 기존 글 전면 정비. **지금 정상 운영**, 연말 JobinKorea365/JobKorea365와 통합·유지·폐쇄 검토. 미리 보류·폐쇄 금지.
### 21 KStudy365.com
- **실제 대학 온라인 입학 지원 플랫폼** (StudyinKorea365 정보매체와 분리). 4개 메뉴: Find Universities; Admissions & Scholarships; Apply Online; My Applications.
- 대학/학과 검색, 지원서/서류 제출, 학생·대학 담당자·관리자 권한, 대학 심사·서류 보완·상태 조회. 공식 대학 계약/권한 검증, 여권·학력서류 암호화·접근통제·보존·삭제. JobKorea365와 공통 지원 엔진 재사용 검토하되 데이터 분리.
### 22 SeoulMall (정확한 운영 도메인 실사 필요)
- **A안 K-Beauty·K-Health 중심 제휴형 쇼핑몰**; 직접 재고·결제·배송 없음. 4: K-Beauty & Skincare; K-Health & Wellness; Korean Lifestyle & Home; Best Deals & Trending Products.
- 쿠팡 파트너스/승인된 제휴처, Kskin365·OliveYoungKorea·K-health365 및 다른 사이트에서 관련 상품 유입. 상품명/가격/이미지/품절/배송지역/제휴 고지 검증, 클릭·전환·수익 분석.

## C. 포트폴리오 수량 정합성
- 위 목록은 **서로 다른 사이트/서비스 22개**다. 이전 대화에서 '23번째'로 SeoulMall을 불렀지만 실제 23번째 독립 도메인은 확인되지 않았다.
- '전체 공통 운영 체계'는 웹사이트가 아니며 23번째 도메인으로 세지 않는다.
- GitHub의 실 운영 WordPress/Blogspot/Tistory/서비스 도메인 목록과 대조하여 누락된 사이트를 식별한다. 이미 제외 지시된 SIS-korea.com, KI-korea.com, KIKorea.com, SISKorea.com, TheSeoulJournal.com 등은 임의 복원하지 않는다.
- 일부 초기 4개 카테고리의 **정확한 이름이 이 대화의 가용 요약에 없음**: 방향/카테고리 수만 확정으로 기록하고, 기존 설정/원문을 재확인한 뒤 이름을 채운다.

## D. 우선순위·실행 통제
1. GitHub/실제 사이트 실사·백업·현재 게시물/카테고리/광고/인증 기준선 기록.
2. K-health365 AdSense와 기존 콘텐츠 보호.
3. SeoulMall 제휴 카탈로그 및 실제 승인 링크 확인.
4. Kskin365·OliveYoungKorea 쇼핑 전환 연결.
5. 나머지 정보 사이트 게시물·이미지·SEO 순차 정비.
6. JobKorea365 채용 지원, KStudy365 대학 지원 별도 플랫폼 개발 및 법적/개인정보 검토.
7. 자동발행 검증 및 통제실 실데이터 연동.
8. 2026 연말 **모든 사이트** 평가, 취업 3개 중복·통합 별도 집중 분석.
- 구현은 사이트별 백업→작은 변경→검증→확대. 실제 게시물/코드/배포는 이 문서 커밋만으로 변경되지 않는다.
- 완료 증거: Git commit SHA, 변경 파일, 게시물 ID·URL, 전후 스크린샷/로그, 오류 및 롤백 기록.
