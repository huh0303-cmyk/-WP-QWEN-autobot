# GitHub Issues 기반 텔레그램 → 네이버 발행 대기열

이 방식은 기존 Google Sheets 대기열을 삭제하거나 자동 전환하지 않습니다. 별도 실험 경로이며, 기존 Sheets 파이프라인은 그대로 유지합니다.

## 구성

1. `scripts/github_queue_bot.py`: Telegram 명령을 받아 GitHub Issue를 생성합니다. 네이버 발행은 하지 않습니다.
2. `scripts/naver_github_issue_runner.py`: 신뢰된 개인 PC에서 GitHub의 준비된 Issue를 가져와 기존 `NaverLocalPublisher`로 처리합니다.
3. 성공은 공개 URL이 확인된 경우에만 `queue:published`로 기록합니다. 발행 확인이 불완전하면 `queue:attention`, 예외는 `queue:failed`로 기록합니다.

## 보안 설정 (Windows PowerShell)

새로 발급한 토큰은 소스코드, 채팅, Git 저장소에 넣지 마세요. 토큰을 환경변수에 설정합니다.

```powershell
$env:TELEGRAM_BOT_TOKEN = Read-Host "New Telegram bot token"
$env:GH_PAT = Read-Host "GitHub PAT with Issues read/write access"
$env:TELEGRAM_ALLOWED_CHAT_IDS = Read-Host "Allowed Telegram numeric user/chat IDs, comma-separated"
```

GitHub PAT는 가능하면 해당 저장소만 허용하고 Issues 읽기/쓰기 권한만 부여하세요. 이 봇은 토큰을 출력하지 않습니다. 환경변수는 현재 PowerShell 세션에만 적용됩니다.

필수 패키지(프로젝트의 활성 Python 환경에서 설치):

```powershell
python -m pip install "python-telegram-bot>=20,<23" requests playwright
python -m playwright install chromium
```

## 1. Telegram 봇 실행

```powershell
python scripts/github_queue_bot.py
```

텔레그램에서 다음 형식으로 보냅니다.

```text
/naver1_365 제목 | 본문
/naver2_365 제목 | 본문
/naver3_365 제목 | 본문
```

정상 접수 시 Issue 링크가 반환됩니다. 접수 성공은 네이버 발행 성공이 아닙니다.

## 2. 네이버 로그인 프로필 준비

각 계정은 별도의 로컬 프로필을 사용합니다. PC에서 해당 계정으로 직접 로그인합니다.

```powershell
python scripts/naver_github_issue_runner.py login --site-id huh0303
python scripts/naver_github_issue_runner.py login --site-id huh3
python scripts/naver_github_issue_runner.py login --site-id huh4
```

브라우저 로그인 완료 후 터미널로 돌아와 Enter를 누릅니다. 프로필은 `.local/naver-profiles/` 아래에 보관되며 공유하거나 Git에 커밋하지 마세요.

## 3. 대기열 실행

```powershell
python scripts/naver_github_issue_runner.py run --site-id huh0303 --max-jobs 1
```

다른 계정은 `huh3`, `huh4`를 지정합니다. 실제 발행이므로 테스트 전용 글로 먼저 검증하고, 실행 중에는 PC와 브라우저 프로필을 유지하세요. 기본 최대 처리 수는 1개입니다.

## 라벨 규칙

- `queue:ready`: 발행 대기
- `queue:processing`: 실행기가 작업을 선점
- `queue:published`: 공개 URL 확인
- `queue:attention`: 로그인/캡차/URL 확인 등 사람의 점검 필요
- `queue:failed`: 실행 중 예외
- `blog:huh0303`, `blog:huh3`, `blog:huh4`: 대상 계정

봇은 상태/계정 라벨을 필요 시 생성합니다. 실행기는 처리 시작 전에 상태 라벨을 바꿔 중복 실행 가능성을 줄입니다. GitHub API에는 트랜잭션형 잠금이 없으므로 같은 계정에서 실행기를 두 개 동시에 실행하지 마세요.

## 제한 사항

- Telegram `run_polling()`은 봇 프로세스가 실행 중인 PC에서만 메시지를 받습니다. PC가 꺼지거나 프로세스가 종료되면 접수도 멈춥니다.
- 네이버 발행은 로그인된 로컬 브라우저에 의존합니다. 캡차, 세션 만료, UI 변경이 발생하면 `queue:attention`으로 바뀌며 사람의 확인이 필요합니다.
- 이 코드는 VPS 배포나 Windows 작업 스케줄러 등록을 자동으로 수행하지 않습니다.
- 기존 `자동화_발행대기` 시트 및 `scripts/naver_blog_local_runner.py`는 변경하지 않습니다.
- 실제 Telegram/GitHub/Naver end-to-end 테스트는 토큰과 PC 로그인 세션이 필요하므로 저장소 커밋만으로 성공을 주장하지 않습니다.
