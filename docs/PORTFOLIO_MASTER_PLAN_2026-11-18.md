# London Project — Portfolio Master Plan (2026-11-18)
Status: APPROVED DESIGN / NOT YET IMPLEMENTED. Owner-approved conversation decisions. Do not interpret as live site changes.
Repository inventory reconciliation required: 22 named sites/services listed below, not 23 distinct domains. Never fabricate missing site.
## Portfolio register
| Site | Positioning | Categories / navigation | Exceptions |
|---|---|---|---|
| Kworld365.com | English global K-POP news | Comebacks & New Releases; K-POP Artists & Groups; Concerts & World Tours; Charts & Music Awards; K-POP Industry News | **5 approved categories** |
| Kfinance365.com | Foreigners' Korea finance | Banking & Savings; Loans & Credit; Remittance & Exchange; Personal Finance & Policy | Minimize commerce |
| KoreaInvest365.com | Korea stocks, ETFs, bonds and strategies | Korean Stocks; ETFs & Funds; Bonds & Fixed Income; Investment Strategies | Verify financial claims |
| KoreaCrypto365.com | Korean and global crypto | Korean Crypto Market; Bitcoin & Major Coins; Exchanges & Regulation; Blockchain & Investment Guides | Verify financial claims |
| KoreaInsurance365.com | Insurance for foreigners in Korea | Health & Medical; Auto & Transportation; Travel; Other Insurance | Consultation CTA; compliance |
| KoreaTaxnLaw | Tax and law for foreigners | Korean Tax; Immigration & Legal Rights; Business & Employment Law; Legal Guides | Legal verification |
| K-visa365.com | Visa and immigration information | Visa Types; Applications & Extensions; Residency & Immigration; Visa Policy & Guides | REST 403 historically; verify |
| StudyinKorea365.com | Information media for foreign students | Universities & Admissions; Scholarships & Tuition; TOPIK & Korean Language; Student Life | Not an application portal |
| JobinKorea365.com | Employment information for foreigners in Korea | Job Industries; Visas & Employment Law; Salaries & Conditions; Job Search Guides | Information site |
| JobKorea365.com | Actual recruitment and online application platform | Industry/occupation navigation (hospitality, restaurants, electronics, manufacturing, construction, IT, logistics, healthcare etc.) | Employer/salary/location/visa/deadline/housing fields; Apply Online, CV upload, application status |
| Krealestate365.com | Korean real estate for foreigners | Renting; Buying; Housing Laws; Market & Living Guides | Verify property claims |
| KoreaWedding365.com | **Real** language/culture exchange club | Korean Language Exchange; Korean Culture & Lifestyle; Community Events & Activities; Relationships & Cross-Cultural Communication | Genuine club; marriage matching separately subject to legal review, never disguise regulated matchmaking |
| KoreaMedicalTour.com | Medical travel information + hospital consultation | Plastic Surgery & Aesthetics; Health Checkups & Clinics; Hospitals & Medical Services; Medical Travel & Patient Guide | Patient referral/solicitation requires legal registration assessment; medical privacy |
| Kskin365.com | K-Beauty keyword, skincare-led editorial and affiliate | K-Beauty Skincare; Skin Concerns & Solutions; K-Beauty Ingredients; K-Beauty Products & Reviews | Coupang affiliate contextual recommendations |
| OliveYoungKorea.com | K-Beauty product discovery and affiliate shopping | K-Beauty Skincare; Korean Makeup & Cosmetics; Hair, Body & Personal Care; K-Beauty Deals & Shopping Guides | Independent site; no unverified official affiliation or trademark misuse |
| K-trip365.com | English Korea travel information and booking affiliate | Korea Destinations & Attractions; Korean Food & Culture; Hotels, Transport & Travel Tips; Korea Tours & Experiences | Five-image homepage slider; three-column cards; approved Trip.com/Booking links |
| KoreaNews365.com | Korean-language political breaking-news newspaper | 정치·국회; 정치 속보·쟁점; 사회·경제; 국제·스포츠 | Politics ~70% editorial target; newspaper header; no ads; breaking news exempt from article length; verify and attribute claims |
| Korea365.org | Global network central hub | Study, Work & Visa; Finance, Law & Living; Travel, Culture & Lifestyle; Health, Beauty & Shopping | Link to originals, don't syndicate duplicate articles; integrated search and service routing |
| K-health365.com | **Korean-language**, only user-reported AdSense-approved site; health + K-Beauty/K-Health sales | 건강·질병 예방; 영양·건강식품; K-뷰티·피부관리; K-헬스·건강용품 | **NO mass rewrite of old posts**, preserve URLs, rankings, AdSense configuration; new Korean articles; Coupang 5 beauty+5 health cards |
| JobKoreaGlobal.com | English Korean employment guidance for people abroad | Korea Jobs & Industries; Work Visa & Employment Rules; Salary & Working Conditions; Job Application & Career Guide | Operate now; compare with JobinKorea365/JobKorea365 at year-end |
| KStudy365.com | Actual foreign-student Korean university application platform | Find Universities; Admissions & Scholarships; Apply Online; My Applications | Student/university/admin accounts, document upload, status tracking, privacy, institutional authority; distinct from StudyinKorea365 |
| SeoulMall | Affiliate shopping hub (no own inventory/shipping) | K-Beauty & Skincare; K-Health & Wellness; Korean Lifestyle & Home; Best Deals & Trending Products | Link from other editorial sites; validate availability, shipping country, affiliate disclosures |
## Cross-site rules
- Before any change: inventory real domains and WordPress data, take database/media backup, preserve current publishing code and URLs.
- Except K-health365 and KoreaNews365 exceptions, audit all existing articles: reclassify, fix missing/broken/duplicate images and ALT, unique titles, inaccurate/outdated facts, short posts, internal links, SEO, 2,500–4,000 chars, H1/H2/H3, FAQ, short paragraphs, color-accent formatting.
- Images: Pexels/Pixabay randomized first, SDXL Turbo then FLUX Schnell fallback, hero/body distinct, 14-day URL/hash/file reuse prevention; do not count image-less posts as fully compliant.
- Article engine: language-specific Gemini fallback, one article per WordPress site/day at non-round randomized times; verify post ID and public URL, never equate workflow success with publication. Check OAuth, API, media, retry and recovery.
- Affiliate cards: contextual products in article and 10 footer cards (5 K-Beauty + 5 K-Health, refresh weekly), except finance/law/insurance/investment where commerce minimized, KoreaNews365 where ads removed. Use actual approved affiliate URLs, disclosure, product availability and geographic shipping accuracy.
- K-health365 preserve AdSense approval and current configuration, protect existing content; selective safety/error fixes only, no bulk rewrites.
- No site automatically merged or removed. **Every site** evaluated at end of 2026: traffic, search, revenue, quality, duplication, publishing reliability. Compare three employment sites especially for possible retention, merger with 301 redirects, or retirement after review.
- Specialized platforms: JobKorea365 job application and KStudy365 university application require role-based access, secure uploads, privacy controls, institution/employer verification. Legal clearance before marriage matchmaking or patient referral operations.
## Implementation phases (NOT COMPLETED)
1. Reconcile exact sites and backups.
2. Commit/version-control specifications and per-site rules.
3. Audit and repair content; K-health365 exception.
4. Build affiliate links and application functions after rights/compliance checks.
5. Restore publishing and verify IDs/URLs.
6. Year-end evaluation of every site.
## Verification checklist
[ ] Actual categories configured
[ ] Existing articles reclassified and improved
[ ] Images and ALT verified
[ ] SEO/internal/affiliate links verified
[ ] New automated post published and verified
[ ] Real public URL and post ID captured
[ ] Control dashboard synchronized
## Next phase
**Blogspot/Blogger portfolio (reported 31 blogs)**: inventory first, then site-by-site editorial classification, content audit, publishing verification, index tracking. This file covers WordPress/service decisions; do not mistake it for Blogger implementation.
