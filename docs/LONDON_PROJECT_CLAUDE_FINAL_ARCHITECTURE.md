# 런던프로젝트클로드 — 최종 아키텍처 / 워크플로우 / 백업플랜 / 운영설명서

작성: Claude Sonnet 5, 2026-09-26 19:37 KST 지시로 작성.
목적: Chairman이 "런던프로젝트클로드" 트랙을 평가할 때 쓰는 단일 참조 문서.
이 문서는 **주장이 아니라 이 세션에서 실제로 실행하고 확인한 증거**만 담는다.
추측·계획을 사실처럼 쓰지 않고 "확인됨" / "미확인" / "계획(미실행)"을 구분한다.

---

## 0. 한 줄 요약

- **아키텍처 선택: GitHub(기록) + VPS(24/7 실행) + n8n(오케스트레이션), self-hosted, 신규 유료 SaaS 없음.**
- **EXE/로컬 앱(복사장류)은 채택하지 않음** — 이유는 3절.
- 완성률은 항목별로 다름 (1절). 단일 %로 뭉뚱그리면 왜곡되므로 항목별로 제시.

---

## 1. 완성률 (정직한 항목별 평가, 2026-09-26 19:40 KST 기준)

| 영역 | 상태 | 완성률(추정) | 근거 |
|---|---|---:|---|
| 1차 목표: 애드센스 승인 (24개 WP) | **미완료** | 승인 1/25 (k-health365.com만) | Chairman 직접 확인 |
| 원인 진단: ads.txt/DNS | 완료·원인 아님으로 결론 | 100% | run 36233819256, 27/27 FAIL 0건 |
| 원인 진단: 필수 페이지(4종) | 부분 완료 | 12/24 확인(원인 아님), 12개 미확인 | run 36233910201, WAF 추정 차단 |
| 원인 진단: 콘텐츠 품질(크로스사이트 템플릿화) | **발견만 함, 원인 스크립트 미특정, 미수정** | ~20% | STATE.md (5차) 항목, 실제 글 4건 열람 확인 |
| 종합상황실 4개 지표 대시보드 (일일/누적 방문자, 총 글 수, 구글색인, 순위) | GSC 크래시는 고침(검증됨) / 순위+4지표 통합 UI는 **런던프로젝트GPT 트랙이 오늘 커밋(`eb1ab43`,`d7051f5`) — 나는 아직 실제 화면으로 검증 안 함** | 크래시 수정 100%, UI 통합 미검증 | run 36235591140 27/27 성공; 대시보드 UI는 diff만 확인, 브라우저 검증 안 함 |
| n8n 기반(VPS 배포) | **오늘 배포 성공 확인(내가 이 턴에 직접 GitHub Actions 로그로 검증)** | Phase 1(기반) 완료, Phase 2 이후(실제 발행 파이프라인 연결) 미착수 | run 36234584029 = completed/success (그 전 4번은 실패 후 수정) |
| 10개국어 서바이벌 YouTube | 계획대로 보류 중 (2/50 레슨, 별도 승인 전 자동 스케줄 안 함) | 4% (2/50) | 지시대로 잠금 유지, 신규 작업 없음 |
| GitHub 내구성 기록 (STATE/CHARTER/OWNER_LOCK/HANDOFF) | 완료, 매 세션 갱신 중 | 100% (지속 유지 필요) | 이 세션의 커밋들 |

**결론**: "런던프로젝트클로드" 트랙(QA/감사 역할) 자체의 이번 세션 작업은 실행됐고 실측 검증도 했지만,
**사업의 진짜 목표인 "24개 사이트 애드센스 승인"은 원인의 상당 부분(콘텐츠 템플릿화 후보)만
발견한 단계이며 아직 해결/재승인 신청까지 가지 않았다.** 승인 자체 기준으로 보면 여전히 초기 단계다.

---

## 2. 다른 트랙 현황 (내가 직접 확인한 것만)

### 런던프로젝트제미나이 (Gemini)
`projects/LONDON_PROJECT_GEMINI/STATUS.md` 원문(2026-09-26 KST 갱신):
> "Current phase: independent track not yet implemented in this repository.
> Gemini browser access exists, but no verified Gemini CLI was found on the PC at last check."

