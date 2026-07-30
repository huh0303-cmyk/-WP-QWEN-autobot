# 다국어(영/일/스/베) 초급 단어 퀴즈 - 하루 2회 자동 발행

기존 TOPIK 한국어 퀴즈 파이프라인과 동일한 구조입니다. 이 폴더 전체를
본인 GitHub 저장소에 그대로 커밋하시면 됩니다 (기존 27사이트/TOPIK 리포에
합쳐도 되고, 새 리포를 파도 됩니다).

## 폴더 구조
```
.github/workflows/daily_multilang_quiz.yml   # 스케줄러 (하루 2회: 아침/저녁)
scripts/make_quiz_short_multi.py             # 영상 생성 본체 (영/일/스/베 4개 언어)
scripts/common.py                            # 언어별 제목/설명 메타데이터
scripts/upload_youtube.py
scripts/upload_tiktok.py
scripts/upload_facebook.py
scripts/prepare_public_urls.py               # 인스타/스레드용 공개 URL 준비
scripts/upload_instagram.py
scripts/upload_threads.py
data/words_en.csv, words_ja.csv, words_es.csv, words_vi.csv   # 단어 데이터
assets/tick.mp3, tick_last.mp3, correct.mp3  # 효과음
requirements.txt
```

## 스케줄 안내
- **아침**: 07:00 KST ±1시간 랜덤 (06:00~08:00 사이 실제 실행, cron `0 21 * * *` UTC + 최대 2시간 랜덤 대기)
- **저녁**: 19:00 KST ±1시간 랜덤 (18:00~20:00 사이 실제 실행, cron `0 9 * * *` UTC + 최대 2시간 랜덤 대기)
- 매 실행마다 **한국어/영어/일본어/스페인어/베트남어 각 5문항짜리 영상 1개씩 (총 5개)** 생성 후
  구글드라이브 저장 + 전 채널 업로드 시도 (한국어는 소셜 업로드 제외, 드라이브 저장만)
- Actions 탭 → "Multilang Quiz Daily Auto-Publish" → **Run workflow** 버튼으로
  스케줄 기다리지 않고 즉시 1회 테스트 실행 가능

## 채널별 준비물 (GitHub Secrets에 등록)

Settings → Secrets and variables → Actions → New repository secret

이미 TOPIK 파이프라인에서 유튜브/틱톡/페이스북/인스타/스레드 Secrets를
등록해두셨다면 **그대로 재사용**하시면 됩니다 (같은 채널에 발행하는 경우).
언어별 별도 채널을 쓰고 싶으시면 `scripts/upload_*.py`에서 언어별로
다른 Secrets를 매핑하도록 조정해드릴 수 있어요.

### 0. Google Drive 저장 (언어별 폴더에 자동 저장) — 가장 먼저 이것부터 설정 권장

매 실행 시 생성된 영상을 아래 폴더에 자동 저장합니다:
- 영어: https://drive.google.com/drive/folders/1m8PuFBuM0RoMmhNK6pZT_zFyR8E0yCiu
- 일본어: https://drive.google.com/drive/folders/1vBfhkO1s61lRfb6-HAbZYPlGhrn8Gw5G
- 스페인어: https://drive.google.com/drive/folders/1akto0rTIvAsIIyHIuJn4Wcy6PXuMXTO0
- 베트남어: https://drive.google.com/drive/folders/11eBiiJSuBe1-COitPRrJhG04IiWUOG4l

GitHub Actions는 사람이 브라우저로 로그인할 수 없어서, "서비스 계정(Service Account)"이라는
로봇 계정 방식으로 인증합니다. 설정은 1회만 하면 됩니다.

**1단계 — 서비스 계정 생성**
1. https://console.cloud.google.com → 프로젝트 선택 (없으면 새로 생성)
2. "API 및 서비스" → "라이브러리" → `Google Drive API` 검색 → 사용 설정
3. "API 및 서비스" → "사용자 인증 정보" → "사용자 인증 정보 만들기" → **서비스 계정**
4. 이름 아무거나 입력(예: `multilang-quiz-uploader`) → 만들고 계속하기 → 완료

