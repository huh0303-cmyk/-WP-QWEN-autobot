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
