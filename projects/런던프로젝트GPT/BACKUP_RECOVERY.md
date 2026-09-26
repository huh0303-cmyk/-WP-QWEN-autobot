# 런던프로젝트GPT — Backup / Recovery Plan

## 1. Source backup
Authority: GitHub main branch.
Every material phase must be committed.

Protected categories:
- architecture docs
- registry/config
- n8n workflow JSON
- deployment workflows
- systemd unit files
- local-agent source
- migration/rollback notes

## 2. VPS runtime backup
Back up:
- /opt/korea365 code checkout
- /opt/korea365/data/n8n
- n8n SQLite/config data
- relevant queue/receipt state
- systemd unit definitions
- non-secret runtime manifests

Do not commit secrets.

## 3. Secret backup
Secrets remain outside repository:
- /etc/korea365/*
- GitHub Actions Secrets
- local authenticated browser profile

Recovery documentation stores only secret **names and locations**, never values.

## 4. n8n recovery
If n8n container fails:
1. verify Docker
2. verify /etc/korea365/n8n.env exists
3. verify /opt/korea365/data/n8n ownership
4. docker compose up -d
5. health check
6. import versioned workflow JSON if required
7. verify gateway health
8. do not enable old schedulers unless n8n cannot be restored

## 5. Git rollback
Every risky migration requires a known-good commit SHA.
Rollback:
- fetch main
- checkout/revert to known-good commit
- redeploy
- verify health and receipt
- record rollback reason

## 6. LocalAgent recovery
If Windows/Aside session is lost:
1. stop local queue consumption
2. preserve pending jobs
3. restore/install LondonLocalAgent
4. user logs into Naver/Tistory
5. verify one canary
6. resume queue

Never resend stale failed jobs before current jobs without review.

## 7. Disaster scenarios

### VPS unavailable
- GitHub state remains durable.
- local browser jobs HOLD.
- do not move whole system to PC automatically.
- restore VPS or replacement VPS from repository + secret inventory.

### GitHub unavailable
- running VPS continues from deployed version.
- no destructive migration until GitHub returns.

### n8n unavailable
- proven workers remain installed.
- emergency manual/systemd execution is allowed only as documented recovery mode.
- no duplicate schedulers.

### AI provider quota exhausted
- existing prepared queues may continue if policy-approved.
- new generation stops or fails over according to allowed provider policy.
- publication evidence remains independent from AI availability.

## 8. Recovery success
Recovery is complete only after:
- service health OK
- one canary execution
- exact receipt
- dashboard reflects state
