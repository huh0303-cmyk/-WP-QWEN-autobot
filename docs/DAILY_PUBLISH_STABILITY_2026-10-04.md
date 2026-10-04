# 매일 발행 안정화 — 진단과 조치 (2026-10-04)

Chairman 요청: "내가 안정적으로 매일 발행할 수 있도록 만들어줘 — VPS와 GitHub에서."

## 진단 (GitHub 실행 기록 근거)
1. **발행을 시작시키는 스케줄이 없다.** 2026-09-28 18:15Z 커밋 `0201910` "chore: remove noisy GitHub schedules"로
   `daily-publication-floor.yml`의 매시 cron이 제거됐다(작성자: huh0303-cmyk). n8n 마스터
   (`deploy/n8n/workflows/*_master.json`)는 저장소 안에서 전부 `"active": false`다. 마지막 floor 실행은 2026-09-29(수동).
   WP·Blogspot·뉴스룸 발행 워크플로는 9/29 이후 실행 기록이 없다. (VPS의 n8n에서 직접 활성화했는지는 이 세션에서 확인 불가.)
2. **9/29 마지막 실행들이 같은 원인으로 실패했다.** 모든 발행기가 하나의 `GEMINI_API_KEY`를 쓴다.
   - Blogspot 33: `Gemini request failed with HTTP 400: API key not valid` (run 36546893420)
   - WP(k-trip365): 5개 모델 전부 `RuntimeError`로 `WRITERS_EXHAUSTED` (run 36547341372)
   - 뉴스룸: Gemini 503 + `GPT checker unavailable`로 편집 게이트 차단 (run 36547085168)
3. **키가 거부돼도 floor는 계속 사이트를 claim했다.** 사이트당 하루 2회 시도를 소진하고 `DISPATCHED`만 남기며,
   실제로는 글이 만들어지지 못한다. 9/29 상태 파일: 60개 중 `PUBLISHED` 11, `DISPATCHED` 41, `CLAIMED` 8.

## 조치 (브랜치 `stable-daily-publish-2026-10-04`, 미병합)
- `scripts/provider_key_check.py`: Gemini `models.list`(무료, 생성 없음)로 키 상태를 OK/QUOTA/UNREACHABLE/INVALID/MISSING으로 분류.
  INVALID·MISSING만 발행을 막는다(쿼터·네트워크는 자체 회복되므로 막지 않음). 키는 URL이 아니라 헤더로 전송.
- `scripts/daily_publication_floor.py`: claim 전에 키를 점검. 거부된 키면 사이트를 claim/dispatch하지 않고(공개 URL 검증은 그대로 수행)
  리포트에 `provider.blocked=true`를 기록하고 run을 실패 처리해 GitHub 알림으로 드러나게 한다.
  키 환경변수를 넘기지 않는 기존 호출자는 이전과 동일하게 동작.
- `.github/workflows/daily-publication-floor.yml`: 키를 job에 전달하고, 하루 9회(KST 06:23~22:23, 2시간 간격, 정각 회피) 스케줄 추가.
  패스당 플랫폼별 최대 4개 dispatch → 9패스 = 플랫폼당 36곳 용량(WP 25 / Blogspot 33 + 재시도 여유).
  모든 사이트가 공개 확인되면 이후 패스는 읽기만 한다.
- `.github/workflows/provider-key-check.yml`: 수동 실행용. 키 교체 후 초록불인지 확인.

## 사람이 해야 하는 것 (Claude가 할 수 없음)
- GitHub Secret `GEMINI_API_KEY`와 VPS `/etc/korea365/article-runtime.json`의 키를 새 유효 키로 교체
  (API 키 입력은 Claude가 하지 않는 항목). 교체 후 **Provider key check** 워크플로를 실행해 `gemini: OK` 확인.
- 9/28에 스케줄을 직접 제거하셨으므로, 이 브랜치의 스케줄 복구를 받아들일지 결정. n8n으로 옮길 계획이면
  n8n 마스터를 활성화하는 같은 변경에서 이 `schedule:`을 제거해야 이중 트리거가 되지 않는다(`LONDON_PROJECT_WORKFLOW_AUDIT_2026-09-26.md` §2).

## 검증
- `tests/test_provider_key_check.py` 신규 17개 + 기존 `tests/test_daily_publication_floor.py` 10개 통과.
- 기존 실패 1건 `test_unknown_dispatch_is_never_replayed`: 변경 전 `main`에서도 동일하게 실패(로컬에 `EXAMPLE_PASS` 환경변수가 없어
  `CREDENTIAL_REQUIRED`가 먼저 반환됨). 이번 변경과 무관.
- 미검증: 실제 키 상태(마지막 실행이 9/29라 현재 키가 여전히 거부되는지는 이 세션에서 직접 확인하지 못함), 스케줄 실제 실행,
  VPS n8n 활성 여부.
