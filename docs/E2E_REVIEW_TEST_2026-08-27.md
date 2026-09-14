# 4단계 소액 E2E 검증 기록 — 2026-08-27

## 범위와 안전 조건

- 공개 발행 없이 대표 샘플만 실행했다.
- WordPress 1건, Blogger 후보 확인, TOPIK 1문항, SNS 검토 세트 1건, YouTube 비공개 업로드 1건으로 제한했다.
- 신규 API, 신규 구독, 신규 채널은 추가하지 않았다.
- 실제 공급자 청구액은 billing 연결이 없어 추정하지 않는다.

## 실행 결과

| 대상 | GitHub Actions run | 결과 | 검증 내용 |
|---|---:|---|---|
| WordPress | 33081517114 | 성공·추가 검증 필요 | GPT 기반 단일 실행 성공, 결과 아티팩트 생성. 일반 사이트 DRAFT 하드 가드는 테스트로 검증됨. Google Sheet 실행행 자동 기록은 아직 없음. |
| Blogger | 33081556035, 33081822962, 33081907799 | 미완료 | 기존 대상의 최근 10개 원문은 이미 대기열에 있거나 공개 원문이 없어 새 검토행을 만들지 못함. API 생성 호출 전 종료. 이 상태가 성공으로 표시되던 코드를 실패 종료로 수정함. |
| TOPIK | 33081625694 | 생성 성공 | 1문항 영상과 메타데이터 생성, Google Drive 검토 링크 및 아티팩트 생성. |
| SNS 검토 세트 | 33081625694 | 부분 성공 | 플랫폼별 제목·Hook·Caption·CTA·Hashtag와 시차 권장시간 생성. Instagram/Threads는 API 공개 없이 준비됨. TikTok은 토큰 없음으로 건너뜀. Facebook 자격 증명 오류로 DRAFT 업로드 실패. |
| YouTube | 33081625694 | 실패 | private 업로드를 요청했으나 OAuth `unauthorized_client`로 실패. 공개 영상은 생성되지 않음. |

## 테스트 흐름 판정

- 생성: WordPress 및 TOPIK 성공, Blogger는 사용할 새 원문 없음.
- 이미지: TOPIK 승인 Replicate 경로 실행. Blogger는 생성 단계 진입 전 종료.
- 품질검사: WordPress 로컬 정책 테스트 통과. Blogger 신규 결과 없음.
- 중복검사: Blogger 활성 대기열 중복 차단 확인, SNS 플랫폼별 fingerprint 상태 파일 생성.
- 발행대기/비공개: WordPress DRAFT 정책 유지. Instagram/Threads 준비만 성공. YouTube/Facebook 업로드 실패.
- 로그: 각 Actions run과 결과 아티팩트 확인.
- Google Sheet: Blogger 신규 행 없음, WordPress/TOPIK/SNS 실행 결과 자동 기록 없음. 4단계 상태는 `자동화_진행현황`에 별도 기록한다.

## 실행 중 발견·수정한 결함

1. TOPIK 워크플로에 명시적 opt-in 검토 업로드 옵션이 없었다. 기본값 false인 `run_social_review`를 추가했다.
2. SNS 플랫폼 실패가 있어도 전체 워크플로가 성공으로 기록됐다. 실제 실패가 하나라도 있으면 비정상 종료하도록 수정했다.
3. Facebook HTTP 오류 URL에 토큰이 포함돼 결과 아티팩트에 기록될 수 있었다. 알려진 자격 증명과 `access_token` 쿼리 값을 마스킹하도록 수정하고 회귀 테스트를 추가했다.
4. Blogger에 새 원문이 없을 때 성공 종료했다. 실제 대기행이 없으면 실패 종료하도록 수정했다.

## 비용

- 정확한 청구액: **연결 필요** (OpenAI, Gemini, Replicate, ElevenLabs billing 데이터 미연결).
- 확인된 최소 호출 범위: WordPress 본문 1건, TOPIK 본문/플랫폼 문구 1문항, TOPIK 이미지 1건, TOPIK 음성 1문항.
- Blogger 보정 실행은 새 원문 선택 전에 종료되어 생성 API 호출이 없었다.

## 남은 차단 사항

1. YouTube OAuth client/refresh token 조합을 재승인해야 한다.
2. Facebook Page 토큰 권한/유효성을 확인하고 노출 가능성이 있었던 토큰을 회전해야 한다.
3. TikTok 공식 Content Posting 토큰 연결이 필요하다.
4. WordPress/TOPIK/SNS 실행 결과를 `자동화_실행현황`에 자동 기록해야 한다.
5. Blogger 대상별 공개 WordPress 원문을 확보하거나 승인된 기존 `ready` 행을 Blogger 비공개 초안으로 전송해야 한다.

이 차단 사항이 해결되기 전에는 4단계를 완료로 표시하지 않는다.