**2단계 — 키(JSON) 발급**
1. 방금 만든 서비스 계정 클릭 → "키" 탭 → "키 추가" → "새 키 만들기" → **JSON** 선택
2. JSON 파일이 자동 다운로드됨 (이 파일 내용 전체가 필요합니다)

**3단계 — 폴더를 서비스 계정과 공유**
1. JSON 파일 안의 `client_email` 값 복사 (예: `multilang-quiz-uploader@프로젝트명.iam.gserviceaccount.com`)
2. 위 4개 구글드라이브 폴더 **각각**에서 우클릭 → 공유 → 방금 복사한 이메일 추가 → 권한 **편집자**로 설정
   (4개 폴더 전부 반복)

**4단계 — GitHub Secrets 등록**
1. 다운로드된 JSON 파일을 텍스트 에디터로 열어서 전체 내용을 복사
2. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret
3. Name: `ML_GDRIVE_SERVICE_ACCOUNT_JSON`
4. Value: JSON 파일 내용 전체를 그대로 붙여넣기 (중괄호 포함 전체)

이렇게 하면 다른 소셜 채널 Secrets를 하나도 안 채워도, 매 실행마다 영상이 지정된
구글드라이브 폴더에 `2026-07-31_AM_quiz_en_beginner.mp4` 같은 이름으로 자동 저장됩니다.

**참고**: 한국어(TOPIK) 영상용 폴더 링크도 주셨는데, 그건 별도 저장소/스크립트
(`make_quiz_short.py`)에서 관리되고 있어서 이 패키지에는 포함하지 않았습니다.
그쪽에도 같은 방식으로 Google Drive 저장을 붙이고 싶으시면 말씀해주세요 — 그 저장소에
동일한 `upload_drive.py`를 추가해드릴 수 있습니다.

---

### 1. YouTube (완전 자동, 비공개로 업로드 → 검토 후 공개 전환)
1. https://console.cloud.google.com → 새 프로젝트
2. "API 및 서비스" → "라이브러리" → YouTube Data API v3 사용 설정
3. "사용자 인증 정보" → OAuth 클라이언트 ID 생성 (유형: 데스크톱 앱)
4. 로컬 PC에서 1회만 인증 흐름을 돌려 refresh_token 발급
5. Secrets 등록: `ML_YT_CLIENT_ID`, `ML_YT_CLIENT_SECRET`, `ML_YT_REFRESH_TOKEN`

### 2. TikTok (초안함 자동 전송, 최종 게시는 본인)
1. https://developers.tiktok.com → 앱 등록
2. Content Posting API 스코프(video.publish) 신청
3. OAuth로 본인 계정 연동 → access_token 발급
4. Secrets 등록: `ML_TIKTOK_CLIENT_KEY`, `ML_TIKTOK_CLIENT_SECRET`, `ML_TIKTOK_ACCESS_TOKEN`

### 3. Facebook 페이지 (완전 자동, 바로 공개됨)
1. https://developers.facebook.com → 앱 생성
2. 본인 페이지 관리자 권한으로 페이지 액세스 토큰 발급 (장기 토큰 교환 권장)
3. Secrets 등록: `ML_FB_PAGE_ID`, `ML_FB_PAGE_ACCESS_TOKEN`

### 4. Instagram / 5. Threads (앱 심사 필요, 초안함 없이 바로 공개됨)
1. Instagram 계정을 Business/Creator로 전환 + Facebook 페이지 연결
2. Meta 개발자 앱에서 Instagram Graph API / Threads API 권한 신청 → **앱 심사** 필요
3. 영상이 "공개 URL"에서 다운로드 가능해야 하므로, `prepare_public_urls.py`가
   자동으로 GitHub Release에 mp4를 올리고 그 다운로드 URL을 사용합니다
   (별도 설정 불필요, `GITHUB_TOKEN`은 Actions가 자동 제공)
4. Secrets 등록: `ML_IG_USER_ID`, `ML_IG_ACCESS_TOKEN`, `ML_THREADS_USER_ID`, `ML_THREADS_ACCESS_TOKEN`

