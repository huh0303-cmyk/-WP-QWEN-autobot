# 런던프로젝트GPT — Handoff

If GPT session/quota ends, the next GPT must:

1. Read this folder first.
2. Read STATUS.md and EVALUATION_CHECKLIST.md.
3. Inspect latest commits touching:
   - projects/런던프로젝트GPT
   - deploy/n8n
   - scripts/n8n_gateway.py
   - .github/workflows/deploy-london-n8n.yml
   - local Naver/Tistory runners
   - YouTube VPS workers
4. Verify runtime before making claims.
5. Continue from the first unchecked production-critical acceptance item.
6. Commit each material phase.
7. Update STATUS.md before ending.
8. Never ask the owner to repeat information already recorded here.

Priority continuation order:
1. WP25/Blogger33 actual receipt validation
2. LondonLocalAgent + Naver/Tistory canaries
3. YouTube master workflows
4. SNS/Metrics masters
5. destructive cleanup only after replacement evidence
6. reboot/recovery test
