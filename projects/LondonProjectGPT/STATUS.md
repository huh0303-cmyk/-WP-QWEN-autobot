# 런던프로젝트GPT Status

Last update: 2026-09-26 KST

## Done
- Claude Code authentication repaired on owner PC.
- Aside CLI installed and callable.
- LondonProjectGPT owner lock committed.
- /london-gpt app shell created and deployed to control.korea365.org.
- Existing control-room credentials and deployment path reused.

## In progress
- Convert app shell into true operations console with queue/retry/receipt state.
- Make Naver/Tistory local-login sessions explicit runtime resources.
- Surface GitHub/VPS/n8n worker health in one screen.
- Reconcile YouTube inventory to full 23-channel target.

## Next
1. Add durable job/receipt model.
2. Add browser-session status for Naver 3 / Tistory 5.
3. Add YouTube 23 inventory cards.
4. Add SNS authorization/readiness cards.
5. Add bounded retry + HOLD state and verified-publication completion gate.


## 2026-09-27 YouTube identity reconciliation
- Cross-checked owner-provided legacy account-selector mapping, owner channel/handle list, current YouTube account-switcher screenshot, existing GitHub locks, and live public @handle pages.
- Created canonical 23-channel lock: `config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json`.
- Resolved exact UC IDs for Chinese, Vietnamese, and Portuguese Survival.
- Survival 10/10 now have exact UC channel IDs.
- Current 23-target = playlist 5 + knowledge 5 + language 10 + health 2 + shopping 1.
- Legacy science/classical/myth/american_archive/classic_reads keys are retained only as historical aliases and excluded from the current 23 production target.
