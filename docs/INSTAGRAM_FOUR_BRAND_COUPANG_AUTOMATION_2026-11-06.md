# Four-brand Instagram automation policy — 2026-11-06

## Scope
Daily automation covers only @english_pick1, @japanese_survival1, @seoul_jisoo, and @seoul_chris1. Seoul TOPIK (@sis_topik1) is explicitly excluded; do not modify its content, credentials, schedules, or workflows.

## Coupang Partners is the highest-priority requirement
- Use only product-specific tracking URLs actually generated in the owner's authenticated Coupang Partners account and stored in an approved catalog.
- Never invent, reconstruct, shorten, or rewrite tracking URLs. Never substitute a generic Coupang URL.
- Require product ID, title, category, exact affiliate URL, and verified status before selecting a product.
- If no relevant verified product exists, block the affiliate placement and report the missing catalog item; do not claim success.
- Include this disclosure: 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.

## Instagram link behavior
Do not assume URLs in captions are clickable. Put the exact tracking URL in the profile link hub and use Stories link stickers for individual products. Reels/carousels direct viewers to the profile link. Verify the destination retains the original tracking URL.

## Editorial roles
- English Pick: beginner English, 3 progressive expressions daily, native audio repeated 5 times per expression.
- Japanese Speak: beginner Japanese, 3 progressive expressions daily, native audio repeated 5 times per expression.
- Seoul Jisoo: Korean beauty, fashion, shopping, lifestyle products and timely consumer trends.
- Seoul Chris: Korean current affairs, sports, entertainment and social topics; add products only when genuinely relevant.

## Audio
Priority: synced repository audio assets; verified public HTTPS assets; approved free TTS. A GitHub-hosted runner cannot read files on an offline PC. Sync local audio into repository assets or host it publicly over HTTPS. Never publish silent or placeholder audio.

## Credentials and publish gate
Use separate Meta credentials per account, stored only as GitHub Actions secrets. Never reuse another brand's token. If credentials, a public media URL, or a verified product tracking URL are missing, mark the run BLOCKED and do not publish.

## Evidence
A successful Actions run is not proof of a public post. Record product IDs, exact tracking URLs, disclosure check, Meta container ID, media ID and permalink. Distinguish PREPARED, BLOCKED, PUBLISHED and VERIFIED.