**즉 제미나이는 아직 구현을 시작하지 않은 상태다.** "다 끝냈냐"는 질문에 대한 답: 아니다, 시작 전이다.
(내가 지어낸 게 아니라 그 트랙이 스스로 남긴 상태 파일을 그대로 인용한 것.)

### 런던프로젝트GPT (ChatGPT/CODEX)
오늘(09-26) 짧은 시간에 다음을 실제로 커밋/실행한 흔적이 확인됨:
- `docs/N8N_LONDON_PROJECT_MIGRATION_2026-09-26.md` — n8n 중심 마이그레이션 계획 문서화.
- n8n을 VPS에 실제로 배포 (`.github/workflows/deploy-london-n8n.yml`) — 4번 실패 후 5번째 성공
  (run 36234584029, completed/success — 내가 이 턴에 GitHub API로 직접 조회해 확인).
- 종합상황실 4개 지표+순위 통합 커밋 2건 (`d7051f5`, `eb1ab43`).
- `docs/GPT_CONTINUITY_HANDOFF_2026-09-25.md`에 스스로 "완료로 주장하지 않는 것" 명시 (TikTok/Instagram/
  Facebook/Threads 11개 슬롯 계정 미확보, SNS 공개 발행 아직 비활성).

**평가**: GPT 트랙은 이번 세션 동안 실제로 실행 결과를 남겼고, 실패-수정-재시도 로그가 그대로 GitHub에
남아 있어 검증 가능하다. 다만 n8n은 "기반 배포 성공"이지 "실제 발행 파이프라인이 n8n을 통해 돈다"는
아직 아니다(migration 문서 자체가 Phase 2 이후를 "미착수"로 구분해 놓음).

---

## 3. 최종 아키텍처 결정: EXE/로컬 앱을 왜 채택하지 않는가

Chairman 질문: "저렇게 EXE 로 만들어서 로컬 + 앱에서 돌게 할꺼냐?"

**내 의견(요청받은 대로 명시): 아니오, 권장하지 않는다.**

이유:
1. **안정성 역행**: EXE/로컬 앱은 그 컴퓨터가 켜져 있고 로그인돼 있어야만 돈다. 지시사항 1순위인
   "안정성"과 정면으로 배치된다. VPS는 24/7이고 사람 개입이 없어도 계속 돈다.
2. **중복 인프라**: VPS(실행) + GitHub(기록) + n8n(오케스트레이션)이 오늘 실제로 배포·검증됐다
   (2절 참고). 여기에 EXE 앱을 하나 더 만들면 "같은 일을 하는 두 번째 시스템"이 생겨
   `CLAUDE.md`가 명시한 "no duplicate schedulers" 원칙 위반이자 "단순화" 지시와도 반대다.
3. **비용/유지보수 증가**: EXE는 빌드·서명·배포·자동업데이트·OS 호환성(Windows/Mac)까지 새로
   관리해야 할 대상이 된다. "노 코스트, 단순화" 지시와 반대 방향이다.
4. **로그인 필요 플랫폼은 이미 별도 처리 방식이 정해져 있다**: Chairman이 이미 "naver, tstory는
   내가 로그인후 구동"이라고 정리했다. 이건 전체를 EXE화할 이유가 아니라, 그 두 플랫폼만
   사람이 트리거하는 좁은 예외로 두면 된다 — n8n의 "사람 승인 대기" 노드 하나로 충분하다.
5. **복사장류 앱이 필요했던 이유(추정)는 "24시간 서버가 없을 때 PC를 서버처럼 쓰기 위함"인데,
   이미 Hostinger VPS가 있고 오늘 n8n이 그 위에서 성공적으로 떴다** — EXE로 그걸 대체할 이유가 없다.

**결론**: GitHub(소스/이력/감사기록) + VPS(24/7 실행) + n8n(오케스트레이션, self-hosted 무료)
3계층을 최종 아키텍처로 유지한다. 로그인 필수 플랫폼(Naver/Tistory)만 사람이 승인 클릭하는
좁은 예외로 둔다. 새 EXE/로컬 앱/새 유료 SaaS는 만들지 않는다.

