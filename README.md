# 통합 블로그 자동발행 허브

> 프로젝트의 고정 운영 범위와 비용 안전 원칙은 [OPERATING_MANDATE.md](OPERATING_MANDATE.md)를 최우선 기준으로 따릅니다.
> 글·제목·이미지·카드뉴스·완료 알림은 [docs/EDITORIAL_AND_MEDIA_MANDATE.md](docs/EDITORIAL_AND_MEDIA_MANDATE.md)를 필수로 따릅니다.

모든 운영 화면, 스케줄 계산과 실행 로그는 한국시간 `Asia/Seoul` 기준입니다. GitHub Actions의 cron 문법과 YouTube API의 `publishAt` 전송값만 서비스 규칙상 UTC를 사용하며, 코드가 자동 변환하므로 사용자는 구글시트에 한국시간만 입력합니다.

Google Sheets를 운영 화면으로, GitHub Actions를 서버로 사용하는 다계정 발행기입니다. 기존 WordPress 27개(A그룹 17, B그룹 8, 신문사 2)는 각 사이트의 발행량·카테고리·페르소나·톤·글자 수·키워드·RSS 설정을 독립적으로 사용합니다. 사이트와 계정 수를 코드에서 제한하지 않습니다.

## 현재 지원 범위

| 플랫폼 | 자동발행 | 실행 위치 | 비고 |
|---|---:|---|---|
| WordPress 27개 | 가능 | GitHub Actions | 현재 운영 중, 실제 공개 URL 검증 |
| Blogger/Blogspot | 가능 | GitHub Actions | Google 공식 Blogger v3 API/OAuth 사용 |
| 네이버 블로그 | 로컬 로그인 필요 | 사용자 PC | 현재 공식 글쓰기 API가 없어 서버 무인발행 불가 |
| 티스토리 | 로컬 로그인 필요 | 사용자 PC | 공식 Open API가 2024년 종료됨 |

네이버는 PC의 Playwright 브라우저 프로필에 사용자가 최초 1회 직접 로그인한 뒤 `scripts/naver_blog_local_runner.py`가 대기열을 처리합니다. 공개 URL을 확인하기 전에는 성공으로 기록하지 않습니다. 티스토리는 아직 `local_login_required`로 보존합니다.

## Google Sheets 운영 탭

- `자동화_사이트설정`: WordPress 포함 전체 사이트별 콘텐츠 설정
- `자동화_플랫폼계정`: Blogger·네이버·티스토리 계정/목적지 등록
- `자동화_발행대기`: 작성된 글, 처리 상태, 공개 URL, 오류 기록
- `자동화_실행현황`: 실행 이력
- `자동화_황금키워드`: 키워드 후보와 점수
- `자동화_RSS`: 신문사별 RSS 출처
- `자동화_유튜브채널`: 플리 5개·지식 5개의 채널 ID, 주기, 예약 지연, 주제·언어·톤, 다음 실행
- `자동화_유튜브실행`: 중앙 스케줄러의 디스패치 및 영상 공개 URL 기록

## YouTube 10채널 자동화

플레이리스트 채널 `globalmusic`, `healing`, `starbucks`, `mbb`, `kpop`과 지식채널 `nasa`, `history`, `invention`, `silent_era`, `retro_reels`를 기본 등록합니다. 등록 행을 추가하면 같은 구조로 채널 수를 늘릴 수 있습니다.

**YouTube Hub — 10 channel scheduler**가 매시간 시트를 읽고 실행 예정 채널을 한 번에 최대 1개만 호출합니다. 채널별 2~3일 간격, 허용 시간대와 예약 공개 지연을 따로 설정하므로 영상이 한꺼번에 공개되지 않습니다. 예전 플리 고정 cron과 지식채널 cron은 비활성화해 중복 생성·발행을 막았습니다.

업로드 직전 OAuth 계정의 실제 YouTube channel ID를 시트/등록부의 기대 ID와 비교합니다. 다르면 `OAuth channel mismatch`로 즉시 중단하므로 다른 채널에 잘못 올리지 않습니다. 텍스트는 `AI_TEXT_PROVIDER=openai`, AI 이미지 생성은 차단 상태이며 무료 스톡·퍼블릭도메인·기존 이미지 소스만 허용됩니다.

`자동화_플랫폼계정`에는 `account_id`, `platform`, `site_id`, `display_name`, `destination_id`, `editor_url`, `auth_profile`, `enabled`, `notes`를 입력합니다. Blogger의 `destination_id`는 숫자 blog ID이고 `auth_profile`은 OAuth 비밀키 묶음의 이름입니다.

`자동화_발행대기`에서 `status`를 `ready`로 설정하면 수동 GitHub Action **Automation Hub — platform publish**가 처리합니다. `publish_now=FALSE`이면 Blogger 초안으로 저장합니다.

블로그스팟 자동 일정은 매시간 17분(UTC cron, 실제 표시는 KST)에 대기열을 확인하고 한 번에 최대 1건만 처리합니다. 저장소 변수 `BLOGGER_AUTOPUBLISH_ENABLED=true`일 때만 예약 실행되므로, 먼저 `scripts/blogger_verify_account.py` 또는 수동 Action으로 OAuth·blog ID를 검증한 뒤 켭니다. 예약 실행은 `PLATFORM_FILTER=blogger`로 고정되어 네이버·티스토리 행을 변경하지 않습니다. 발행 성공은 Blogger가 돌려준 URL을 실제로 열어 제목까지 확인한 뒤에만 시트에 기록합니다.

