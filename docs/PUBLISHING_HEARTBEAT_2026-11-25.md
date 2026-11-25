# 자동 발행 전체 점검 + 발행 하트비트 (2026-11-25 KST, 런던프로젝트클로드)

task_id: `claude-20261125-publishing-heartbeat`
요청: "리모트 컨트롤이 꺼졌다는데 뭐가 문제인지 보고, WordPress·Blogspot·YouTube·Instagram·Threads·TikTok
자동 발행 워크플로 전체 다시 체크해서 액티브하게."

## 1. "리모트 컨트롤 꺼짐"의 의미
- Claude Remote Control(클라우드 세션 → PC 폴더 연결): `list_computer_folders` 결과 공유 폴더 **0개**.
  즉 Claude 데스크톱 앱 Settings → Claude Code → Remote Control 에서 공유 중인 폴더가 없다.
- Desktop Commander 기준 PC `ChrisHUH`는 **온라인**(2026-11-25 확인). `DESKTOP-TN6TN3J`는 178시간 오프라인.
- WordPress·Blogger·YouTube·Threads 발행은 전부 GitHub Actions에서 돈다. **PC Remote Control이 꺼져 있어도
  발행 자체는 멈추지 않아야 정상**이다. 실제 발행 정체의 원인은 아래 2번이다.

## 2. 근본 원인 — GitHub가 이 저장소의 cron 실행을 대부분 누락
| 워크플로 | 예약 | 실제 실행 (근거: Actions run 목록) |
|---|---|---|
| `daily-publication-floor.yml` (WP 22 + Blogger 33 + 뉴스룸의 유일한 스케줄 담당) | 하루 34회 | 11-18~11-24 하루 약 2회, **11-24 14:35Z 이후 0회** (마지막 run 45336861424, 11-24 05:57Z) |
| `threads-6-publisher.yml` | 10분마다 | 11-24 17:51Z 이후 schedule 실행 **0회** (수동 1회뿐) |
| `youtube-github-scheduler.yml` | 매시 17분 | 하루 약 3회 |
| `meta-12-randomized-publisher.yml` | 10분마다 | 총 3회, 전부 skipped |

- 모든 YAML 파싱 정상(검사함). 워크플로 상태 active. 즉 설정 오류가 아니라 GitHub 스케줄러의 고부하 누락.
- 결과: floor는 1회에 최대 2개 사이트만 dispatch → 하루 2회면 WP 23·Blogger 33 중 극히 일부만 발행.
  `data/daily-publication/*.json` 영수증: WP 대부분 마지막 11-22, Blogger 영수증은 9월~11-09에 멈춤.
- `workflow_dispatch`는 누락되지 않는다(11-24 12:58Z 수동 dispatch 20건 모두 실행됨).

## 3. 수정 — `publishing-heartbeat.yml` + `scripts/publishing_heartbeat.py`
- 러너 1개가 약 5.5시간 동안 10~14분(무작위) 간격으로 기존 발행 워크플로를 `workflow_dispatch`로 깨운다.
  - `daily-publication-floor.yml`: 06:05~23:15 KST, 최소 14분 간격 (사이트별 무작위 슬롯·공개 URL 확인·영수증 게이트는 floor가 그대로 담당)
  - `threads-6-publisher.yml`: 08:05~23:15 KST, 최소 9분 간격 (스크립트 catch-up 20분 안에 들어감)
  - `youtube-github-scheduler.yml`: 24시간, 최소 55분 간격 (원래 설계인 시간당 1회 복원; 비용 홀드 게이트 유지)
- 루프 종료 시 자기 자신을 다시 dispatch(체인). 체인이 끊겨도 2시간마다 2개의 백업 cron이 재시작.
- concurrency 그룹으로 동시 실행 1 + 대기 1만 허용 → 중복 실행 없음.
- 직접 발행하는 코드는 없다. 각 대상의 게이트·킬스위치·중복 방지는 그대로.
- 킬스위치: 저장소 변수 `PUBLISHING_HEARTBEAT=false`.
- 비용: 공개 저장소(visibility=public) → 표준 러너 분 과금 없음. 유료 API 추가 없음.
- 테스트: `tests/test_publishing_heartbeat.py` 9개 + 기존 floor 테스트 14개 = 23 passed.
- **활성화 조건:** `workflow_dispatch`는 기본 브랜치에 있는 파일만 실행 가능 → PR이 main에 병합된 뒤
  `publishing-heartbeat.yml`을 1회 수동 실행하면 체인이 시작된다.

## 4. 플랫폼별 점검 결과 (코드로 고칠 수 없는 차단 포함)
| 플랫폼 | 상태 | 근거 | 필요한 조치 |
|---|---|---|---|
| WordPress 23 | 코드·인증 경로 정상, **스케줄 누락으로 정체** | floor 영수증, run 목록 | 하트비트 병합 |
| Blogspot 33 | 동일 (11-24에 floor가 Blogger 담당으로 변경됐으나 그 뒤 floor 실행 0회) | 위 동일 | 하트비트 병합 |
| YouTube 캘린더(플레이리스트/지식) | scheduler 정상 실행(가드 통과), 실행 빈도만 부족 | run 45489306219 | 하트비트 병합 |
| YouTube 9개 언어 SOS 쇼츠 | **매일 실패(11-13~)** | run 45490452567: `RefreshError unauthorized_client` | Chairman: `YOUTUBE_OAUTH_CLIENT_ID`와 같은 OAuth 클라이언트로 언어 채널 refresh token 재발급 |
| YouTube Seoul_Jisoo1 쇼츠 | **매일 실패** | run 45507302896: 동일 `unauthorized_client` | `YOUTUBE_OAUTH_REFRESH_TOKEN_SHOPPING_SEOUL_JISOO1` 재발급 |
| YouTube Seoul Journal 정치 쇼츠 | 실패(장면 계획 검증) — 다른 세션이 11-25 커밋 44e4458로 작업 중 | run 45520705600 | 해당 트랙에서 처리 (이번 변경 없음) |
| Threads 6 | 워크플로는 동작, **토큰·USER_ID 12개 값 전부 비어 있음** | run 45453146622 로그: 6계정 `credentials missing` | Chairman: `META-SOCIAL` 환경에 `META_THREADS_*_ACCESS_TOKEN`(secret)·`_USER_ID`(variable) 등록 |
| Instagram 6 | `meta-12-randomized-publisher` 변수 게이트로 skipped | runs 3건 모두 skipped | 토큰 등록 + `META_LIVE_PUBLISH`, `META_12_TARGETS_READY` 승인 |
| TikTok | **자동 발행 워크플로 없음** (`social-topic-publish.yml` disabled_manually, `TIKTOK_ACCESS_TOKEN` 경로만 존재, 미감사 앱=SELF_ONLY) | 코드 검색 | TikTok 개발자 앱 감사·토큰 발급 후 별도 승인 필요 |

## 5. 미검증 / 다음 조치
- 이 문서 시점에 하트비트는 main 미병합 → 아직 동작 안 함. 병합 후 첫 실행 로그의 `DISPATCH ... ok=True` 및
  floor 리포트 `public_verified` 증가로 확인해야 한다.
- 2026-11-25 00:54Z에 기존 `daily-publication-floor.yml`을 main에서 수동 1회 dispatch함(run 45521665016, 밀린 슬롯 처리용).
- VERIFIED_COMPLETE 아님. 공개 URL 확인은 floor 리포트·감사 엔진 기준.
