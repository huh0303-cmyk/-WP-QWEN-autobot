# 런던프로젝트GPT — Workflow Authority

## Master workflow rule
Use a small registry-driven master set.
Do not create one workflow per destination.

## Required masters

### 1. WP25_MASTER
Scope: 25 ordinary WordPress sites.
Input: site registry + due state.
Execution: existing authenticated VPS WordPress worker.
Success: exact destination + post ID + public URL.
Failure: site-level isolation only.

### 2. BLOGGER33_MASTER
Scope: 33 Blogspot properties.
Execution: existing Blogger publisher.
Success: exact blog + post ID + URL.
One failed blog must not stop the other 32.

### 3. NEWS2_MASTER
Scope: The Seoul Journal + Koreanews365.
Separate rules from normal WordPress.
Only verified source-based stories.
No fabricated filler to hit quota.

### 4. TISTORY5_MASTER
n8n only creates/queues a job.
Final browser write is performed by LondonLocalAgent.
Login/captcha => HOLD.
Success: public URL.

### 5. NAVER3_MASTER
Same architecture as Tistory.
Separate local browser profiles per account.
Success: public URL.

### 6. YOUTUBE_PLAYLIST5_MASTER
n8n selects due channel.
VPS generates/render/uploads.
Default upload state: PRIVATE until explicit approval if review-gated.
Success: video_id + channel_id + privacyStatus.

### 7. YOUTUBE_KNOWLEDGE5_MASTER
Topic → source check → script → TTS/assets → render → private upload → receipt.

### 8. YOUTUBE_LANGUAGE_MASTER
Registry driven.
Never hard-code a stale fixed channel count.
Only channels with verified channel IDs may be enabled.

### 9. SNS_MASTER
Platform-aware transformation.
Do not paste identical content across every SNS.
Only verified connected accounts are enabled.

### 10. METRICS_MASTER
Collect:
- previous-day daily visitors + delta
- cumulative visitors + delta
- total public posts + delta
- Google indexed public posts + delta

Dashboard ordering:
1위, 2위, 3위... based on previous-day daily visitor metric.

## Scheduling policy
- KST authority.
- avoid exact-hour repetitive patterns unless a strict operational task needs one.
- minimum same-platform gap where practical.
- no unnecessary high-frequency polling.
- state changes should be event/receipt driven where possible.

## Migration rule
Old production path remains only until the replacement master has one verified end-to-end receipt.
After verification:
1. disable old scheduler
2. observe one cycle
3. delete old scheduler/workflow
4. preserve rollback commit
