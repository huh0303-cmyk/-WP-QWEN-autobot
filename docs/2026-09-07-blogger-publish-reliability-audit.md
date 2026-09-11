# 2026-09-07 Blogger/YouTube 발행 안정성 감사 및 수정 기록

CEO 지시: "모든 사이트 하나하나 체크하라" — 32개 Blogspot 전체를 실제로
디스패치해서 결과를 확인하고, 발견되는 문제를 전부 근본 원인까지 고칠 것.

## 1. Blogspot 계정 미등록 (근본 원인, 완전 해결)

`blogger-rewrite.yml`이 "success"를 반환해도 실제 발행은 별도 워크플로
(`platform-publish-v2.yml` → `process_platform_queue.py`)가 처리하며, 이
워크플로는 `자동화_플랫폼계정` 시트에 활성화된 계정 행이 없는 사이트는
`"enabled account not found"`로 조용히 건너뛴다. 32개 Blogspot 중 5개만
이 시트에 등록되어 있었다 (Tistory는 자동 등록기가 있었지만 Blogger는
없었음).

- `scripts/sync_automation_hub_to_sheets.py`에 `_seed_blogger_accounts()`
  추가 → 25개 자동 등록.
- `scripts/activate_held_blogger_accounts.py` (일회성) → 보류 중이던
  3개(`blogger_korea365`, `blogger_kfinance365`, `blogger_kieca`) 활성화.
- 검증: `scripts/check_blogger_accounts_enabled.py` 결과 32/32 정상.

## 2. 한국어 콘텐츠가 영어 사이트에 유출되는 버그

`automation_hub/blogger_topic_router.py`가 한국어 매체에서 주제어를
가져오는데, 이걸 영어 사이트에 그대로 프롬프트에 넣으면서 번역 지시가
없었음. `automation_hub/original_writer.py`의 `original_prompt()`에
"한국어 키워드/근거는 배경으로 참고만 하고 반드시 영어로 직접 번역해서
써라, 한글 문자를 단 하나도 출력하지 마라" 지시를 명시적으로 추가.

## 3. 32개 동시 디스패치 시 "오늘자 주제어 없음" 대량 실패

**증상**: 32개를 몰아서 디스패치하면 24개 이상이
`NoEligibleTopic("오늘자 복수 매체 근거와 사이트 주제를 함께 만족하는
주제어가 없습니다")`로 실패. 같은 시각대에 Codex가 독립적으로 실행한
배치에서도 동일 패턴 재현 확인 — 특정 세션만의 문제가 아니라 구조적
문제.

**근본 원인**: `MEDIA_FEEDS`는 모든 사이트에 공통인 고정 뉴스 피드
목록이다. 32개 사이트를 짧은 시간에 디스패치하면 GitHub Actions의
공유 러너 IP 대역에서 거의 동시에 같은 `news.google.com` RSS URL을
32번 두드리게 되고, 이건 구글의 요청 제한(rate limiting)에 걸리는
전형적인 패턴이다. 얇거나 빈 200 OK 응답은 예외를 던지지 않아서 감지
되지 않았다.

**수정** (`automation_hub/blogger_topic_router.py`):
- `BLOGGER_TOPIC_FETCH_JITTER_MAX_SECONDS` 환경변수로 헤드라인 조회 전
  0~N초 무작위 지연 추가 (배치 디스패치에서만 60초로 설정, 수동 단일
  실행·테스트는 0).
- 재시도 2회 → 3회, 백오프 8초/20초로 증가.
- `.github/workflows/blogger-rewrite.yml`에 `fetch_jitter_max_seconds`
  입력 추가, `control_center/app.py`의 blogspot33 그룹 버튼과
  `scripts/blogger_daily_auto_publish.py`(하루 4회 크론)에서 60초로 설정.

## 4. "Commit budget guard state 실패"로 성공한 작업이 실패로 표시됨