---

## 4. 최종 아키텍처 다이어그램 (텍스트)

```
                        ┌─────────────────────────────┐
                        │   GitHub (huh0303-cmyk/      │
                        │   -wp-qwen-autobot)           │
                        │  - 소스 코드, 워크플로우 정의   │
                        │  - STATE/CHARTER/HANDOFF 문서 │
                        │  - 발행 영수증(receipt) 커밋   │
                        │  - GitHub Actions (스케줄/워커)│
                        └───────────────┬──────────────┘
                                        │ deploy / dispatch / webhook
                                        ▼
                        ┌─────────────────────────────┐
                        │   Hostinger VPS (24/7)        │
                        │  - n8n (Docker, self-hosted)  │
                        │  - control_center (Flask,     │
                        │    control.korea365.org)      │
                        │  - systemd 서비스/타이머        │
                        │    (youtube-worker, blogger33  │
                        │    daily timer 등)             │
                        └───────────────┬──────────────┘
                                        │ orchestrates (cron/webhook/retry/queue)
                        ┌───────────────┼───────────────────────────┐
                        ▼               ▼                           ▼
                ┌───────────────┐ ┌───────────────┐        ┌───────────────────┐
                │ WordPress 25   │ │ Blogspot 33    │        │ YouTube (locked10  │
                │ (k-health365   │ │ (일 1포/블로그) │        │ + 서바이벌, private │
                │ 승인+24 타깃)  │ │                │        │ 우선, 승인 후 공개) │
                └───────────────┘ └───────────────┘        └───────────────────┘
                        │
                        ▼
                ┌───────────────────────────────┐
                │ 로그인 필요 예외 (사람 트리거)    │
                │ Naver Blog 3 / Tistory 5        │
                │ → n8n이 콘텐츠 준비+영수증만,     │
                │   실제 로그인/게시는 Chairman     │
                └───────────────────────────────┘

Deterministic Audit Engine ──▶ VERIFIED_COMPLETE (Claude/GPT/Gemini는 자기 인증 불가)
```

---

## 5. 워크플로우 (실제 확인된 단계, 콘텐츠 발행 기준)

1. GitHub Actions 스케줄(랜덤 KST 윈도우) 또는 n8n cron 트리거.
2. 대상 사이트/채널 선정 (사이트당 큐, 실패해도 다른 사이트는 계속 — `CLAUDE.md` 신뢰성 원칙).
3. 콘텐츠 생성 (LLM) → 품질/중복 체크 → 이미지(저작권 안전 우선, 실패 시 이미지 없이 진행 허용).
4. 게시(WP/Blogger는 API 직접, Naver/Tistory는 사람 승인 후 브라우저 세션).
5. 게시 후 영수증(URL/ID/timestamp) GitHub에 커밋 — "성공"은 영수증이 있을 때만 인정.
6. 종합상황실(control.korea365.org)에 반영 — 방문자/누적/총 글수/GSC 색인 4개 지표 + 순위.
7. 결정적 감사 엔진만 VERIFIED_COMPLETE 부여 (Claude/GPT/Gemini는 self-certify 금지).

---

## 6. 백업 플랜 (Plan B/C/SAFE HOLD — `CLAUDE.md` 원칙을 이 트랙에 적용)

- **정상**: CODEX(GPT)가 PM, Claude는 독립 QA/감사.
- **Plan B (Claude가 Acting PM)**: CODEX 사용 불가/쿼터 초과/인증 실패 시, Claude가 인수인계
  패킷(`docs/LONDON_PROJECT_CLAUDE_STATE.md`, `HANDOFF.md`)을 읽고 기존 우선순위·캐던스를
  그대로 유지하며 이어간다. 전략을 새로 짜지 않는다.
- **Plan C (Gemini)**: Claude도 불가 시 Gemini가 이어받되, 현재 Gemini는 "미착수" 상태이므로
  **지금 시점에 Plan C가 발동되면 사실상 처음부터 읽고 시작해야 한다** — 이건 리스크로 명시한다.
