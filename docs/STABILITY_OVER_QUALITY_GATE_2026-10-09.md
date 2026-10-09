# 발행 안정성 우선 조치 — 2026-10-09

Chairman 구두 지시: "교차검증 하지 말라고.. SEO점수 체크도 하지 말고.. 발행이 안정적인것이 가장 중요한거야"

## 변경 사항

1. **`daily-network-publish.yml`**: `CHATGPT_SINGLE_MODEL_PIPELINE`을 `false → true`로 변경.
   - `scripts/editorial_title_gate.py`의 분기에 따라, 두 번의 독립 GPT(무료 체인) 교차검증(`three_model_consensus`, CONSENSUS_FAILED 원인)을 건너뛰고, 저렴한 결정론적 체크(제목 클리셰·"Unlock" 금지어·본문 AI 문구 패턴)만 통과하면 바로 발행됨.
   - SEO 점수 체크는 이미 이전에 제거되어 있었음(`score=None`, 코드 주석 "SEO score intentionally removed from the publication pipeline").
   - 이 워크플로우는 예약 발행(daily-publication-floor.yml) · 순차발행(a-group-sequential-publish.yml) · 확장프로그램 즉시발행이 모두 공유하므로 한 곳 수정으로 전부 적용됨.
   - k-visa365.com의 "Korea Top-Tier Visa" 날조 건이 이 변경 전 마지막으로 막힌 사례였음 — 앞으로는 같은 수준의 날조도 걸러지지 않고 발행될 수 있음. 10/6 확정한 "글 품질 5원칙"(①날조 금지 등)과 정면으로 충돌하는 조치이므로, 기록만 남기고 그대로 실행함. 품질 이슈가 다시 체감되면 이 커밋을 되돌리면 됨.

2. **`daily-publication-floor.yml`**: 자동 예약 cron을 "10분마다 상시 체크"에서 Blogspot과 동일한 **오전/오후 윈도우(07:07–11:37, 14:07–20:37 KST)** 패턴으로 변경. 확장프로그램의 수동 즉시/순차 발행과는 완전히 분리되어 독립적으로 돈다.

## 확장프로그램에서 이미 확인된 것 (변경 없음)
- "WordPress 25 — 즉시 발행" = `daily-network-publish.yml` (target_site_url 비우면 25개 전체, 특정 사이트 지정도 가능)
- "WordPress 25 — 순차 공개 발행" = `a-group-sequential-publish.yml` → `scripts/a_group_sequential_dispatch.py`가 매 실행마다 새 랜덤 시드로 25개 사이트를 셔플해서 처음부터 끝까지 순서대로(사이트당 3~7분 랜덤 간격) 발행 — 이미 구현되어 있었음, 별도 작업 불필요.
