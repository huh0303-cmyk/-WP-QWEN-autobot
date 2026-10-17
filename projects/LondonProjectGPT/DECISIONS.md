# 런던프로젝트GPT Decisions

## 2026-09-26
- GPT, Claude and Gemini tracks are completely separate.
- Each track makes its own architecture/implementation decisions and owns its own results.
- Shared production facts may be read, but implementation decisions must not be copied across tracks without owner approval.
- GitHub main is the continuity source; each track writes under its own project directory.
- GPT architecture: app-first control plane, existing engines reused behind it.
- GitHub and VPS run 24/7 workloads.
- Human login is reserved for platforms that actually require it.
- Naver/Tistory: owner login when needed, then session reuse; no repeated credential entry.
- Completion requires Verify stage and saved receipt.
- Never mark login-only, code-only, or queued-only work as complete.


## 2026-09-27 YouTube canonical identity rule
- Exact production identity is the triple: current channel title + current @handle + exact UC channel ID.
- Google/Brand account selection labels such as Studio_K3, Chinese Survival, K-ISSUE, K-RELAX, Spanish Survival, Arabic Survival, and *_TIMES names are selector/history aliases only.
- Never route uploads by legacy selector label alone.
- `config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json` supersedes old 10-channel-only and legacy archive mappings for LondonProjectGPT routing.


## 2026-10-17 YouTube upload target hard lock — misroute cShePd9rQvY
- Video `cShePd9rQvY` must be repaired by uploading its original source to `HISTORY_TV_TODAY` channel ID `UCVBvZwodUF4s57KeNicxQ3w`.
- Never identify an upload target from legacy OAuth/brand-selector names such as `AMERICAN_ARCHIVE_TIMES`; always compare the OAuth-authenticated UC channel ID with the canonical lock before upload.
- A video cannot be transferred across YouTube channels by changing metadata. Re-upload to the correct channel, verify via API, and retain the wrong private copy until replacement verification. No automatic deletion.
- Tracking document: `docs/YOUTUBE_MISROUTE_REPAIR_cShePd9rQvY_2026-10-17.md`.
