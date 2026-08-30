# Blogger Description & SEO Setup — 2026-08-30

Scope: all 26 channels in `config/blogger_portfolio.json` **except order 7
(koreamedicaltour.com)**, which stays excluded pending its address conflict.

## Why this is manual, not automated

Blogger API v3 exposes the `Blogs` resource as **read-only** (`get`,
`getByUrl`, `list`, `listByUser` — no `update`/`patch`). Blog-level
Description and Search preferences have never been writable through the
API, only through the Blogger web UI. That is true for the 13 already-
connected (`EXISTING`) blogs and the 1 newly created (`CREATED`) one just
as much as for the 12 `SCHEDULED` ones. So every row below needs a human to
paste it into Blogger's settings screen once.

Source text: original WordPress site domains are unreachable from this
session's network policy (egress blocked to all non-allowlisted domains,
blogspot.com included), so these descriptions are written from each
channel's locked `topic`/title in `config/blogger_portfolio.json`, in a
warm, plain-language, SEO-friendly voice. If you have the live WP tagline
text and want an exact match instead, send it over and these get revised.

## Per-blog checklist (do this for every row)

1. **Settings → Basic → Description** — paste the `Description` column.
2. **Settings → Basic → Privacy → "Let search engines find your blog"** →
   **ON**. (Critical — off means Google never indexes it, regardless of
   everything else below.)
3. **Settings → Search preferences → Meta tags → Enable search
   description** → **Yes**, paste the `Search description` column.
4. **Settings → Search preferences → Errors and redirects** — leave
   default unless a custom 404 is specifically needed.
5. Add required pages: **About, Contact, Privacy Policy, Disclaimer**.
6. Register the blog in **Google Search Console** and submit
   `https://<blog>.blogspot.com/sitemap.xml`.
7. On the first post, use the blog's core keyword (see `Topic` column) as
   a **Label** — Blogger's label archive pages help indexing.

## All 26 blogs

