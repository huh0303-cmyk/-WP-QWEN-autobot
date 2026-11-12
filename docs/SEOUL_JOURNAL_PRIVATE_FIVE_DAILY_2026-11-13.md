# 서울저널 최신 운영 지시 — 하루 5편 이상 비공개 (2026-11-13)

**최신 사용자 지시가 기존 2026-11-09 하루 3편 공개 발행 정책보다 우선한다.**

- 대상: 서울저널 YouTube `@seouljournal1`, channel `UChRUdHZlXSjftAqBtdDNEWA`. 업로드 전 OAuth 채널 ID 재확인.
- 목표: **매일 최소 5편의 서로 다른 정치 Shorts 제작 및 PRIVATE 업로드**. 조건 미충족은 BLOCKED로 보고하며, 숫자를 채우기 위한 허위/중복 업로드 금지.
- 공개 자동 발행 금지. `privacyStatus=private`를 업로드 요청에 명시하고 API 응답 및 재조회로 확인. 사용자의 별도 명시적 승인 없이 public/unlisted 변경 금지.
- 주제: 이재명, 한동훈 등 주요 정치인의 **당일 확인 가능한 정치 공방, 공개 충돌, 국회 질의·답변, 수사/특검 관련 발언**. 일반 사회·스포츠·쇼핑·월급방위대 등 무관한 이슈 제외.
- 사실 확인: 1차 원본 영상/발언·일시·발언자, 반론/답변, 맥락, 법적 상태를 검증. 의혹은 의혹으로 귀속. 사실 없는 충돌을 만들지 말 것.
- 영상: 사용자 KNN 참고 영상 `1DE5qibASjc`, `MShzimoRGX8`의 실제 발언/응답 중심 뉴스 편집 *형식* 참고. 영상·음성·로고 복제 금지. 원본 클립 재사용권 확인.
- 썸네일: 사용자 제공 고조회수 뉴스 썸네일의 가독성/대비/인물 대립 구도 참고. 실제 허가된 정치인 사진, 검증된 인용문, 큰 자막. 합성 얼굴을 실제 사진으로 오인시키지 말 것.
- 실제 음성/영상이 확보되면 원본 발언 우선; 설명용 TTS는 분리 표기. 말에 맞춘 중앙 자막, 얼굴을 가리는 불투명 상자 금지. 마지막 중립적 의견 질문.
- 권장 다섯 슬롯: KST 08:00–10:00, 11:00–13:00, 14:00–16:00, 17:00–19:00, 20:00–23:00. 최신 속보 추가 슬롯 허용. 이는 **운영 목표**이며 실제 Actions schedule 반영은 별도 작업.
- 필수 검증 영수증: video_id, channel_id, `privacyStatus=private`, source URLs/timecodes/rights, photo attribution, unique story fingerprint, narration/caption QA, upload timestamp. 업로드 성공과 조회수 성과는 별도.
- 실패 시 해당 슬롯만 재시도. YouTube 업로드 결과가 불명확하면 채널 조회 후 중복 방지. 다른 계정의 OAuth 사용 금지.

## 현재 구현과의 차이 (미완료)
- `docs/SEOUL_JOURNAL_PUBLIC_POLICY_2026-11-09.md`에는 3 PUBLIC/day가 남아 있으므로 실제 실행 워크플로와 스케줄, privacyStatus를 교체해야 한다.
- `scripts/seoul_journal_daily_queue.py`에는 7건 후보 큐 및 구형 ElevenLabs-only 문구가 남아 있다.
- `scripts/seoul_journal_shorts_pipeline.py`는 첫 네이버 정치 기사 선택/AI 낭독형 경로다. 실제 국회 발언 클립 중심 별도 렌더 경로 필요.
- **이 문서 저장만으로 5편 자동 업로드가 활성화되지는 않는다.** 비공개 업로드 시크릿/권한, 실제 Actions 연결, 샘플 영상 검증 후 활성화한다.
