import os

KEYWORDS_DB = {
    "keywords_khealth.txt": [
        "당뇨 초기증상", "고혈압 낮추는법", "간수치 내리는음식", "오메가3 고르는법", "유산균 추천",
        "크릴오일 효능", "비타민D 부족증상", "마그네슘 많은음식", "루테인 효과", "밀크씨슬 복용법",
        "콜레스테롤 낮추는 운동", "공복혈당 낮추기", "지방간에 좋은 음식", "통풍 원인", "역류성식도염 완화",
        "갑상선 기능저하증", "요로결석 증상", "담석증 통증", "전립선비대증 관리", "갱년기 영양제",
        "아르기닌 효능", "콜라겐 고르는 기준", "프로폴리스 원액 효과", "종합비타민 순위", "코엔자임Q10",
        "새싹보리 효능", "보스웰리아 관절", "타트체리 불면증", "식이섬유 많은 영양제", "단백질 보충제 추천",
        "허리디스크 스트레칭", "목디스크 베개", "손목터널증후군 보호대", "족저근막염 깔창", "무릎연골 강화운동",
        "자가면역질환 종류", "대상포진 예방접종", "독감 예방주사 시기", "폐렴구균 백신", "아토피 크림 추천",
        "여드름 흉터 연고", "탈모 샴푸 효과", "원형탈모 치료", "새치 원인", "두피 스케일링",
        "불면증 극복하는 법", "멜라토닌 직구", "스트레스 해소법", "만성피로 증후군", "공황장애 초기증상",
        "우울증 자가진단", "치매 예방 운동", "이명 치료 방법", "안구건조증 안약", "비염 작두콩차",
        "천식 흡입기 사용법", "대상포진에 좋은 음식", "골다공증 영양제", "류마티스 관절염", "체지방 줄이는 다이어트"
    ],
    "keywords_koreanews.txt": [
        "한국 부동산 정책 동향", "K-콘텐츠 글로벌 흥행 비결", "한국은행 기준금리 전망", "국내 주식시장 시황 분석", "반도체 수출 실적 리포트",
        "국내 전기차 보조금 현황", "청년 주거지원 정책 총정리", "육아휴직 급여 인상안", "소상공인 저금리 대환대출", "국민연금 개혁안 핵심",
        "지방자치단체 지원금 조회", "올해 세법 개정안 포인트", "국내 고용동향 및 취업률", "K-배터리 기술 개발 현황", "한국 인공지능 스타트업",
        "우주항공청 개청 효과", "국내 저출산 대책 예산", "기후변화 대응 탄소중립", "신재생에너지 인프라 구축", "한국 관광 마케팅 전략",
        "K-푸드 전세계 수출 현황", "바이오 의약품 국내 생산", "디지털 자산 법안 통과", "국내 물가 동향 및 전망", "소비자 신뢰지수 변화",
        "청년 창업 지원 프로그램", "중소기업 육성 자금 신청", "수도권 광역급행철도 GTX 개통", "지방 소멸 대응 기금", "대중교통 정기권 혜택",
        "소비자 피해 구제 방법", "개인정보 보호법 강화 조치", "국내 로봇 산업 투자 규모", "자율주행 자동차 시범 운행", "메타버스 규제 가이드라인",
        "의료 개혁 및 필수의료 지원", "국가 장학금 신청 기간", "늘봄학교 확대 운영 계획", "고향사랑기부제 참여 방법", "전세사기 피해자 지원 대책",
        "생애 최초 주택구독 혜택", "종합소득세 신고 주의사항", "연말정산 미리보기 활용", "전통시장 활성화 온누리상품권", "국내 방산 수출 역대 최고",
        "조선업 수주 실적 분석", "엔저 현상이 국내 경제에 미치는 영향", "미국 대선과 한국 경제 전망", "글로벌 공급망 재편 대응", "해외 주식 투자 양도세",
        "국내 원전 건설 재개 동향", "수소 경제 활성화 로드맵", "AI 반도체 팹리스 육성", "스타트업 투자 유치 성공 사례", "국내 OTT 시장 점유율 경쟁",
        "웹툰 플랫폼 글로벌 확장", "K-뷰티 인디 브랜드 열풍", "전통 문화 콘텐츠의 현대화", "국내 축제 및 대형 행사 일정", "지역 경제 활성화 성공 모델"
    ],
    "keywords_medicaltour.txt": [
        "Best health checkup in Seoul", "Korean plastic surgery safety", "Laser skin clinic Seoul Gangnam", "Dental implants in Korea price", "Lasik surgery cost Seoul",
        "Korean medical visa requirements", "Top hospitals in Seoul for foreigners", "Cancer treatment technology Korea", "Orthopedic surgery Seoul", "Korean dermatology clinic review",
        "Medical tourism packages Korea", "English speaking doctors Seoul", "Stem cell therapy in Korea", "Hair transplant Seoul review", "Infertility clinic Seoul IVF",
        "Traditional Korean medicine clinic", "Spine hospital Seoul international", "Cardiovascular checkup Korea", "Eye clinic Seoul foreign patients", "Veneers in Korea dental cost",
        "Rhinoplasty Seoul best surgeon", "Facelift surgery Korea price", "Breast augmentation Seoul clinic", "Liposuction in Korea review", "Anti aging treatment Seoul",
        "Korean facial contouring safety", "Double eyelid surgery Seoul", "Botox and filler Gangnam price", "Acne scar treatment Seoul clinic", "Tattoo removal Korea clinic",
        "Health screening center Seoul", "Medical coordination agency Korea", "Foreigner insurance medical Korea", "Post surgery care hotel Seoul", "Emergency hospital Seoul English",
        "Robotic surgery in Korea", "Pediatric hospital Seoul foreign", "Korean health insurance expats", "Gastric bypass surgery Korea", "Chiropractic clinic Seoul English",
        "Dermal fillers Gangnam clinic", "Ulthera and Shurink Seoul", "Pigmentation treatment Korea", "Mole removal Seoul price", "Body contouring Korea clinic",
        "Korean wellness medical tour", "Luxury medical checkup Seoul", "Joint replacement surgery Korea", "Cataract surgery Seoul price", "Orthodontics clinic Seoul English",
        "Jaw surgery Korea review", "Skin booster Chanel injection Seoul", "Rejuran healer price Gangnam", "Foreign patient rights Korea", "Medical tour guide Seoul",
        "Korean medicine detox program", "Scalp clinic Seoul hair loss", "Plastic surgery recovery tips", "Best medical district Seoul", "Telehealth services Korea foreigners"
    ],
    "keywords_kskin.txt": [
        "Glass skin routine steps", "Korean rice toner benefits", "Centella asiatica for acne", "Snail mucin serum review", "Best Korean sunscreen no white cast",
        "Double cleansing oil and foam", "Korean sheet mask skin barrier", "Hyaluronic acid ampoule Korea", "Galactomyces ferment filtrate", "Probiotics in Korean skincare",
        "Mugwort extract soothing cream", "Korean anti aging eye cream", "Vitamin C serum K-beauty", "Chemical exfoliant AHA BHA PHA", "Korean moisturizing cream dry skin",
        "Sebum control toner oily skin", "Sensitive skin K-beauty brands", "Korean skincare routine for acne", "Brightening serum dark spots", "Collagen cream K-beauty review",
        "Pore minimizing toner Korea", "Korean lip mask overnight", "Ceramide cream skin barrier repair", "Green tea toner oily skin", "Ginseng anti aging serum",
        "Korean skincare ingredients guide", "Cruelty free K-beauty brands", "Vegan Korean skincare line", "Hydrogel eye patch review", "Korean pimple patch how to use",
        "Exosome skincare trend Korea", "PDRN salmon DNA serum", "Glutathione skin brightening", "Korean sun stick convenient", "Milk skin toner challenge",
        "Tea tree ampoule redness", "Korean exfoliating mitt body", "All-in-one Korean lotion men", "Teenage acne K-beauty routine", "Mature skin K-beauty regimen",
        "Korean sleeping pack hydration", "Heartleaf extract redness relief", "Bamboo water hydrating gel", "Korean wash off mask pack", "Peptide complex serum Korea",
        "Propolis glow serum K-beauty", "Licorice root extract dark spots", "Beta glucan vs hyaluronic acid", "Korean facial oil glowing skin", "Daily sunscreen anti aging K-beauty",
        "Korean cushion foundation skincare", "K-beauty trends 2026", "Aesthetic clinic skincare products", "Korean face mist hydration", "Niacinamide toner K-beauty",
        "Rice bran enzyme powder wash", "Korean sun milk matte finish", "Cica balm irritated skin", "Squalane moisturizer Korea", "K-beauty holy grail list"
    ],
    "keywords_korea365.txt": [
        "Hanok village stay guide", "Korean temple stay experience", "How to wear Hanbok Seoul", "Hangul learning tips beginners", "Korean etiquette for tourists",
        "Traditional Korean tea house", "Gyeongbokgung palace night tour", "K-pop dance class Seoul", "Korean history museum guide", "Traditional market street food",
        "Korean folk village Yongin", "Namsan Seoul tower cable car", "Han river park picnic delivery", "Korean drinking culture rules", "Chuseok holiday traditions Korea",
        "Seollal lunar new year guide", "Korean calligraphy class", "Nanta non verbal performance", "Korean national parks hiking", "Jeju island cultural sites",
        "Busan Gamcheon culture village", "Gyeongju historical city tour", "Korean pottery making experience", "Andong Hahoe folk village", "DMZ tour from Seoul guide",
        "Korean street fashion trends", "K-drama filming locations Seoul", "Hongdae street performance busking", "Itaewon international district", "Insadong antique shopping",
        "Korean subcultures and trends", "Jimjilbang Korean spa guide", "PC bang culture in Korea", "Noreabang Korean karaoke tips", "Korean convenience food hacks",
        "Mukbang cultural phenomenon", "Korean wedding traditions vs modern", "K-beauty shopping in Myeongdong", "Korean local festivals calendar", "Taekwondo experience program",
        "Korean superstition and myths", "Traditional Korean instruments", "Pansori folk music history", "Korean architecture ancient modern", "Hanji traditional paper craft",
        "Korean climate and seasons packing", "Public transportation tips Korea", "T-money card guide foreigners", "Sim card vs wifi egg Korea", "Useful Korean phrases travel",
        "Korean cafe culture interior", "Han river sunset viewpoints", "Seoul night market schedule", "Korean independent indie music", "Korean cinema beyond Parasite",
        "K-art modern art galleries", "Korean literature translated english", "Korean table manners formal", "Living in Korea expat guide", "DDP Dongdaemun architecture tour"
    ],
    "keywords_jobinkorea365.txt": [
        "E7 visa job search Korea", "D10 job seeking visa guide", "English teaching jobs Seoul", "Global companies in Gangnam", "Korean resume format resume",
        "Job interview tips Korean corporate", "Working holiday visa Korea jobs", "Foreigner recruitment agencies Seoul", "Tech startup jobs Korea English",
        "Korean language ability TOPIK job", "Average salary in Seoul expats", "LinkedIn networking in Korea", "Corporate culture in South Korea", "Internship programs for foreigners",
        "Software engineer jobs Seoul English", "Digital marketing jobs Korea", "Customer service jobs foreigners", "Translation interpretation jobs Seoul", "Visa sponsorship companies Korea",
        "Part time jobs Seoul international", "Work environment in tech Korea", "Labor laws Korea foreign workers", "Severance pay calculation Korea", "Health insurance foreign employees",
        "National pension refund expats", "Overtime pay regulation Korea", "Annual leave policy Korean labor", "Discrimination laws workplace Korea", "Remote work friendly companies Seoul",
        "Networking events professionals Seoul", "Korean business etiquette guide", "Negotiating salary Korean company", "Job change notification immigration", "F27 points visa strategy",
        "F5 permanent residency job", "Startup visa OASIS program", "English copywriter jobs Seoul", "Hotel industry jobs Korea foreign", "Aviation airline jobs Seoul",
        "Global trade company recruitment", "Logistics supply chain jobs Korea", "Finance banking jobs Seoul expats", "Graphic designer portfolio Korea", "UI UX design jobs Seoul",
        "Data scientist jobs Korea English", "Product manager recruitment Seoul", "E-commerce specialist jobs Korea", "Luxury retail brand jobs Seoul", "Embassy jobs in Seoul recruitment",
        "NGO non profit jobs Korea", "University lecturer jobs foreigners", "Research fellow positions Korea", "Biotech company jobs Seoul", "Automotive industry career Korea",
        "Shipbuilding engineering jobs Korea", "Green energy job market Korea", "Freelance developer tax Korea", "Contract worker rights Korea", "Job search websites South Korea"
    ],
    "keywords_jobkorea365.txt": [
        "How to get job in Korea", "Working in Seoul as foreigner", "High paying jobs Korea expats", "Visa sponsor companies list", "Korean corporate hierarchy culture",
        "Working hours in South Korea", "Minimum wage Korea 2026", "Paid vacation days Korea", "Maternity leave policy Korean law", "Unemployment benefit foreign workers",
        "Industrial accident insurance Korea", "Tax tax return expats Korea", "Housing allowance corporate benefit", "Business card etiquette Korea", "Company dinner Hoesik survival",
        "Smart casual dress code Seoul", "Commuting in Seoul rush hour", "English job boards South Korea", "Headhunters in Seoul for expats", "Tech stacks popular Korean startups",
        "Kakao Line Coupang recruitment", "Samsung Hyundai LG global hiring", "K-pop agency global career", "Gaming company jobs Seoul English", "EPIK program application guide",
        "Hagwon teacher working conditions", "International school jobs Korea", "University job openings Seoul", "Freelance visa criteria South Korea", "Sole proprietorship registration Korea",
        "Tax incentive foreign engineers", "Korean workplace slang terms", "Asking for promotion Korean firm", "Resignation notice period Korea", "Wrongful dismissal remedy labor",
        "Whistleblower protection workplace Korea", "Trade union membership foreigners", "Employment contract review checklist", "Probation period regulations Korea", "Part time job hourly wage",
        "Seoul global center job service", "Foreign chamber of commerce Seoul", "AmCham EUCCK job listings", "Embassy career opportunities Seoul", "Expat professional communities",
        "Incentive bonus structure Korea", "Flexible working hours system", "Four major social insurances", "Retirement age regulation Korea", "Workplace bullying prevention law",
        "English speaking hr department", "Relocation package Korea guide", "Expat networking group meetup", "Executive search firm Gangnam", "Entry level jobs Seoul foreign",
        "Mid career transition Korea", "IT certification value Korean market", "Mechanical engineering jobs Korea", "Chemical industry recruitment Seoul", "Construction management jobs expat"
    ],
    "keywords_jobkoreaglobal.txt": [
        "Global talent recruitment Korea", "Multinational companies in Seoul", "Cross border recruitment Asia", "Remote jobs from Korea global", "Expat executive positions Seoul",
        "Intercultural communication workplace", "English as official business language", "Global mobility specialist Korea", "Foreign investment companies hiring", "Outsourcing developer team Korea",
        "Global tech talent acquisition", "International business development Seoul", "Strategic partnership manager Korea", "Global supply chain expert recruitment", "Cross cultural management training",
        "Bilingual recruiter career Seoul", "Headhunting global tech stars", "Relocation consultant Seoul career", "International law firm expat attorney", "Global marketing director Seoul",
        "E-commerce global expansion specialist", "Fintech startup global compliance", "Crypto exchange international hiring", "Venture capital associate Seoul", "Global PR agency career Seoul",
        "Overseas sales manager recruitment", "Localization specialist English native", "Foreign trade analyst Seoul", "Global logistics coordinator Korea", "Multilingual data analyst",
        "AI research global recruitment", "SaaS sales professional Seoul", "Cloud architect jobs Korea English", "Cybersecurity expert global firm", "ESG compliance officer Korea",
        "Global medical coordinator job", "International student job fair", "KOTRA global talent matching", "Seoul invest employment program", "Foreign startup accelerator manager",
        "Global non profit management", "International organization career Seoul", "Bilingual project manager tech", "Global content strategist K-beauty", "K-pop global marketing specialist",
        "International shipping specialist Busan", "Global procurement officer Incheon", "Expat package negotiation tips", "Double taxation treaty expat worker", "Global payroll system compliance",
        "Remote HR manager global team", "Diversity and inclusion workplace", "Global talent visa parameters", "International school principal hiring", "Global consulting firm analyst",
        "Cross border tax consultant", "Global intellectual property lawyer", "English technical writer job", "Global customer success manager", "International event coordinator Seoul"
    ],
    "keywords_kstudy365.txt": [
        "Learn Korean language fast", "Best Korean language academy", "Sogang vs Yonsei Korean program", "TOPIK test preparation strategy", "Korean alphabet Hangul master",
        "Online Korean language course", "Korean vocabulary hacks daily", "Speaking Korean fluently tips", "Korean grammar intermediate guide", "Free Korean learning apps",
        "Korean language exchange Seoul", "Study Korean in Busan academy", "Intensive Korean language summer", "Korean slang words dictionary", "Business Korean phrases useful",
        "TOPIK 2 writing section tips", "Korean pronunciation guide audio", "Shadowing technique learning Korean", "Korean immersion program reviews", "University language institute cost",
        "KGSP Korean language year", "TOPIK mock test online", "Korean particles master guide", "Honorifics system in Korean", "Ewha Korean textbook review",
        "Seoul national university language", "K-pop lyrics learn Korean", "K-drama expressions everyday use", "Korean listening practice beginner", "Read Korean book translated",
        "Korean webtoon for language study", "Learn Korean with YouTube", "Korean typing practice speed", "Exchange student Korean course", "TOPIK level 4 requirements",
        "Korean numbers counting system", "Sino Korean vs Native Korean", "Korean verbs conjugation chart", "Common mistakes learning Korean", "Self study Korean roadmap",
        "Korean vocabulary flashcards app", "Private Korean tutor Seoul price", "Language school visa D4", "D4 visa to D2 visa change", "Working part time D4 visa",
        "Korean culture via language", "Idiomatic expressions in Korean", "TOPIK level 5 vocabulary", "Korean dictation practice audio", "Children learning Korean materials",
        "Korean corporate terminology prep", "Street language Seoul guide", "Satoori regional dialects Korea", "Busan dialect useful phrases", "Jeju dialect unique words",
        "Korean language certificate value", "TOPIK registration process dates", "Computer based TOPIK test", "Best dictionary app Korean", "Learn Hangul in one hour"
    ],
    "keywords_studyinkorea.com": [
        "Global Korea Scholarship GKS", "Apply to Seoul National University", "SKY universities admission international", "Tuition fees in South Korea", "D2 student visa application",
        "English track degree programs Korea", "KAIST scholarship international students", "Yonsei University Underwood College", "Korea University global admission", "Study abroad in Seoul guide",
        "Exchange student life in Korea", "University dormitory vs Goshiwon", "Cost of living student Seoul", "Part time job rules student", "Post graduate job prospects Korea",
        "English speaking university professor", "GKS undergraduate application guide", "GKS graduate requirements deadline", "Admission essay Korean university", "Recommendation letter university Korea",
        "Apostille diploma verification Korea", "English proficiency test IELTS university", "Korean university ranking 2026", "Study engineering in South Korea", "MBA programs in Seoul English",
        "International relations degree Korea", "K-beauty fashion design school", "Korean Government scholarship benefits", "Student health insurance mandatory", "Alien registration card student",
        "Opening bank account student Korea", "Student discount benefit card", "Hanyang university international program", "Sungkyunkwan university admission global", "Busan national university expat",
        "Ewha womans university global", "Sogang university international track", "Chung Ang university media program", "Kyung Hee university tourism hospitality", "Top tech universities South Korea",
        "Student internship during semester", "Working hours limit student visa", "D2 visa extension documents", "Graduating university job search D10", "Korean university festival culture",
        "Student clubs for foreigners university", "Mental health support international student", "Cheap eats near Seoul universities", "Best university neighborhood student", "Goshiwon booking tips foreigners",
        "One room rental contract student", "Korean roommate cultural adjustment", "Studying in Korea without TOPIK", "GKS interview preparation questions", "Korean university academic calendar",
        "Credit transfer system international", "Summer school program Seoul", "Winter camp Korean university", "Online admission portal Jinhak", "Visa issuance number student"
    ],
    "keywords_kfinance.txt": [
        "Korean economy growth forecast", "Bank of Korea monetary policy", "Investing in KOSPI guide", "Top Korean tech stocks", "Samsung electronics financial report",
        "Won to Dollar exchange trend", "Opening bank account Korea expat", "Best credit card for foreigners", "Digital banking apps Kakao Toss", "Foreign direct investment Korea",
        "Real estate market trends Seoul", "Jeonse system financial analysis", "Korean corporate tax rate", "Income tax bracket South Korea", "Foreign exchange regulation Korea",
        "KOSDAQ market investment strategy", "Korean bonds yield overview", "Fintech industry regulation Seoul", "Crypto market tax policy Korea", "Personal financial management expat",
        "Inflation rate South Korea 2026", "Consumer spending habits Korea", "Household debt analysis South Korea", "Korean stock market trading hours", "Foreigners buying property Seoul",
        "Mortgage loan options South Korea", "National tax service english guide", "Year end tax settlement expat", "Double taxation agreement criteria", "Remittance money from Korea overseas",
        "Best savings account rate Korea", "Korean financial supervisory service", "Stock dividend yield top firms", "ETF investment strategy KOSPI", "Corporate governance reform Korea",
        "K-battery industry stock trends", "Semiconductor market financial cycle", "Automotive export data valuation", "Defense industry financial growth", "E-commerce market size revenue",
        "Korean venture capital funding", "Angel investor network Seoul", "Startup funding stages Korea", "Green finance policy South Korea", "Carbon credit trading market",
        "Financial tech sandbox program", "Open banking system South Korea", "Mobile payment trends Samsung Pay", "Credit score system for foreigners", "Getting personal loan expat Korea",
        "Withholding tax rate foreign worker", "Inheritance tax regulation Korea", "Gift tax exemption parameters", "Corporate investment incentives Korea", "Free economic zone financial tax",
        "Seoul international financial center", "Busan finance hub development", "Korean economic history brief", "Export credit agency funding", "Public pension fund management KIC"
    ],
    "keywords_kinvest.txt": [
        "KOSPI day trading strategy", "Undervalued Korean stocks list", "K-pop entertainment stocks buy", "EV battery supply chain invest", "AI semiconductor chips KOSPI",
        "Foreign institutional investor trend", "Retail investors ant movement", "Short selling regulation South Korea", "Dividend aristocrats Korean market", "IPO calendar Seoul exchange",
        "SK Hynix stock valuation", "LG Energy Solution financial outlook", "Naver vs Kakao stock analysis", "Hyundai Motor global sales stock", "Bio biosimilar stocks KOSDAQ",
        "Defense sector investment booming", "Shipbuilding turnaround stock cycle", "Korean ETF tracking technology", "Leverage inverse ETF KOSPI", "Market capitalization ranking top",
        "KOSPI 200 index rebalancing", "Foreigner net buying sector", "Stock trading app English Korea", "Opening brokerage account expat", "Capital gains tax stock Korea",
        "Financial statement reading guide", "Price to earnings ratio KOSPI", "Corporate value up program", "Shareholder return policy Korea", "Stock split history top firms",
        "Venture investment KOSDAQ list", "Tech startup equity crowdfunding", "Real estate investment trust REITs", "Seoul apartment price investment", "Commercial property market Gangnam",
        "Jeonse gap investment risk", "Building yield calculation Seoul", "Foreigner land ownership law", "Crypto asset investment pattern", "Bitcoin regulation premium premium",
        "Ethereum staging Korean exchanges", "Alternative investment infrastructure fund", "Gold trading market South Korea", "Commodity market investment overview", "Treasury bonds auction schedule",
        "Corporate bond credit rating", "Interest rate swap market", "Foreign portfolio investment limits", "Investment advisory firm Seoul", "Wealth management service expat",
        "Robo advisor platform South Korea", "Sustainable investing ESG factors", "Renewable energy stock portfolio", "Aviation marine stock recovery", "Webtoon anime production stock",
        "K-food export boom investment", "Medical device manufacturer stock", "Global macro impact KOSPI", "US interest rate impact won", "Investment risk mitigation strategies"
    ],
    "keywords_ktax.txt": [
        "Korean income tax guide expat", "Global income tax reporting Korea", "Tax residence status criteria", "Year end tax adjustment checklist", "Foreign code tax deduction",
        "Tax standard deduction single", "Dependent exemption qualification tax", "Medical expense tax credit", "Education fee tax deduction expat", "Donation tax credit parameters",
        "Housing rent tax deduction Korea", "Credit card spending tax deduction", "Flat tax rate option foreign", "Executive tax benefit corporate", "Corporate income tax rate return",
        "Transfer pricing documentation rules", "Permanent establishment tax trigger", "Controlled foreign corporation tax", "Withholding tax double treaty", "VAT refund system tourists",
        "Value added tax rate business", "Tax invoice system Home Tax", "Customs duty import tariff", "Duty free allowance Incheon airport", "Gift tax rate threshold family",
        "Inheritance tax property calculation", "Real estate holding tax종부세", "Property acquisition tax rate", "Capital gains tax real estate", "Stock transfer tax capital gains",
        "Securities transaction tax rate", "Crypto tax implementation plan", "Digital service tax discussion", "Tax audit process corporate Korea", "Tax dispute resolution system",
        "National tax service contact center", "HomeTax website usage English", "Local income tax calculation", "Automobile tax rate criteria", "Stamp duty transaction contract",
        "Tax incentive R&D investment", "Startup tax holiday qualification", "Free economic zone tax reduction", "Foreign investor tax exemption", "Social security contribution vs tax",
        "National pension tax deductibility", "Health insurance premium tax", "Employment insurance contribution rate", "Double taxation relief credit", "Foreign tax credit calculation",
        "Tax evasion penalties fine", "Voluntary disclosure program tax", "Tax advisor fee Seoul certified", "English speaking tax accountant", "Tax reporting deadline calendar",
        "Liquor tax tobacco tax structure", "Leisure tax local tax item", "Registration and license tax", "Inheritance tax reform proposal", "Corporate restructuring tax impact"
    ],
    "keywords_ktrip.txt": [
        "Seoul itinerary 3 days first time", "Best time to visit South Korea", "Jeju island road trip itinerary", "Busan travel guide top attractions", "Gyeongju historical sites checklist",
        "Hidden gem cafes in Seoul", "Myeongdong street food price", "Hongdae nightlife clubbing guide", "Itaewon rooftop bar view", "Gangnam shopping underground mall",
        "Nami island day tour spring", "Seoraksan national park hiking autumn", "Bukhansan peak trail map", "Han river park bike rental", "Cherry blossom forecast Korea 2026",
        "Autumn foliage calendar spots", "Ski resort near Seoul winter", "Jejudo beach emerald water", "Haeundae beach Busan guide", "Gamcheon culture village photo spot",
        "Traditional Hanok village Jeonju", "Andong mask dance festival", "DMZ tour safe booking portal", "Incheon airport transit tour", "KTX high speed train booking",
        "Arex express train airport", "Seoul subway app english navigate", "Kakao taxi app international card", "Luggage delivery service airport hotel", "Best luxury hotel in Seoul",
        "Affordable hostel Hongdae student", "AirBnb regulations South Korea", "Traditional market vs department store", "Lotte World vs Everland theme park", "Coex aquarium starfield library",
        "Seoul palace pass entry fee", "Changdeokgung secret garden tour", "Bukchon Hanok village etiquette", "Insadong traditional souvenir item", "Dongdaemun design plaza exhibition",
        "Yeouido park Hyundai Seoul mall", "Suwon Hwaseong fortress day trip", "Incheon Chinatown food tour", "Gangneung beach coffee street", "Sokcho seafood market guide",
        "Tongyeong cable car luge", "Yeosu night sea romantic view", "Suncheon bay wetland reserve", "Boseong green tea field ice cream", "Namhae island scenic driving",
        "Ulleungdo island ferry schedule", "Dokdo island travel permit", "Korea travel simulation card", "Esim data plan comparison Korea", "Emergency contact numbers travel"
    ],
    "keywords_kvisa.txt": [
        "Korea tourist visa C3 criteria", "K-ETA application guide countries", "E7 visa sponsorship requirement", "D2 student visa documents checklist", "D4 language trainee visa process",
        "D10 job seeker visa points", "F27 points based resident visa", "F5 permanent residency criteria South", "F6 marriage visa document timeline", "Working holiday visa H1 parameter",
        "H2 working visa ethnic Koreans", "F4 visa privileges registration", "OASIS startup visa points system", "Corporate investor visa D8", "Trade visa D9 management",
        "Digital nomad visa Korea requirements", "K-culture training visa upcoming", "Visa extension application online", "Hi Korea portal account setup", "Immigration office reservation tip",
        "Alien registration card ARC processing", "Change of workplace immigration notice", "Part time job permission student", "Illegal stay amnesty program", "Deportation grounds visa violation",
        "Visa re entry permit regulations", "Invitation letter format immigration", "Financial proof visa threshold", "Criminal record check apostille visa", "Health medical certificate visa",
        "F299 visa long term resident", "F5 Permanent residency English test", "KIIP Korean immigration integration program", "KIIP level 5 test prep", "Visa status check online result",
        "Seoul immigration office location", "Incheon airport immigration process", "Automatic border control smart entry", "Visa agency service Seoul fee", "English speaking immigration lawyer",
        "D10 visa extension justification", "E7 visa salary minimum criteria", "E2 conversational English teacher visa", "E1 professor visa qualification", "F1 family visit visa extension",
        "F3 dependent visa employment limit", "Visa sponsorship cancellation remedy", "Refusal of visa appeal options", "Overstaying visa fine calculation", "Passport validity requirement visa",
        "G1 humanitarian visa conditions", "D7 intra company transfer visa", "D2 visa to E7 visa transition", "E7 visa job categories list", "Immigration call center 1345 tips",
        "Expedited visa processing condition", "Lost ARC card replacement process", "Updating passport information immigration", "Visa free entry transit rules", "Biometric registration immigration Korea"
    ],
    "keywords_kcrypto.txt": [
        "Upbit vs Bithumb trading volume", "Korean crypto tax policy law", "Kimchi premium indicator live", "Coinone listing criteria token", "Korbit exchange review fee",
        "Digital asset basic act Korea", "Crypto investor protection regulation", "Bitcoin price premium Seoul", "Ethereum staking yield platform", "Ripple XRP popularity Korea",
        "Top altcoins traded by Koreans", "Crypto exchange real name account", "Bank verification crypto trading", "Travel rule VerifyVASP CODE", "DeFi adoption trend South Korea",
        "NFT market K-pop entertainment", "Web3 gaming tokenomics Korea", "Metaverse token listing KOSDAQ", "Crypto deposit insurance framework", "Cold wallet security advice Korea",
        "Crypto hacking incident response unit", "FSS crypto market monitoring", "Staking service regulation FSC", "Token security offering STO framework", "Real world asset RWA tokenization",
        "CBDC pilot program Bank of Korea", "Digital won architecture model", "Crypto whale wallet tracking Korea", "Day trading crypto strategy Upbit", "Crypto trading bot regulation",
        "Initial exchange offering IEO status", "Crypto venture capital Seoul", "Blockchain hub Busan special zone", "BIFC blockchain infrastructure project", "Crypto meetup community Seoul",
        "Ethereum Seoul developer conference", "Smart contract audit firm Korea", "Solana ecosystem growth Korea", "Layer 2 scaling solution adoption", "Stablecoin volume Korean premium",
        "OTC crypto desk Seoul corporate", "Crypto asset management expat", "Bitcoin ETF discussion South Korea", "Meme coin trading volume frenzy", "Loss recovery crypto scam legal",
        "Crypto tax return reporting form", "Corporate crypto holding regulation", "DAO legal status South Korea", "Zero knowledge proof project Korea", "Decentralized identity DID project",
        "Crypto mining profitability electricity", "Hardware wallet distributor Seoul", "Crypto market sentiment index", "P2E game ban status Korea", "GameFi development studio Seoul",
        "Crypto venture funding seed round", "Arbitrage opportunity Kimchi premium", "Crypto compliance officer career", "Blockchain patent registration Korea", "Future of digital assets Asia"
    ],
    "keywords_kinsurance.txt": [
        "Korean national health insurance NHI", "Foreigner mandatory health insurance cost", "Silbi private indemnity insurance review", "Best cancer insurance policy Korea",
        "Driver insurance coverage mandatory option", "Auto insurance calculation comparison Korea", "Travel insurance incoming tourists Korea", "Life insurance expat coverage criteria",
        "Variable life insurance investment product", "Annuity pension insurance tax benefit", "Samsung Fire Marine insurance profile", "Hyundai Marine Fire corporate policy",
        "DB Insurance coverage assessment", "KB Insurance English customer support", "Foreign worker accident insurance mandatory", "Return of premium insurance feature",
        "Insurance claim document checklist app", "Mobile app insurance payout speed", "Pre existing condition insurance sign", "Medical checkup impact insurance premium",
        "Dental insurance coverage scaling implant", "Child insurance Children policy Korea", "F6 visa spouse insurance enrollment", "D2 student health insurance reduction",
        "E7 visa employee insurance package", "Four major social insurance breakdown", "Employment insurance unemployment safety", "Industrial accident compensation insurance benefit",
        "National pension expat totalization agreement", "Lump sum refund national pension", "Insurance fraud detection unit Korea", "Financial supervisory service insurance complaint",
        "Insurance premium tax deduction year", "Corporate liability insurance Korea", "Director and officer liability insurance", "Marine cargo insurance shipping Busan",
        "Product liability insurance manufacturer Korea", "Group health insurance corporate benefit", "Retirement pension insurance IRP account", "Term life vs whole life",
        "Guaranteed asset protection insurance auto", "Fire insurance commercial property Seoul", "Casualty insurance market size growth", "Reinsurance company Korean Re profile",
        "Insurance agent commission structure", "Online digital only insurance platform", "Kakao Pay insurance product review", "AI automated insurance underwriting",
        "Insurance policy loan interest rate", "Surrender charge life insurance contract", "Expat insurance broker Seoul English", "Claims adjuster assessment process",
        "Medical negligence insurance doctor", "Pet insurance coverage cost vet", "Golfers insurance third party liability", "Windstorm flood insurance national program",
        "Long term care insurance senior", "Inheritance tax mitigation via insurance", "Keyman insurance small business Korea", "Insurance clause dynamic reading tips"
    ],
    "keywords_kwedding.txt": [
        "Korea wedding hall cost packages", "Gangnam luxury wedding venue booking", "Studio dress makeup Sudme package", "Korean pre wedding photoshoot concept",
        "Jeju island outdoor bridal shoot", "Traditional Korean wedding ceremony Pyebaek", "Hanbok for bride and groom", "Wedding invitation card custom design",
        "Korean wedding guest outfit etiquette", "Wedding cash gift money amount", "Buffet vs steak wedding catering", "Hotel wedding Seoul pricing structure",
        "Outdoor garden wedding venue Korea", "Small wedding minimalist trend Seoul", "Church cathedral wedding ceremony criteria", "Wedding planner agency Seoul cost",
        "Bridal shower party hotel package", "Groom tuxedo rental tailor shop", "Wedding makeup salon Cheongdamdong", "Bridal gown designer shop review",
        "Korean wedding tradition cash white", "Congratulatory money envelope writing format", "Wedding MC host script program", "Parent formal attire Hanbok mom",
        "Honeymoon destination trend Koreans", "Marriage registration document international couple", "F6 spouse visa wedding certificate", "Pre nuptial agreement legal status",
        "Wedding ring jewelry brand Cheongdam", "Proposal event company Seoul cost", "Engagement ceremony family meeting Sanggyeonrye", "Dowry and wedding gifts Yedan",
        "New marital home deposit trends", "Housewarming party Jipdeori gift item", "Korean wedding photography snapshot editing", "Flower decoration pricing wedding hall",
        "Musical wedding performance singer option", "Destination wedding Jeju planning agency", "Traditional wedding performance Samulnori", "Intercultural marriage ceremony challenges Korea",
        "Wedding anniversary celebration culture Korea", "Vow renewal ceremony venue Seoul", "Second marriage trends wedding market", "Eco friendly wedding sustainable venue",
        "Hanok courtyard wedding venue cost", "Weekday evening wedding discount benefit", "Wedding expo Seoul registration date", "Catering tasting session bridal review",
        "Bridal bouquet custom flower trend", "Wedding videography cinematic editing firm", "After party venue rental Itaewon", "Pre marriage counseling program center",
        "Bride waiting room interior setup", "Mobile wedding invitation link creation", "Wedding return gift 답례품 item", "Joint wedding expense division guide",
        "Micro wedding package boutique hotel", "Celebrity wedding venue trend analysis", "Average age of marriage Korea", "Wedding budget checklist excel calculator"
    ],
    "keywords_ktech.txt": [
        "Samsung Galaxy flagship review 2026", "SK Hynix HBM memory tech", "Naver HyperCLOVA AI advancement", "Kakao mobility autonomous driving taxi", "LG rollable display technology commercial",
        "South Korea 6G network roadmap", "Quantum computing research institute Seoul", "K-battery solid state technology breakthrough", "Hyundai humanoid robot factory implementation",
        "AI chip design fabless startup", "Cybersecurity threat report government agency", "Smart city Songdo infrastructure data", "Korean aerospace satellite launch status",
        "K-defense stealth drone tech", "Shipbuilding automation smart shipyard container", "Fintech open API sandbox results", "Biotech CRISPR gene editing Korea",
        "Hydrogen fuel cell passenger car", "Eco friendly plastic recycling technology", "Korean independent web browser platform", "E-commerce logistics automated sorting system",
        "Coupang delivery drone testing path", "Webtoon production AI assist tool", "K-pop virtual idol technology engine", "Metaverse platform Zepeto technical evolution",
        "Digital twin city modeling Seoul", "Medical AI diagnostic software review", "Wearable health tracker Korean venture", "Smart farm vertical agriculture automation",
        "Nuclear fusion reactor KSTAR milestone", "Small modular reactor SMR development", "Korean supercomputer specifications computing speed", "Superconductor research update laboratory",
        "Graphene commercialization electronic component factory", "Flexible battery wearable electronic device", "OLED vs MicroLED Korean manufacturing", "Automotive sensor lidar radar tech",
        "V2X vehicle to everything network", "Smart home IoT appliance integration", "Voice recognition processor dialect handling", "Blockchain voting system national testing",
        "DeFi protocol safety verification framework", "NFT ticketing counterfeit protection system", "Cloud infrastructure data center Seoul", "SaaS startup business enterprise solution",
        "Developer salary trend Pangyo valley", "Tech incubator campus startup funding", "Tech transfer university industry collaboration", "Patent filing numbers global ranking",
        "Government R&D budget allocation tech", "Data privacy law compliance tech", "Green tech carbon capture plant", "Robotic surgery system local alternative",
        "3D bio printing tissue engineering", "Exoskeleton suit industry worker safety", "Drone defense jamming system airport", "Autonomous shipping cargo vessel sea",
        "Smart grid renewable energy storage", "Pangyo techno valley mapping expansion", "Korean tech exhibition World IT Show"
    ],
    "keywords_kworld.txt": [
        "BTS comeback album tracklist rumors", "Blackpink member solo project schedule", "NewJeans global fashion brand ambassador", "Top K-pop entertainment companies ranking",
        "K-pop global audition trainee criteria", "Korean drama ratings chart weekly", "Netflix original K-drama production lineup", "Cannes film festival Korean director",
        "K-movie box office record breaker", "Webtoon original drama adaptation list", "K-pop concert world tour ticketing", "Fandom culture voting app voting",
        "Lightstick custom design technical features", "MAMA awards winner prediction category", "Melon music chart algorithm change", "K-indie music scene festival Hongdae",
        "Korean hip hop hiphopplaya lineup", "K-pop dance choreography tutorial center", "Virtual K-pop group member analysis", "K-variety show global popularity recipe",
        "Squid Game new season analysis", "Korean actor brand reputation index", "Cheongdamdong celebrity hair salon list", "K-pop idol airport fashion style",
        "Photocard collecting market price trend", "K-pop merch pop up store", "Weverse platform communication feature review", "K-pop vocal trainer training technique",
        "Korean trainee strict daily routine", "Music broadcast pre recording access", "Hallyu wave economic impact report", "K-pop concept storytelling universe building",
        "Music video production studio Korea", "Korean background composer sound score", "Idol athletic championship broadcast schedule", "Busking culture Sinchon fashion street",
        "K-pop album sales unboxing review", "Korean agency global fan club", "K-drama OST chart topping melody", "Historical drama Sageuk filming set",
        "Korean theatre scene original musical", "Nanta cooking show performance ticket", "K-pop lyricist songwriting process insights", "Idol debut showcase streaming link",
        "Korean web novel premium translation", "K-pop backup dancer career opportunities", "Entertainment lawyer contract dispute Korea", "Idol mental health welfare policy",
        "K-entertainment streaming platform comparison OTT", "釜산 international film festival program", "Jeonju indie film selection review", "Korean animation studio global co-production",
        "K-pop festival calendar worldwide locations", "Fan-led subway advertisement cost guide", "K-pop jargon dictionary fan terms", "Korean celebrity endorsement contract fee",
        "Retro K-pop vinyl record shop", "Korean traditional music crossover band", "K-drama fashion icon outfit match", "Pop culture museum Seoul archive"
    ],
    "keywords_oliveyoung.txt": [
        "Olive Young global shipping speed", "Best K-beauty toner pads review", "Olive Young awards winner skincare", "Torriden low molecular hyaluronic acid",
        "Anua heartleaf toner soothing effect", "Beauty of Joseon ginseng sunscreen", "Round Lab birch juice moisturizer", "Skin1004 madagascar centella ampoule",
        "Cosrx snail mucin essence sale", "Manyo factory cleansing oil blackhead", "Mediheal sheet mask line comparison", "Unleashia glitter eyeshadow palette swatch",
        "Romand juicy lasting tint color", "Peripera ink velvet lip tint", "Clio kill cover cushion foundation", "Wakemake water blurring tint review",
        "Abib heartleaf spot pad evaluation", "Goodal green tangerine vitamin C", "Isntree hyaluronic acid watery sun", "Illiyoon ceramide ato concentrate cream",
        "Aestura atobarrier 365 cream verification", "Some By Mi AHA BHA", "Numbuzin serum line numbering choice", "Dr.G clear soothing cream acne",
        "Bring Green tea tree toner", "Olive Young hair care top", "Daleaf scalp scaling shampoo review", "Grow Gorgeous hair loss serum",
        "Healux body acne wash treatment", "Olive Young inner beauty supplement", "Teazen kombucha flavors review benefit", "Lacto-Fit probiotics yellow tube option",
        "bbia last auto gel eyeliner", "Dasique pro eyeshadow palette pastel", "Espoir pro tailor be velvet", "Banila Co clean it zero",
        "Heimish all clean balm sensitive", "I'm From honey mask wash", "Skinfood black sugar mask wash", "Axis-Y dark spot correcting serum",
        "Mixsoon bean essence texture method", "Haruharu wonder black rice toner", "Purito centella unscented serum brand", "Pyunkang Yul moisture cream minimal",
        "VT cosmetics reedle shot intensity", "Reedle shot 100 300 comparison", "Olive Young coupon code global", "Myeongdong Olive Young flagship store",
        "Korean pore pack nose strip", "Hydrogel pimple patch master list", "Olive Young sale period calendar", "Trending body mist K-beauty store",
        "Korean makeup sponge puff recommendation", "Too Cool For School shading", "Kat Maconie cushion review K-beauty", "Jumbo size toner bargain buy",
        "Olive Young travel kit essentials", "Men skincare set ranking Olive", "Lip plumper tint review K-beauty", "Olive Young shopping vlog item"
    ],
    "keywords_seouljournal.txt": [
        "Seoul lifestyle trends expat perspective", "Han river park luxury picnic", "Seongsu dong hipster cafe street", "Apgujeong Rodeo fashion boutique retail",
        "Seoul rental market officetel studio", "Expat cost of living Seoul", "Best neighborhood in Seoul live", "Seoul co working space digital",
        "English friendly gym gym Seoul", "Vegan restaurants in Seoul option", "Seoul specialty coffee roastery tour", "Vintage clothing market Dongmyo shopping",
        "Seoul public bike Ttareungyi guide", "Hanok restoration architecture interior trend", "Seoul independent bookstore curated english", "Yeonnam dong residential park walk",
        "Seoul contemporary art gallery map", "Hannam dong fine dining restaurant", "Seoul craft beer brewery taproom", "Itaewon global grocery store list",
        "Seoul city wall trail sunset", "Night photography spots in Seoul", "Seoul fashion week designer street", "Fleamarket calendar schedule Seoul square",
        "Seoul zero waste shop eco", "Han river kayaking water sport", "Indoor climbing gym Seoul center", "Pilates studio English speaker Gangnam",
        "Seoul international church services group", "Language exchange cafe Sinchon review", "Seoul pet friendly cafe terrace", "Gourmet supermarket food hall review",
        "Seoul jazz club live performance", "Independent theater indie cinema Seoul", "Seoul subculture fashion brand list", "Expat parent international school guide",
        "Seoul public library english archive", "Han river swimming pool summer", "Seoul ice skating rink winter", "Traditional tea ceremony workshop Bukchon",
        "Seoul cooking class market tour", "Perfume flagship store Seongsu design", "Seoul interior design supply market", "Expat health insurance clinic mapping",
        "Seoul cycling route Han river", "Urban camping spot suburban Seoul", "Seoul historical walk hidden alley", "Myeongdong alternative shopping spots local",
        "Seoul subway station art exhibition", "Han river fountain show schedule", "Seoul startup incubator hub community", "Expat professional meetup network calendar",
        "Seoul weekend getaway train ride", "Local market grocery price comparison", "Seoul street art mural village", "Korean design stationery shop tour",
        "Seoul luxury spa treatment review", "Traditional public bathhouse Jimjilbang rule", "Seoul seasonal packing guide checklist", "Seoul future urban planning layout"
    ]
}

def build_keyword_files():
    print(f"📂 [키워드 매니저] 한 달 치 자동 구축 가동 (총 {len(KEYWORDS_DB)}개 파일)")
    current_dir = os.path.dirname(os.path.abspath(__file__)) if __file__ else "."
    created_count = 0
    for filename, keywords in KEYWORDS_DB.items():
        file_path = os.path.join(current_dir, filename)
        unique_keywords = list(dict.fromkeys(keywords))
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for kw in unique_keywords:
                    f.write(f"{kw}\n")
            print(f"  └ ✅ 생성 완료: {filename} ({len(unique_keywords)}개)")
            created_count += 1
        except Exception as e:
            print(f"  └ ❌ 생성 실패 ({filename}): {str(e)}")
    print(f"🎯 총 {created_count}개 파일 생성 완료!")

if __name__ == "__main__":
    build_keyword_files()