| # | Blogspot address | Status | Lang | Topic | Description (Basic → Description) | Search description (Meta tag) |
|---|---|---|---|---|---|---|
| 1 | k-trip365.blogspot.com | EXISTING | en | Korea travel | Friendly, practical guides to traveling in Korea — itineraries, hidden gems, transportation tips, and seasonal highlights for first-time visitors and repeat travelers alike. | Practical Korea travel guides: itineraries, hidden gems, transport tips, and seasonal highlights for every traveler. |
| 2 | kworld365.blogspot.com | SCHEDULED 08:17 | en | K-pop | Your friendly companion for K-pop news, artist spotlights, comeback updates, and fan culture — written for global fans who want to stay close to Korean pop music. | K-pop news, artist spotlights, and comeback updates for global fans of Korean pop music and culture. |
| 3 | jobkorea365.blogspot.com | EXISTING | en | Jobs and careers in Korea | A welcoming guide to jobs and careers in Korea — hiring trends, resume tips, workplace culture, and practical advice for anyone building a career here. | Jobs and career advice for Korea: hiring trends, resume tips, and workplace culture, explained simply. |
| 4 | kstudy365.blogspot.com | EXISTING | en | Studying in Korea | Helpful, friendly guidance for studying in Korea — university admissions, scholarships, student visas, and everyday campus life tips for international students. | Studying in Korea made simple: admissions, scholarships, visas, and campus life tips. |
| 5 | koreainsurance365.blogspot.com | EXISTING | en | Insurance in Korea | Clear, friendly explanations of insurance in Korea — health coverage, national pension basics, and practical comparisons to help you choose with confidence. | Insurance in Korea explained simply: health coverage, national pension basics, and practical comparisons. |
| 6 | kfinance365.blogspot.com | EXISTING | en | Personal finance in Korea | Friendly, practical personal finance guidance for life in Korea — banking, saving, taxes, and everyday money tips for residents and newcomers alike. | Personal finance in Korea: banking, saving, taxes, and everyday money tips for residents and newcomers. |
| 8 | k-visa365.blogspot.com | EXISTING | en | Korean visas and immigration | A friendly, step-by-step resource for Korean visas and immigration — application requirements, renewal tips, and practical advice for a smoother process. | Korean visa and immigration guidance: requirements, renewal tips, and practical advice, explained clearly. |
| 9 | koreanews365.blogspot.com | SCHEDULED 09:06 | **ko** | 한국 뉴스·시사 | 한국의 주요 뉴스와 시사 이슈를 알기 쉽고 친절하게 정리해서 전해드리는 블로그입니다. 바쁜 일상 속에서도 핵심을 빠르게 확인하실 수 있어요. | 한국 뉴스와 시사 이슈를 쉽고 친절하게 정리해서 전해드립니다. |
| 10 | koreainvest365.blogspot.com | EXISTING | en | Investing and business in Korea | Friendly, practical insights on investing and business in Korea — market trends, company spotlights, and everyday guidance for curious investors. | Investing and business in Korea explained: market trends, company spotlights, and practical guidance. |
| 11 | oliveyoungkorea.blogspot.com | SCHEDULED 10:21 | en | K-beauty products and shopping | A friendly guide to K-beauty products and shopping in Korea — honest reviews, must-try picks, and shopping tips for skincare and cosmetics lovers everywhere. | K-beauty product reviews and shopping tips: must-try skincare and cosmetics picks from Korea. |
| 12 | koreacrypto365.blogspot.com | SCHEDULED 11:09 | en | Korean digital assets and regulation | Clear, friendly coverage of Korean digital assets and regulation — market updates, policy explainers, and practical guidance for crypto users in Korea. | Korean crypto and digital asset news: market updates, regulation explainers, and practical guidance. |
| 13 | jobinkorea365.blogspot.com | EXISTING | en | Foreign worker job guidance | A supportive, friendly resource for foreign workers in Korea — visa-linked job guidance, workplace rights, and practical tips for building a career here. | Job guidance for foreign workers in Korea: visa-linked advice, workplace rights, and practical tips. |
| 14 | koreawedding365.blogspot.com | SCHEDULED 12:38 | en | Korean weddings and international couples | A warm, friendly guide to Korean weddings and international couples — traditions, planning tips, and paperwork basics for a smooth, joyful celebration. | Korean wedding guide for international couples: traditions, planning tips, and paperwork basics. |
| 15 | theseouljournal.blogspot.com | SCHEDULED 13:27 | en | English-language Korea news and analysis | Friendly, English-language news and analysis on Korea — politics, society, and culture explained clearly for readers who want the full picture. | English-language Korea news and analysis: politics, society, and culture explained clearly. |
| 16 | ktech365.blogspot.com | SCHEDULED 14:44 | en | Korean technology and innovation | A friendly look at Korean technology and innovation — startups, gadgets, and industry trends explained in plain language for curious readers. | Korean tech and innovation news: startups, gadgets, and industry trends explained simply. |
| 17 | kieca-korea.blogspot.com | SCHEDULED 15:31 | en | International education and cultural exchange | A welcoming resource on international education and cultural exchange in Korea — programs, opportunities, and practical guidance for global learners. | International education and cultural exchange in Korea: programs and practical guidance for global learners. |
| 18 | ki-korea.blogspot.com | SCHEDULED 16:58 | en | Korea-focused international cooperation | Friendly insights on Korea-focused international cooperation — partnerships, programs, and practical updates for a global audience. | Korea-focused international cooperation: partnerships, programs, and practical updates explained clearly. |
| 19 | ksa-korea.blogspot.com | SCHEDULED 17:46 | en | Korea study networks and student support | A supportive guide to Korea study networks and student support — community resources, practical tips, and friendly advice for students far from home. | Korea study networks and student support: community resources and practical tips for international students. |
| 20 | koreataxnlaw.blogspot.com | EXISTING | en | Korean tax and practical law | Clear, friendly explanations of Korean tax and practical law — everyday legal questions answered simply, without the confusing jargon. | Korean tax and law explained simply: everyday legal questions answered without the jargon. |
| 21 | jobkoreaglobal.blogspot.com | EXISTING | en | Global careers connected to Korea | A friendly guide to global careers connected to Korea — international hiring trends, remote work, and practical advice for a borderless career. | Global careers connected to Korea: hiring trends, remote work, and practical career advice. |
| 22 | studyinkorea365.blogspot.com | EXISTING | en | Admissions and student life | Friendly, practical guidance on studying in Korea — admissions steps, scholarships, and everyday student life tips for international students. | Study in Korea guide: admissions steps, scholarships, and student life tips, explained simply. |
| 23 | korea365.blogspot.com | SCHEDULED 18:53 | en | Public-interest Korea information | A friendly, public-interest resource on life in Korea — practical information and everyday guidance written to be genuinely useful. | Public-interest Korea information: practical, everyday guidance written to be genuinely useful. |
| 24 | sis-korea.blogspot.com | SCHEDULED 19:41 | en | Seoul International University and global education | A welcoming guide to Seoul International University and global education in Korea — admissions, programs, and campus life for international students. | Seoul International University and global education in Korea: admissions, programs, and campus life. |
| 25 | krealestate365.blogspot.com | EXISTING | en | Housing and property in Korea | Friendly, practical guidance on housing and property in Korea — rental basics, buying tips, and market trends explained in plain language. | Housing and property in Korea explained: rental basics, buying tips, and market trends. |
| 26 | k-health365.blogspot.com | EXISTING | **ko** | 건강·영양·생활습관 | 건강, 영양, 생활습관에 관한 정보를 친절하고 이해하기 쉽게 전해드리는 블로그입니다. 일상에서 바로 실천할 수 있는 팁을 담았습니다. | 건강·영양·생활습관 정보를 친절하고 쉽게 전해드립니다. |
| 27 | kskin365.blogspot.com | CREATED | en | Korean skincare | A friendly guide to Korean skincare — ingredient explainers, routine tips, and honest product insights for healthier, happier skin. | Korean skincare guide: ingredient explainers, routine tips, and honest product insights. |

## Excluded

- **koreamedicaltour.com** (order 7) — blogspot address unresolved
  (`koreamedicaltour.blogspot.com` availability unconfirmed;
  `koreamedicaltour365.blogspot.com` is a different asset and must not be
  substituted). Revisit once the address is confirmed.
