# 런던프로젝트클로드 운영 잠금

- 공식 명칭: 런던프로젝트클로드
- 총괄 운영자: Claude (이 트랙 한정)
- Chairman 직접 지시(2026-09-26, 18:41 KST): "다 별도야.. 런던프로젝트클로드는
  온전히 너꺼고 너가 책임자고 책임도 너가 진다." — 이 트랙의 판단·점검·실행·
  검증·보고 책임은 Claude가 진다.

## 다른 트랙과의 관계

같은 저장소에 병행 운영되는 "런던프로젝트GPT"(ChatGPT 총괄,
`config/LONDON_PROJECT_GPT_OWNER_LOCK_2026-09-26.md`)와는 **완전히 별도
트랙**이다. 상호 지휘·위임 관계 없음. 서로의 범위를 침범하지 않는다.

- 런던프로젝트GPT 선언 범위: WordPress 25, 신문사 2, Blogspot 33, Tistory 5,
  Naver 3, YouTube/SNS 및 Control Korea365 연동 자동화 전체.
- **런던프로젝트클로드 범위는 의도적으로 좁게 유지한다** (아래 참고) —
  선언 범위가 넓게 겹치더라도, 실제로 손대는 파일은 좁게 유지해서 같은 파일을
  동시에 고치는 충돌을 최소화한다.

## 런던프로젝트클로드 실제 범위

`docs/LONDON_PROJECT_CLAUDE_CHARTER.md` 기준:
- 1차 목표: 구글 애드센스 승인 (현재 k-health365.com 1개, 나머지 24개 WP)
- 소유 파일(우선 관리 대상): `scripts/audit_adsense_sites.py`,
  `scripts/ensure_required_pages.py`, `.github/workflows/ensure-required-pages.yml`,
  `.github/workflows/adsense-infrastructure-audit.yml`,
  `config/survival_language_channels.json`(유튜브 채널 신원 확인 지원),
  `docs/LONDON_PROJECT_CLAUDE_CHARTER.md`, `docs/LONDON_PROJECT_CLAUDE_STATE.md`,
  이 파일.
- 이 목록 밖의 파일(다른 트랙이 최근에 만졌거나 만들 가능성이 있는 파일)을
  고칠 때는 먼저 `git log --oneline -5 -- <path>`로 최근 변경 이력을 확인하고,
  다른 트랙이 만든 것이면 겹치는 작업을 하지 않고 STATE 문서에 그 사실만
  기록한다.

## 운영 원칙 (런던프로젝트GPT 락 파일과 동일한 기준 적용)

- 모호하거나 충돌하는 요구사항이 있으면 추측하지 않고 즉시 사용자에게 확인한다.
- 진행률은 설치 여부가 아니라 실제 작동 여부와 발행/검증 결과를 기준으로
  보고한다.
- "완료" 표기는 실제 검증까지 끝난 경우에만 사용한다 — VERIFIED_COMPLETE는
  Deterministic Audit Engine만 선언 가능 (`CLAUDE.md` 기존 원칙 유지).
- 핵심 KPI: 애드센스 승인 사이트 수, 안정적 실제 발행, 트래픽 증가.
