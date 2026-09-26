# 런던프로젝트클로드 (London Project · Claude Track) — 헌장

작성: 2026-09-26 · Claude Sonnet 5 · Chairman(허정윤) 직접 지시로 개설

## 1. 이 트랙이 존재하는 이유

런던프로젝트 본체(`CLAUDE.md`, n8n 마이그레이션 등)는 워크플로우 66개 전체를
아우르는 큰 그림이다. "런던프로젝트클로드"는 그 안에서 **안정성 최우선 +
구글애드센스 승인**이라는 좁고 명확한 목표만 파는 독립 서브트랙이다. 새 시스템을
만들지 않는다 — 기존 인프라(GitHub Actions, WordPress REST API, Blogger API)
위에서만 움직인다.

## 2. 1차 목표 (Chairman 지시, 변경 없음)

**구글 애드센스 승인 확대.** 현재 27개 사이트 중 `k-health365.com` 1개만 승인.
나머지 24개 WordPress 사이트가 승인을 받도록 만드는 것이 최우선 순위다.

이 목표가 다른 모든 결정(콘텐츠 우선순위, 버그 수정 순서, 새 기능 여부)보다
위에 있다. 애드센스 승인에 도움이 안 되는 작업은 뒤로 미룬다.

## 3. 운영 범위와 발행 빈도 (기존 정책 확인 — 새로 만든 것 아님)

이미 `docs/NEWSROOM_INDEPENDENT_PUBLISHING_POLICY.md`와
`.github/workflows/daily-publication-floor.yml`에 정확히 이 구조로 박혀 있음을
확인했다:

| 구분 | 사이트 수 | 빈도 | 담당 메커니즘 |
|---|---|---|---|
| WordPress (애드센스 승인 대상) | 24개 | 사이트당 1일 1건 | `daily-publication-floor.yml` (매시 13분, 누락분만 채움) |
| WordPress (이미 승인됨) | 1개 (k-health365.com) | 1일 1건 | 동일 |
| 신문사 (독립 운영) | 2개 (koreanews365.com, theseouljournal.com) | 1일 3~10건, 상한 10 | `newsrooms-daily-publisher.yml` + RSS watch |
| Blogspot | 33개 (계정 기준) | 1일 1건 | 동일 daily-floor의 blogger 잡 |
| YouTube | 10개 잠금 채널 | 주 2~3회, 랜덤 요일 | 별도 VPS 렌더링 (n8n 마이그레이션 문서 참조) |

**결론: 빈도 정책은 이미 사용자 지시와 100% 일치한다. 새로 설계하지 않았고
바꾸지 않았다.** 이번 세션에서 추가한 것은 "24개 사이트가 애드센스 요건을
실제로 충족하는지 확인/보강하는 도구"뿐이다.

## 4. 안정성 원칙 (이 트랙의 최상위 제약)

1. **읽기 전용 감사가 기본값이다.** 라이브 사이트에 쓰기 작업을 하는 스크립트는
   전부 `workflow_dispatch` 수동 트리거만 허용한다 (스케줄 자동 실행 금지) —
   최소 1회 사람이 결과를 확인할 때까지.
2. **쓰기 작업은 반드시 멱등(idempotent)이어야 한다.** 이미 존재하는 페이지/글을
   중복 생성하지 않는다. `scripts/ensure_required_pages.py`(기존 코드, 27개
   사이트 대상, slug+제목 이중 검사로 오탐 방지)가 그 기준 구현.
3. **새 코드를 쓰기 전에 기존 코드부터 읽는다.** 이 세션 초반에 이 원칙을 어기고
   `ensure_required_pages.py`를 안 읽고 덮어썼다가 되돌린 사고가 있었다 (아래
   STATE 문서 "2026-09-26" 항목 참고). 같은 실수를 반복하지 않기 위해 원칙으로
   명문화한다.
4. **한 사이트 실패가 나머지를 막지 않는다.** 사이트별 try/except, 개별 결과
   기록.
5. **새 유료 API·Make.com·새 SaaS 도입 금지** (2026-09-26 Chairman 지시 유지).
   이번 트랙의 모든 스크립트는 `requests`만 쓰고, 기존 GitHub Secrets(WP
   application password)만 사용한다.
6. **VERIFIED_COMPLETE는 절대 자가 선언하지 않는다.** 애드센스 "승인"은 구글이
   내리는 결정이며, 이 트랙은 "승인 요건 충족 여부"까지만 확인·보강한다.

## 5. 진행 상태의 단일 진실 공급원

`docs/LONDON_PROJECT_CLAUDE_STATE.md` — 모든 세션(토큰 소진으로 끊겨도) 시작 시
이 파일부터 읽는다. `CLAUDE.md`의 "Before any work, read" 목록 8번에 등록했다.
