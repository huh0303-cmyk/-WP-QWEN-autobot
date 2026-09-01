# Korea 365 WordPress 27 Control Center

WordPress 27개를 한 화면에서 다루는 로컬 우선 운영 앱이다. 일반 운영에는 Codex를 호출하지 않는다.

## 책임 분리

- ChatGPT/OpenAI API: 기사 초안 작성
- Control Center: 작업 상태, 품질점수, 중복 방지, WordPress 비공개 초안 저장
- 사용자: WordPress 편집 화면에서 최종 검토
- Codex: 앱 개발·수정·장애 분석에만 사용

현재 MVP에는 공개 발행 메서드가 없다. `APPROVED`는 사용자 검토 기록이며 글을 공개하지 않는다.

## 실행

```powershell
python -m pip install -r requirements-control-center.txt
$env:OPENAI_API_KEY = "본인의 API 키"
$env:CONTROL_CENTER_TEXT_MODEL = "사용할 OpenAI API 모델"
$env:KHEALTH365COM = "해당 WP application password"
# 나머지 사이트도 config/automation_hub_sites.json의 secret_name 기준으로 설정
python run_control_center.py
```

브라우저에서 `http://127.0.0.1:8766`을 연다. 서버는 외부 네트워크가 아닌 `127.0.0.1`에만 바인딩된다.

## 상태 흐름

```text
CREATED
  -> GENERATING
  -> GENERATED
  -> QUALITY_PASSED (75점 이상) 또는 QUALITY_FAILED
  -> DRAFTING
  -> WP_DRAFTED
  -> APPROVED 또는 REJECTED
```

## 안전장치

- `(플랫폼, 사이트, 정규화 키워드, 콘텐츠 버전)` 고유키로 중복 작업 차단
- SQLite `BEGIN IMMEDIATE`와 WAL로 단일 작업 소유권 확보
- 결정적 WordPress slug로 불확실한 HTTP 결과 재조회
- WordPress API payload의 상태를 항상 `draft`로 강제
- 응답 상태가 `draft`가 아니면 성공 처리하지 않음
- 품질점수 75점 미만이면 WordPress API를 호출하지 않음
- 앱 코드에는 공개 발행 API가 없음
- 이미지 후보는 0~2개이며 현재 MVP는 이미지 생성 비용을 사용하지 않음

## 인증

GitHub Secrets는 값을 다시 읽을 수 없으므로 로컬 앱에 자동 복사할 수 없다. 운영 버전에서는 OS 비밀 저장소 또는 전용 서버 Secret Manager를 연결한다. 비밀번호와 API 키는 Git, SQLite, 로그, 화면에 저장하지 않는다.
