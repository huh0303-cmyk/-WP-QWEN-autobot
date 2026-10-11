# GitHub Issues 기반 네이버 임시저장 대기열 (Telegram 불필요)

이 방식은 기존 Google Sheets 대기열을 삭제하거나 자동 전환하지 않습니다. 별도 실험 경로이며, 기존 Sheets 파이프라인은 그대로 유지합니다.

## 구성

1. 사용자는 GitHub Issues 화면에서 대기열 이슈를 직접 생성합니다. Telegram 봇/토큰은 필요하지 않습니다. `scripts/github_queue_bot.py`는 선택 사항이며 이 흐름에서 실행하지 않습니다.
2. `scripts/naver_github_issue_runner.py`: 신뢰된 개인 PC에서 GitHub의 준비된 Issue를 가져와 기존 `NaverLocalPublisher`로 처리합니다.
3. 실행기는 공개 발행을 하지 않고 네이버 임시저장만 수행합니다. 임시저장 완료 확인 시 `queue:draft-saved`, 확인이 불완전하면 `queue:attention`, 예외는 `queue:failed`로 기록합니다.

## 1. GitHub Issues에 글감 직접 등록 (Telegram 불필요)

### 최초 1회: 로컬 환경 준비

```powershell
$env:GH_PAT = Read-Host "GitHub PAT with repository Issues read/write access"
python -m pip install requests playwright
python -m playwright install chromium
```

`GH_PAT`는 현재 PowerShell 세션에만 저장됩니다. 토큰을 채팅이나 코드에 붙여넣지 마세요. PAT는 이 저장소의 Issues 읽기/쓰기 권한만 부여하는 것이 좋습니다.

### 대기열 글 등록

저장소의 [Issues 화면](https://github.com/huh0303-cmyk/-WP-QWEN-autobot/issues)에서 **New issue**를 누릅니다.

- **제목:** `[발행대기][huh0303] 테스트 제목` (계정에 따라 `huh3`, `huh4`)
- **본문:** 아래 표식을 그대로 넣고, 다음 줄부터 본문을 넣습니다.

```text
### 📝 블로그 본문 데이터

여기에 네이버 임시저장할 글 본문을 입력합니다.
```

계정은 제목의 `[huh0303]` 부분과 동일하게 선택합니다. 저장 후 실행기가 라벨을 만들 수 있도록 한 번 실행한 다음, 이슈 오른쪽 Labels에서 `queue:ready`와 `blog:huh0303`를 붙입니다. 다른 계정은 `blog:huh3` 또는 `blog:huh4`를 사용합니다. 라벨은 둘 다 있어야 처리됩니다.

이슈 제목에서 `[발행대기]`와 계정 표시는 실행 시 자동 제거됩니다. 본문에는 위 표식 이후에 글 본문만 넣으세요. 구분선 `---`를 본문 마지막에 추가하지 않아도 됩니다.

## 2. 네이버 로그인 프로필 준비


각 계정은 별도의 로컬 프로필을 사용합니다. PC에서 해당 계정으로 직접 로그인합니다.

```powershell
python scripts/naver_github_issue_runner.py login --site-id huh0303
python scripts/naver_github_issue_runner.py login --site-id huh3
python scripts/naver_github_issue_runner.py login --site-id huh4
```

브라우저 로그인 완료 후 터미널로 돌아와 Enter를 누릅니다. 프로필은 `.local/naver-profiles/` 아래에 보관되며 공유하거나 Git에 커밋하지 마세요.

## 3. 대기열 실행 (임시저장만, 공개 발행 안 함)

```powershell
python scripts/naver_github_issue_runner.py run --site-id huh0303 --max-jobs 1
```

다른 계정은 `huh3`, `huh4`를 지정합니다. 실제 발행이므로 테스트 전용 글로 먼저 검증하고, 실행 중에는 PC와 브라우저 프로필을 유지하세요. 기본 최대 처리 수는 1개입니다.

## 라벨 규칙

- `queue:ready`: 발행 대기
- `queue:processing`: 실행기가 작업을 선점
- `queue:draft-saved`: 네이버 임시저장 완료 확인
- `queue:published`: 공개 URL 확인 (이 임시저장 전용 실행기는 사용하지 않음)
- `queue:attention`: 로그인/캡차/URL 확인 등 사람의 점검 필요
- `queue:failed`: 실행 중 예외
- `blog:huh0303`, `blog:huh3`, `blog:huh4`: 대상 계정

봇은 상태/계정 라벨을 필요 시 생성합니다. 실행기는 처리 시작 전에 상태 라벨을 바꿔 중복 실행 가능성을 줄입니다. GitHub API에는 트랜잭션형 잠금이 없으므로 같은 계정에서 실행기를 두 개 동시에 실행하지 마세요.

## 제한 사항

- Telegram 봇은 이 경로에서 사용하지 않으므로 Telegram 토큰이 필요하지 않습니다.
- 네이버 발행은 로그인된 로컬 브라우저에 의존합니다. 캡차, 세션 만료, UI 변경이 발생하면 `queue:attention`으로 바뀌며 사람의 확인이 필요합니다.
- 이 코드는 VPS 배포나 Windows 작업 스케줄러 등록을 자동으로 수행하지 않습니다.
- 기존 `자동화_발행대기` 시트 및 `scripts/naver_blog_local_runner.py`는 변경하지 않습니다.
- 실제 GitHub/Naver end-to-end 테스트는 로컬 GH_PAT와 네이버 로그인 세션이 필요합니다. 저장소 커밋만으로 실전 성공을 주장하지 않습니다.