**Automation Hub — WordPress to Blogger rewrite**는 최근 WordPress 공개글 중 아직 사용하지 않은 원문을 골라 문장 치환이 아닌 새 검색의도·목차·사례·체크리스트·FAQ 구조로 다시 작성합니다. 원문과의 텍스트 유사도가 `0.68`을 넘으면 차단하고, Pexels 또는 Pixabay 무료 사진을 정확히 1장만 넣어 출처를 표시합니다. 무료 사진이 없으면 유료/AI 이미지로 폴백하지 않고 실패합니다. 생성 결과는 항상 `publish_now=FALSE` 검토 대기열로 시작합니다.

## 네이버 블로그 최초 1회 준비와 실행

네이버 로그인 비밀번호는 시트나 저장소에 넣지 않습니다. Google Cloud에서 OAuth 클라이언트를 `데스크톱 앱` 유형으로 하나 만들고 JSON을 내려받은 뒤 로컬 연결 도구를 실행합니다. 연결 파일은 `.local/google_sheets_oauth.json`에 저장되어 GitHub에 올라가지 않습니다. `SHEET_ID`만 PC 환경변수로 지정합니다.

```powershell
pip install playwright google-api-python-client google-auth
python -m playwright install chromium
pip install google-auth-oauthlib
python scripts/setup_google_sheets_local.py "C:\Users\사용자\Downloads\client_secret.json"
$env:SHEET_ID="12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI"
python scripts/naver_blog_local_runner.py login --site-id naver_main
python scripts/naver_blog_local_runner.py run --site-id naver_main --max-jobs 1
```

`자동화_플랫폼계정`에 플랫폼 `naver`, 고유 `site_id`, 블로그 ID인 `destination_id`, 글쓰기 주소인 `editor_url`, `enabled=ON`을 입력합니다. 계정을 추가할 때마다 다른 `site_id` 행을 추가하면 수 제한 없이 별도 로그인 프로필로 관리됩니다. `자동화_발행대기`에는 같은 `site_id`와 `status=ready`인 글을 넣습니다. 첫 실전은 `publish_now=FALSE`로 편집기 입력만 확인하고, 검토가 끝난 뒤 `TRUE`로 1건만 시험하는 것을 권장합니다.

## 비용 안전장치

- `OPENAI_IMAGE_ENABLED=false`
- `PAID_IMAGE_GENERATION_ENABLED=false`
- 새 플랫폼 발행 흐름은 이미지 API를 호출하지 않음
- WordPress 27개는 본문·대표이미지 모두 `none / 0 / 0`
- 기존 예약 이미지·썸네일 생성 워크플로는 자동 일정 비활성화
- OpenAI 이미지 함수는 기존 환경변수 값과 관계없이 항상 차단
- 현재 함께 만드는 유튜브 허브만 보유 원본·무료 공개자료를 사용할 수 있으며 AI 이미지 API는 금지

## Blogger 최초 1회 준비

1. Google Cloud에서 Blogger API를 활성화합니다.
2. 공용 Drive/Sheets refresh token을 덮어쓰지 말고, 데스크톱 OAuth JSON으로 Blogger 전용 토큰을 발급합니다.

   ```bash
   python scripts/setup_blogger_oauth_local.py /path/to/desktop-oauth-client.json
   ```

3. 생성된 `.local/blogger_oauth.json`의 값을 GitHub Secrets
   `BLOGGER_GOOGLE_CLIENT_ID`, `BLOGGER_GOOGLE_CLIENT_SECRET`,
   `BLOGGER_GOOGLE_REFRESH_TOKEN`에 각각 저장합니다. 토큰 값을 로그, 시트,
   문서 또는 저장소에 붙여넣지 않습니다.
4. `자동화_플랫폼계정`의 Blogger 행에서 `auth_profile=blogger`, blog ID,
   `enabled=ON`을 확인합니다.
5. 기존 ready 행 하나만 `publish_now=FALSE` 상태로 전송해 실제 Blogger
   DRAFT ID와 편집 URL을 확인합니다. PUBLIC 전환은 별도 승인 없이는 금지합니다.

여러 Google 계정은 `auth_profile`을 예를 들어 `BRAND2`로 지정하고 `BRAND2_GOOGLE_CLIENT_ID`, `BRAND2_GOOGLE_CLIENT_SECRET`, `BRAND2_GOOGLE_REFRESH_TOKEN` 형태로 별도 secret을 연결할 수 있습니다. GitHub Actions에는 사용할 프로필 secret을 명시적으로 추가해야 합니다.

## 보안 주의

과거 Git 기록에 들어갔던 네이버 및 커머스 자격증명은 코드에서 제거됐지만 공개 Git 기록 자체에는 남아 있을 수 있습니다. 해당 비밀번호/API 키를 교체하기 전에는 네이버 로그인 자동화를 실행하지 마세요. 비밀번호나 토큰은 시트와 코드에 쓰지 않고 GitHub Secrets만 사용합니다.

## 점검

```bash
python -m unittest discover -s tests -v
python -m automation_hub.cli validate
```
