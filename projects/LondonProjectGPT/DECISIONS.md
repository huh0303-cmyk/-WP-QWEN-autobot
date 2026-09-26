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