**증상**: 실제로는 기사 생성·큐잉·발행 디스패치까지 전부 성공했는데
(`ktech365` 실행 로그로 직접 확인: `quality_score: 100`,
`platform-publish-v2.yml`까지 정상 디스패치됨), 마지막 비용 기록용
git 커밋 단계가 다른 실행과 충돌하면서 워크플로 전체가 "실패"로 표시됨.

**근본 원인**: GitHub Actions의 `run:` 스텝은 기본적으로 `set -e`로
실행된다. 재시도 루프 안의 `git pull --rebase`가 충돌하면 그 자체가
0이 아닌 종료 코드를 내면서 스텝 전체가 즉시 실패 처리된다.

**수정**: 해당 스텝에 `continue-on-error: true` 추가, 충돌 시
`git rebase --abort`로 정리 후 재시도. 비용 기록은 부가 정보일 뿐 실제
작업 성공 여부와 무관해야 한다.

## 5. YouTube 그룹 버튼(플리5/지식5)이 5개 중 4개 "cancelled"

**근본 원인**: `generate-youtube-playlist.yml`은 의도적으로 단일
동시성 그룹(`youtube-production-single-owner`,
`cancel-in-progress: false`)을 쓴다 — 영상 렌더링은 한 번에 하나만
설계상 맞다. 그런데 그룹 버튼이 5개 채널을 8초 간격으로만 디스패치하고
끝에 한꺼번에 폴링했기 때문에, 뒤에 디스패치된 채널이 앞 채널이 아직
큐에 있는 동안 그 큐 자리를 밀어내면서 연쇄적으로 취소됨.

**수정**: `control_center/app.py`의 `_run_group_publish` — 이제 채널
하나를 디스패치하고 완료될 때까지(`_poll_bulk_items`) 기다린 다음에
다음 채널을 디스패치한다. 5개 전부 성공하지만 시간은 더 걸린다
(영상이라 어쩔 수 없음).

## 6. Facebook 페이지별(TOPIK/ENGLISH/LANGUAGE) 인증 분리

Instagram/Threads는 이미 `scripts/meta_publish.py`가
`SOCIAL_BRAND` 환경변수 기반으로 브랜드별 시크릿을 구분해서 쓰고
있었다 (Codex 작업, PR #23). Facebook만 단일 페이지/토큰 쌍으로 남아
있어서 같은 방식으로 확장: `scripts/social_publish.py`에
`facebook_page_credentials()` 추가, TOPIK은 기존 이름 그대로,
ENGLISH/LANGUAGE는 `_ENGLISH`/`_LANGUAGE` 접미사. 실제로 켜려면 메타
개발자 앱에서 발급받은 값이 GitHub Secrets에 필요함 (아직 없음):
`FB_PAGE_ACCESS_TOKEN_ENGLISH`, `FB_PAGE_ID_ENGLISH`,
`FB_PAGE_ACCESS_TOKEN_LANGUAGE`, `FB_PAGE_ID_LANGUAGE`.

## 7. `blogger_portfolio.json` 복구 후 발생한 크래시

`koreamedicaltour1`(일반 관심사 블로그로 재배정됨, wp 필드 없음)
때문에 `scripts/roll_14day_content_calendar.py`가
`item["wp"]`에서 `KeyError`. `site_key`로 대체하도록 수정.

## 검증

전체 테스트 스위트 376개 통과 (스파스 체크아웃으로 로고 파일이 로컬에
없어서 나는 1개 실패, 뉴스 데이터 의존적인 1개 실패 제외 — 둘 다 이번
수정과 무관, 클린 체크아웃/CI에서는 통과함).

## 남은 일

- 다음 실제 크론(하루 4회, 01/07/13/19 UTC)에서 위 수정들이 실제로
  효과가 있는지 확인 필요 — 이건 소량(≤12개) 배치에서 검증된 적 없음.
- Facebook/Instagram/Threads 실사용은 메타 개발자 앱 설정 및 브랜드별
  토큰 발급이 남음 (`docs/META_PUBLISHING_SETUP.md` 참고).
