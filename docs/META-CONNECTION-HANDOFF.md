# Instagram / Threads connection handoff
Verified 2026-09-24 KST. User authorized connection and persistent storage. Content-specific final approval remains mandatory before public posting.

## Intended accounts (must verify authenticated IDs)
Instagram: sis_topik1, seoul_item365 (Rosie Picks), seoul_life365, seoul_health365.
Threads: seoul_item365, seoul_life365, seoul_health365. Do not infer account IDs from these handles or old display names.

## Actual state
No Instagram, Threads or Facebook credentials found in the VPS control.env/article-runtime.json/youtube-runtime.json stores inspected. Windsor Instagram supports direct Instagram authorization or Facebook authorization. Both opened flows currently show logged-out login screens. User login requested; no successful Meta connection or new token is claimed.
Windsor exposes Threads via /app/threads and Grant Threads Access. Threads requires its own authorization; Instagram connection does not prove Threads access.
Windsor trial currently has 15/15 selected accounts used by YouTube and ends 2026-10-23. Do not remove existing YouTube coverage or purchase a plan without addressing this constraint. Connecting Meta credentials alone does not guarantee additional collection slots.

## Resume
Reuse saved browser session and the current login popup, then verify every real account ID with a read-only profile/insights response. Store secrets outside GitHub with restrictive permissions. Commit only code and sanitized verification records. Never report connected based solely on an OAuth screen. Do not publish test posts.
