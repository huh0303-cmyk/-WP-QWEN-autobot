# London Project — owner-approved unified image source policy (2026-11-10)
Status: policy specification only; NOT yet wired into every production workflow.

## Global general-content image order (strict)
1. Pexels OR Pixabay — find relevant cleared stock images, with attribution/license/usage metadata and cross-channel dedup.
2. SDXL Lightning — only if stock sources unavailable or relevant assets rejected.
3. FLUX.1 Schnell — only if SDXL Lightning unavailable or rejected.
4. SDXL Turbo — final free-generation fallback.

Applicable by default to all WordPress and Blogspot properties and general information, health and education content. No paid image API or GPU charges without separate approval. A model's open weights do not guarantee free hosted inference. No unrelated or duplicated image to satisfy a mandatory-image rule.

Music/healing channels: preserve the owner's approved high-performing visual samples and channel-specific motion/storyboard requirements. Apply shared asset provenance and dedup checks to newly acquired imagery; do not replace the reference-led visual treatment with a generic template.

## Strict exceptions
SEOUL_JOURNAL political Shorts and SEOUL_JISOO political Shorts:
- NO Pexels, Pixabay or synthetic politician portraits.
- Source only authentic person/event footage and photographs with verified reuse permission.
- Candidate sources: Parliament/National Assembly TV, public agency and politician official releases, cleared Commons, licensed footage library.
- Do not assume all National Assembly TV content is public domain. Verify exact asset, reuse terms, attribution and third-party rights, including embedded broadcast/music/audio.
- Original speech audio may be retained only where permitted, with timestamps and transcript; never edit into misleading out-of-context clashes.
- Extract claim, opponent response, verified context and viewer poll; captions aligned with spoken words.
- Fail closed on uncertain rights, wrong person, unverified quotation or missing footage.

SEOUL_JISOO shopping Shorts:
- NO generic Pexels/Pixabay stock product substitutes.
- Use genuine product photography/footage supplied by seller, brand, affiliate program or owned assets with appropriate permission.
- Do not imply AI depictions are authentic products; check claims and disclosures.

## QA and traceability
Persist provider, asset ID, source URL, creator, rights basis, download time, exact SHA256 and perceptual hash.
Check within-video duplicates, recent channel reuse and cross-platform reuse; avoid repeated first-result stock photos.
Fail only the affected job on rights/identity/fact errors; continue independent jobs.
Never silently use a generic image or public-post unreviewed political material.

## Implementation checklist
- Inventory active workflow entrypoints and remove conflicting provider ordering after tests.
- Implement one shared image source router with explicit channel/content type policies.
- Add regression tests for all four general fallbacks and both special exceptions.
- Validate free quotas and configured keys without printing secrets.
- Pilot on a WP site, a Blogger site, Health Clinic and a political Short; then rollout in batches.
- Verify publication receipts; a commit alone is not deployment or a successful upload.
