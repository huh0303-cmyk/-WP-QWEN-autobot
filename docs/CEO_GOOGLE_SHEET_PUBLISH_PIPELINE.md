# CEO Google Sheet 발행 파이프라인 기준

확정일: 2026-08-30  
적용 목표: 2026-08-31부터 Google Sheet를 유일한 운영 통제판으로 사용

## 1. 운영 대상

| 구분 | 수량 | Google Sheet 통제 탭 | 실제 작업기 |
|---|---:|---|---|
| WordPress | 27 | `자동화_사이트설정`, `자동화_황금키워드`, `자동화_발행대기` | `daily-network-publish.yml`, `newsrooms-daily-publisher.yml` |
| Blogspot | 27 | `자동화_사이트설정`, `자동화_발행대기` | `platform-publish-v2.yml` |
| YouTube 플레이리스트 | 5 | `자동화_유튜브채널`, `자동화_유튜브실행` | `generate-youtube-playlist.yml` |
| YouTube 영어 지식 | 5 | `자동화_유튜브채널`, `자동화_유튜브실행` | `curio-longform-daily.yml` |

총 관리 대상은 웹사이트 54개와 YouTube 10개다.

## 2. 단일 통제 원칙

1. GitHub의 JSON은 초기값·복구용 기준본이다.
2. 일상 운영의 ON/OFF, 다음 실행시각, 키워드, 상태, 승인 여부는 Google Sheet 값만 사용한다.
3. GitHub 스케줄은 시트를 확인하는 폴링 장치일 뿐, 발행 대상과 주제를 독자적으로 결정하지 않는다.
4. WordPress와 Blogspot은 기본적으로 초안, YouTube는 비공개로 생성한다.
5. 공개 발행은 Google Sheet 승인값이 명시된 작업만 허용한다.
6. 모든 실행 결과와 오류는 Google Sheet 실행현황 탭에 다시 기록한다.
7. 같은 자산·같은 키워드·같은 날짜의 중복 실행을 차단한다.

## 3. 현재 실제 상태

### WordPress 27

- 27개가 `자동화_사이트설정` 관리 대상이다.
- 일반 블로그는 `publish-scheduler.yml`이 시트 설정을 읽어 초안 작업을 호출한다.
- 뉴스 2개는 `newsrooms-daily-publisher.yml`이 담당하며 역시 시트 설정을 읽는다.
- 작업기 기본값은 `publication_approved=false`, 즉 초안이다.

### Blogspot 27

- 27개 대응 행은 등록되어 있다.
- Blogger API destination ID가 있고 즉시 작업 가능한 사이트는 제한적이다.
- 현재 READY 6개, QUALITY_FAIL 1개, 나머지는 CREATED_SHELL 또는 EMPTY다.
- 실제 시트 큐 작업기는 `platform-publish-v2.yml`이다.
- `blogger-daily-scheduler-v2.yml`은 별도 상태 파일을 쓰는 구형 경로이므로 최종 전환 때 정기 스케줄을 제거해야 한다.

### YouTube 10

- 플레이리스트 5개와 영어 지식채널 5개가 모두 `자동화_유튜브채널`에 등록될 수 있는 구조다.
- 플레이리스트: 로맨틱글로벌, 힐링, 카페음악, MBB, K-pop.
- 영어 지식: 우주, 역사, 발명, 무성영화, 레트로.
- `youtube-control-scheduler.yml`은 Google Sheet의 ON/OFF와 `next_run_at`을 읽도록 구현되어 있다.
- 현재 워크플로 전체에 EMERGENCY LOCK이 걸려 있어 자동 디스패치는 실행되지 않는다.
- 잠금 해제 전에는 10개 채널 행·비공개 정책·OAuth·작업기 입력값을 한 번에 검증해야 한다.

## 4. 제거해야 할 중복 경로

| 중복 경로 | 처리 기준 |
|---|---|
| `blogger-daily-scheduler-v2.yml` 정기 스케줄 | 중지하고 `platform-publish-v2.yml`만 사용 |
| JSON 상태 파일 기반 Blogger 랜덤 발사 | Google Sheet `자동화_발행대기`로 대체 |
| YouTube 개별 채널 자체 스케줄러 | `youtube-control-scheduler.yml`로 통합 |
| 별도 방문자 보고 | CEO 종합상황실 한 번으로 통합 완료 |

## 5. 내일 전환 전 필수 게이트

- [ ] `자동화_사이트설정`에 WP 27개가 정확히 27행인지 확인
- [ ] Blogspot 27개 행과 WP 대응 관계 확인
- [ ] Blogspot destination ID 누락·주소 충돌 목록을 CEO에게 보고
- [ ] `자동화_유튜브채널`에 PLAYLIST 5 + KNOWLEDGE 5가 정확히 10행인지 확인
- [ ] YouTube 10개 모두 기본 공개상태가 private인지 확인
- [ ] WP·Blogger 기본 상태가 draft인지 확인
- [ ] SEO 기준점수 75와 2회 재작성 후 미달 시 중지 규칙 확인
- [ ] 중복 방지키와 결과 회신 열 확인
- [ ] 구형 Blogger 정기 스케줄 중지
- [ ] YouTube 안전 잠금은 위 검증 성공 후에만 해제
- [ ] 테스트 1건씩(WP/Blogger/Playlist/Knowledge) 비공개·초안 생성 검증

## 6. CEO가 보는 결과

`자동화_실행현황`과 `자동화_유튜브실행`에는 다음 값이 반드시 남아야 한다.

- 자산명과 실제 주소
- 핵심 키워드
- 생성 모델
- 품질점수
- 초안/비공개/공개 상태
- 실제 편집 또는 검토 링크
- 실행시각과 완료시각
- 성공/보류/실패 및 원인

CEO 종합상황실은 위 결과를 요약해 정상, 급증, 급락, 지연, 오류와 당일 의사결정 항목을 가장 먼저 보여준다.

## 7. 모든 성과 수치의 증감 표기 — 2026-08-31 사용자 확정

WP·Blogger·YouTube·SNS의 모든 성과 수치와 소계·합계는 반드시 `값(전일 대비 증감)`으로 보고한다. 숫자 단독 표기를 금지한다. 비교값이 없으면 `값(증감 미확인)`, 수집 실패는 `미집계(증감 미확인)`이며 임의의 `(0)`으로 대체하지 않는다.

계산 기준 및 보고 전 체크리스트는 [CEO_METRIC_DELTA_MANDATE.md](CEO_METRIC_DELTA_MANDATE.md)를 따른다.