## 심사 전 임시 운영 방법
Instagram/Threads는 심사가 끝날 때까지 `continue-on-error: true`로 설정해뒀기 때문에
나머지 채널(YouTube/TikTok/Facebook) 업로드에는 지장 없이 정상 진행됩니다.
심사 기다리는 동안은 영상이 outputs 폴더 + GitHub Actions 아티팩트에 저장되니
수동으로 다운받아 두 채널만 직접 올리시면 됩니다.

## 필요 시 조정 가능한 부분
- 문항 수: `make_quiz_short_multi.py --n 5` → 원하는 숫자로 변경
- 카운트다운 초: `--question_seconds 5` (기본 5초)
- 단어 늘리기: `data/words_*.csv`에 `word,category,image_query` 행 추가
- 상단 브랜드명: `make_quiz_short_multi.py` 상단의 `TOP_BRAND = "서울국제대학교"` 수정
- 업로드 문구(제목/설명/해시태그): `scripts/common.py`의 `META` 딕셔너리 수정

## 테스트 방법
Actions 탭 → "Multilang Quiz Daily Auto-Publish" → "Run workflow" 버튼으로
스케줄 기다리지 않고 바로 1회 실행해서 테스트할 수 있습니다.
처음 실행하실 땐 Secrets를 아직 다 안 채우셨어도 괜찮습니다 — 각 업로드 스텝은
해당 Secrets가 없으면 자동으로 건너뛰고, 영상 생성 + 워크플로우 아티팩트 저장까지는
항상 진행됩니다.

## 파일명 규칙
구글드라이브에 저장되는 파일명은 `MM-DD-YYYY-언어코드.mp4` 형식입니다.
예: `07-31-2026-JP.mp4` (일본어), `07-31-2026-EN.mp4` (영어)

| 언어 | 코드 |
|---|---|
| 한국어 | KR |
| 영어 | EN |
| 일본어 | JP |
| 스페인어 | ES |
| 베트남어 | VN |

## 실행 후 이메일 리포트 (huh0303@gmail.com)

매 실행이 끝나면 구글드라이브/유튜브/틱톡/페이스북/인스타/스레드 각각의 성공·실패 내역을
정리해서 이메일로 보내드립니다. Gmail SMTP + 앱 비밀번호 방식(무료, 별도 API 불필요)입니다.

**설정 방법**
1. huh0303@gmail.com 계정에 2단계 인증이 켜져 있어야 합니다 (앱 비밀번호 발급 조건)
2. https://myaccount.google.com/apppasswords 접속 → 앱 이름 아무거나 입력(예: `github-actions`) → 생성
3. 생성된 16자리 비밀번호(공백 없이) 복사
4. GitHub Secrets 등록:
   - `ML_GMAIL_SENDER` = `huh0303@gmail.com`
   - `ML_GMAIL_APP_PASSWORD` = 방금 생성한 16자리 앱 비밀번호

받는 사람 주소는 워크플로우 파일에 `huh0303@gmail.com`으로 고정되어 있습니다. 바꾸고 싶으시면
`.github/workflows/daily_multilang_quiz.yml`의 `ML_REPORT_TO` 값을 수정하시면 됩니다.

이 Secrets를 등록하지 않아도 워크플로우는 정상 진행되며, 이메일 대신 Actions 로그에
같은 내용이 출력됩니다.

## 참고: 한국어(TOPIK) 소셜 업로드 제외 처리
이 패키지는 한국어 영상도 함께 생성해서 지정하신 구글드라이브 폴더에 저장하지만,
유튜브/틱톡/페이스북/인스타/스레드에는 **한국어를 올리지 않도록** 설정해뒀습니다
(이미 별도의 TOPIK 자동화 파이프라인이 같은 채널에 한국어 콘텐츠를 발행 중이라
중복 게시를 막기 위함입니다). 이 판단이 틀렸다면 — 즉 한국어도 이 파이프라인에서
소셜 업로드까지 하길 원하시면 — `scripts/common.py`의 `SOCIAL_LANGS` 목록에
`"ko"`를 추가해달라고 말씀해주세요.
