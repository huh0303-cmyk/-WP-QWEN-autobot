# CONTROL SNS live reconciliation — 2026-10-01 04:45 KST

Task ID: control-sns-live-20261001. User requested Instagram, Threads and Facebook counts and the complete roster on control.korea365.org.

## Verified live state

- Deployment: GitHub Actions run 36767708437 succeeded; VPS /opt/korea365 is at 0a0a9da8006aaaec0ad737e6137051e6dce5fdec, deploy-status.json says deployed at 2026-10-01 04:44 KST.
- Browser inspection of https://control.korea365.org/ at 04:45 KST: Instagram 4 rows, Threads 4 rows, Facebook 6 rows. https://sns.korea365.org/social-accounts?platform=SNS shows the same. These are displayed account/role rows, not proof that each can publish.
- Instagram four daily roles: Seoul TOPIK @sis_topik1; English Survival @englishsurvival1; Japanese Survival @japanese_survival1; Seoul Jisoo shopping @seoul_jisoo. The latter handle was saved in Meta, but its display name still needs user Facebook password reauthentication.
- Threads four daily roles: Seoul TOPIK @seoultopik; English Survival @english_survival_1; Japanese Survival (actual Threads account and handle unconfirmed); Seoul Jisoo shopping (policy still records @seoul_item365; current @seoul_jisoo Threads handle unverified). None of these four should be treated as fully API authorized based on the roster alone.
- Facebook six role rows: 서울국제대학 SIS - TOPIK Center (prior post receipt, current VPS page ID/token absent); 서울국제대학 SIS-ENGLISH Center (name observed, page ID/write permission unverified); 서울국제대학교 SIS - Language Center (name observed, page ID/write permission unverified); Seoul Health365 Shop, Seoul Travel365 Shop, Seoul Hot Items365 Shop (three planned pages, account existence unverified).
- TikTok remains six role rows, with mixed verification. YouTube shows 24 rows because provisional Jisoo2 is counted despite missing UC ID and a 404 handle; 23 confirmed channels remain the authoritative active inventory. Correct the display distinction separately; do not call Jisoo2 verified.

## Deployment recovery and next actions

The prior VPS deploy attempts were deferred as waiting_for_video because one orphaned YouTube queue running marker, vps-1790793906-5185e3f4e0, remained after the worker was idle. After checking age, no lock holder, no job log and no dashboard job, the marker was moved reversibly to failed under an exclusive queue lock. The recovery receipt is /opt/korea365/data/youtube_vps_queue/logs/vps-1790793906-5185e3f4e0.stale-recovery.json. No upload or queue dispatch was made. The following deployment succeeded (run 36767708437).

Next: complete the pending Meta display-name reauthentication, verify the two unresolved Threads identities and platform write access, identify Facebook page IDs and tokens for the existing pages, create/verify the three planned shopping pages only if separately authorized, and remove the provisional Jisoo2 row from active YouTube counts or present it explicitly as unconfirmed.