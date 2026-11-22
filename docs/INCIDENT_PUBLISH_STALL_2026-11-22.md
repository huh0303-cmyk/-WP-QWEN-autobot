# 발행 중단 점검·수정 기록 — 2026-11-22

요청자: Chairman. 증상: WordPress 24곳 7~9일, Blogspot 31곳 8~10일 발행 없음. 대시보드(control.korea365.org) 자체는 정상 로드.
이 기록은 근거 있는 사실과 아직 미검증인 항목을 구분한다. `VERIFIED_COMPLETE` 판정은 결정론적 감사에서만 가능하다.

## 1. 근본 원인 (확인됨 — Actions 로그 근거)

| # | 영역 | 원인 | 근거 |
|---|------|------|------|
| 1 | WordPress | `scripts/autopost_mega.py` 생성 루프가 제목만 있으면 `best_result`를 잡고 바로 `break` → 길이 검사·재생성 피드백 코드가 실행되지 않음. 모델은 4,814~5,774자를 쓰고 최종 게이트(2,500~4,000자)가 매번 `WP_LENGTH_BLOCKED`로 거부. 재시도 3회 모두 동일 | run 45011527369, 45011521587 (koreataxnlaw, krealestate365) |
| 2 | WordPress | 제목 반복/템플릿 오류 시 매번 본문 전체를 재생성, 4회 모두 실패하면 "제목 추출 실패"로 당일 발행 차단 | run 45011521587 |
| 3 | 이미지 | `find_stock_image`가 검색어 100자 초과 시 즉시 `None` 반환(호출부가 "keyword + 전체 제목"을 넘김) + `matches()`가 검색어 전 단어가 사진 alt에 있어야 통과. 무료 2단계(Pexels/Pixabay)가 조용히 무산 → 3·4단계는 Replicate(유료) 401 | 같은 run 로그의 `all_four_failed`, 401 |
| 4 | Blogger 33 | 코드 버그 아님. 11/18 승인 문서(`docs/BLOGGER_33_AUTO_PUBLICATION_APPROVAL_2026-11-18.md`) §5에 따라 `BLOGGER_33_BACKUP_AND_TEST_VERIFIED`가 false라 `publish_blogger_33_now.py`가 스스로 중단 | run 45008152348 |
| 5 | Blogger 33 | 길이 재시도 힌트가 "too short" 문자열에만 반응하나 검증기 메시지에는 그 문구가 없어 길이 피드백이 전달되지 않음 | `publish_blogger_33_now.py` |
| 6 | 대시보드/콘솔 | `scripts/publication_board.py` 123~124행 들여쓰기 오류(SyntaxError). `control_center/app.py`가 이 모듈을 import | pytest 수집 오류 |
| 7 | YouTube | `youtube_github_worker.py`: 한 채널 작업 실패 시 워커 전체 종료. 이번 건은 History 채널이 퍼블릭도메인 영상을 못 찾음(archive.org 응답 이상 + 시각 관련도 0/4) | run 44996778916 아티팩트 로그 |
| 8 | SNS | `london-social-affiliate-10-links.yml`: `--mode`가 빈 문자열이면 argparse 오류(exit 2) | run 44903199941 |

## 2. 이번 커밋의 변경

- 글자 수: 목표 3,000~3,500자, 통과 2,500~4,500자 (WP·Blogger 동일). `editorial_readability.py`, `autopost_mega.py`, `autopost_current.py`, `publish_blogger_33_now.py`.
- WP 생성 루프: 길이를 실제로 검사하고 허용 범위 밖이면 방향(증량/축약)을 명시해 재생성. 모두 초과하면 마지막 수단으로 문장 단위 절삭(허용 범위 안일 때만).
- 제목: 뻔한 AI 제목 패턴 추가(Demystifying, Deep Dive, Top N tips, 꿀팁, A to Z, 총정리 등). 제목만 문제일 때 제목만 재작성. 본문의 제거 가능한 AI 상투구("In conclusion," 등) 자동 삭제.
- 이미지: 검색어 압축(`condense_query`), 부분 일치 규칙(2단어 이하는 전부, 3단어 이상은 절반·최소 2개), 무료 단계 결과 로그 추가, Replicate 401 시 같은 실행에서 재호출 중단.
- `publication_board.py` 문법 오류 수정.
- YouTube 워커: 작업 실패 시 기록 후 다음 작업 진행. 성공이 하나도 없을 때만 실패 종료.
- 10-Link 워크플로우: `--mode` 기본값 `new`.

## 3. 아직 미해결 — 사람의 조치(비밀값/승인) 필요

- **Meta**: 8개 연결 `INVALID_OR_EXPIRED_TOKEN`(HTTP 400), Threads 2개(`META_THREADS_SEOUL_CHRIS_ACCESS_TOKEN`, `META_THREADS_JAPANESE_PICK_ACCESS_TOKEN`) 토큰 없음. 토큰 재발급 후 GitHub Secrets 갱신 필요 (run 44994690462, 44998223667).
- **YouTube SOS 쇼츠**: `unauthorized_client` (OAuth 재인증 필요, `scripts/reauthorize_youtube_channel.py`) (run 44933549695).
- **Replicate**: `REPLICATE_API_TOKEN` 401. 무료 전용 정책이면 비워 두고, 유료 폴백을 쓰려면 갱신.
- **Blogger 33 잠금**: 백업·복원 확인 + 영어/한국어 테스트 발행 완료 후 저장소 변수 `BLOGGER_33_BACKUP_AND_TEST_VERIFIED=true`. Chairman 결정 사항.
- **Seoul Jisoo 쇼츠**: "No recent attributed headline from approved sources" — 승인된 뉴스 소스에서 최신 기사 없음(15/15 실패). 소스 점검 필요.

## 4. 검증 상태

- 로컬: 변경 모듈 컴파일, 이미지 테스트 12개 통과, `editorial_gate_preflight` 통과. 전체 테스트는 변경 전에도 132건 실패(기존 낡은 테스트)였고 이번 변경으로 새 실패 없음.
- 미검증: `autopost_mega.py`는 이 세션 환경 제약으로 로컬 컴파일을 못 했다. 실제 검증은 GitHub Actions 수동 실행과 게시 URL 확인으로만 가능.