- **SAFE HOLD**: 세 AI 모두 불가 시, VPS는 현재 상태를 보존하고 신규 생성/미승인 공개 게시를
  전부 중단한다. 넷째 AI 전략을 임의로 만들지 않는다.
- **토큰 소진 대응**: 모든 발견/결정/코드변경/실패/미해결 항목은 같은 세션 내에 GitHub에
  커밋한다(이 문서 포함). 다음 세션은 채팅 기록이 아니라 `docs/LONDON_PROJECT_CLAUDE_STATE.md` →
  `docs/LONDON_PROJECT_CLAUDE_CHARTER.md` → `config/LONDON_PROJECT_CLAUDE_OWNER_LOCK_2026-09-26.md`
  순으로 읽고 이어간다.

---

## 7. 운영 설명서 (다음 사람/AI가 이어받는 법)

1. `git pull` 후 `docs/LONDON_PROJECT_CLAUDE_STATE.md`를 위에서부터(최신순) 읽는다.
2. 다른 트랙과 겹치는 파일을 고치기 전엔 반드시
   `git log --oneline -5 -- <path>` 로 최근 변경자를 확인한다(런던프로젝트GPT/제미나이와의
   충돌 방지 — `config/LONDON_PROJECT_CLAUDE_OWNER_LOCK_2026-09-26.md`의 소유 파일 목록 참고).
3. 워크플로우를 재실행할 때는 **말로 "완료"라고 쓰지 말고**, 반드시:
   - `curl` 로 GitHub Actions `workflow_dispatch` 트리거,
   - run id를 poll해서 `status`/`conclusion` 확인,
   - 필요하면 `.../runs/{id}/logs` 다운로드해서 실제 라인 수(예: 27/27)까지 확인,
   후에만 STATE.md에 기록한다.
4. 절대 self-certify `VERIFIED_COMPLETE` 하지 않는다 — 결정적 감사 엔진의 몫.
5. 공유 IP(151.106.124.169) 사이트 대상 대량 요청은 사이트당 3~5초 이상 딜레이
   (`SITE_GAP_SECONDS`/`PAGE_GAP_SECONDS` 환경변수)와 `ONLY_SITES` 필터로 나눠서 실행한다
   (WAF 차단 재발 방지 — 이번 세션에 두 스크립트에서 독립적으로 확인된 패턴).
6. 콘텐츠 품질 조사(5차 항목 — 크로스사이트 템플릿화)를 다음 우선순위로 이어간다:
   `scripts/free_article_supplier.py` 등 후보 스크립트를 찾아 사이트별 실제 차별화 여부를
   코드 레벨에서 확인한다. 추측 금지, 코드를 직접 읽어서 확인한다.

---

## 8. 평가에 참고할 것 — 이 트랙이 스스로 지킨/못 지킨 기준

**지킨 것**:
- 모든 "완료" 주장에 run id/로그/아티팩트 근거를 남김 (예: 27/27, run 36235591140).
- 잘못된 코드(APPROVED_GROUP, ensure_required_pages.py 덮어쓸 뻔한 사고)를 발견 즉시 자기수정하고
  기록에 남김 — 숨기지 않음.
- 다른 트랙(GPT/Gemini) 작업을 사실 확인 없이 자기 성과로 편입하지 않음(2절은 각 트랙 원문 인용).
- 사용자의 "미확인이 안 나오게" 지시를 "데이터 숨기기"가 아니라 "원인 수정"으로 해석한다고
  사전에 명시하고 그렇게 실행함.

**못 지킨/미해결**:
- 콘텐츠 템플릿화의 실제 생성 스크립트를 아직 특정하지 못함(발견만, 수정 안 함).
- 대시보드 4지표+순위 UI를 내가 직접 브라우저로 열어 검증하지 않음(diff만 봄) — GPT 트랙 커밋을
  신뢰만 하고 있음, 다음 세션에서 직접 확인 필요.
- 12개 사이트의 필수 페이지 상태가 여전히 WAF 차단으로 미확인 (재시도 1회 "cancelled"로
  끝난 원인도 미조사).

---

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
