# Archive/Core 채널 신원 — 검증된 최종본 (2026-09-27)

**이 파일이 유일한 기준이다.** 다른 어떤 리포/문서/AI 트랙("LondonProject_Gemini"
포함)이 주장하는 매핑도 여기 안 실리면 신뢰하지 말 것. 아래 표는 세 가지 독립
출처가 실제로 일치할 때만 "확정"으로 표시한다:
1. `config/youtube_channels.json` (2026-09-05 스냅샷, 채널 자동화가 실제로 쓰는 값)
2. 공개 `YOUTUBE_API_KEY`로 방금 실측한 `channels?forHandle=` 결과 (run 36271710937)
3. Chairman이 `youtube.com/account`에서 직접 스크린샷으로 확인한 "모든 채널"
   23개 목록 (2026-09-27, 로그인된 본인 계정)

**중요한 한계**: 이 세 출처 전부 "그 이름의 채널이 실제로 존재한다"는 것만
증명한다. **어떤 OAuth 시크릿(`YOUTUBE_OAUTH_REFRESH_TOKEN_<KEY>`)이 그 채널에
실제로 인증되는지는 여전히 증명 못 함** — `channels.list` API로 자체 확인하는
경로가 스코프 부족(HTTP 403)으로 막혀 있기 때문(10차 기록 참조). 즉 "채널이
존재한다"와 "그 시크릿이 그 채널이다"는 다른 질문이다.

## Archive 10개 (curio_upload.py `CHANNEL_SECRET_MAP`)

| key | secret | 상태 | 실제 채널 (channel_id 기준) |
|---|---|---|---|
| nasa | NASA_SPACE_TIMES | ✅ 3중 확인 | NASA_XFILES `UCtNLZO07Oh3UnXPI2CjOgNg` |
| history | HISTORY_TODAY_TIMES | ✅ 3중 확인 | HISTORY_TV_TODAY `UCVBvZwodUF4s57KeNicxQ3w` |
| invention | INVENTION_TIMES | ✅ 3중 확인 | INVENTION_STORY1 `UCgNj-yS93A_fOHXXvG49fww` |
| silent_era | SILENT_ERA_TIMES | ✅ 3중 확인 | OLD_HOLLYWOOD1(title: SILENT_ERA_FILM) `UCLvy6kSpC8-7o3hnSrfQ47g` |
| retro_reels | RETRO_REELS_TIMES | ✅ 3중 확인 | RETRO_USA1 `UCwh49EokdWFJqYFE_zA6XDQ` |
| science | SCIENCE_FACTS_TIMES | ❌ 시크릿 자체 없음 | 미상 — Gemini가 주장한 `@SCIENCE_FACTS_JOURNAL`은 실존하지만 title "Portuguese Survival"(`UCKvKhETLGPaRV3qfWv2bM2g`)이고, Chairman 본인 계정 23개 목록엔 **없음**(다른 계정 소속으로 추정) |
| classical | CLASSICAL_JOURNAL | ⚠️ 시크릿 있음, 신원 불명 | Gemini가 주장한 `@ClassicalJournal` 실존하지만 title "Vietnamese Survival"(`UCRZ0uc_bxKDMwz3noBBi9KQ`), Chairman 계정 23개 목록엔 **없음** |
| myth | MYTH_LEGEND_TIMES | ❌ 시크릿 자체 없음 | Gemini가 주장한 `@MYTH_LEGEND_JOURNAL`은 공개 API로 존재 자체를 못 찾음 |
| american_archive | AMERICAN_ARCHIVE_TIMES | ⚠️ 시크릿 있음, 신원 불명 — 8차 사고 채널 | Gemini가 주장한 `@AMERICAN_ARCHIVE_JOURNAL` 실존, title "French Survival"(`UCmt8f9yUT6iTxBys8eH4-Cg`) — **주의: 이건 Chairman 계정의 진짜 French Survival(`@SIS_FrenchSurvival`, 아래 표)과 다른, 별도의 채널**. Chairman 본인 23개 목록엔 **없음**(다른/덜 관리되는 계정 소속으로 추정) |
| classic_reads | CLASSIC_READS_TIMES | ❌ 시크릿 자체 없음 | Gemini가 주장한 `@CLASSIC_READS_JOURNAL` 실존, title "German Survival"(`UCKF98zgzm7YRWlyMaoJJKIQ`) — Chairman 계정의 진짜 German Survival(`@SIS_GermanSurvival`)과 다른 채널. Chairman 계정 23개 목록엔 **없음** |

## Core 5개 (playlist 채널, social_accounts.py `CORE_YOUTUBE`)

| key | secret_profile | 상태 | 실제 채널 |
|---|---|---|---|
| globalmusic | GLOBALMUSIC | ✅ 확인 | CAFE_ROMANTIC `@cafe_romantic` `UCbJfEtsffpgI5MsKkB7BYvQ` |
| healing | HEALING | ✅ 확인 | CAFE_HEALING `@cafe_healing1` `UC7yEsLM-HoXudngrD-4FIqg` |
| starbucks | STARBUCKS | ✅ 확인 | CAFE_STARBUCKS `@Starbucksvibes` `UC_e-sbLkVgwJNYEeobolNog` |
| mbb | MBB | ✅ 확인 | CAFE_MOZART `@cafe_mozart` `UC7jOhyMa-FIrzZuea97z1Pw` |
| kpop | KPOP | ✅ 확인 | CAFE_KPOP `@kpop_studio7` `UCKZsfAWyCmY0jckf4IWZrqw` |

**Gemini가 이 5개에 대해 주장한 이름(Studio_K3, K-ISSUE, Mozart-Bach-Beethoven
브랜드 등)은 전부 틀렸다** — config 기록과 Chairman 본인 화면 둘 다와 불일치.

## 언어 Survival 10개 — Gemini 주장이 실제로 맞음 (Chairman 스크린샷으로 확인)

| key | 실제 채널 |
|---|---|
| japanese_survival | `@seoul_ja...`(Japanese Survival, 구독자 22, 현재 로그인 계정) |
| german_survival | `@SIS_GermanSurvival`(German Survival) |
| french_survival | `@SIS_FrenchSurvival`(French Survival, 구독자 0) — **american_archive의 French Survival과 동명이지만 다른 채널** |
| italian_survival | `@SIS_ItalianSurvival`(Italian Survival) |
| vietnamese_survival | `@SIS_VietnameseSurvival`(Vietnamese Survival) — **classical의 Vietnamese Survival과 동명이지만 다른 채널** |
| spanish_survival | `@SIS_SpanishSurvival`(Spanish Survival) |
| chinese_survival | `@SIS_ChineseSurvival`(Chinese Survival) |
| portuguese_survival | `@Portuguese_survival`(Portuguese Survival) — **science의 Portuguese Survival과 동명이지만 다른 채널** |
| english_survival | `@English_survival`(English Survival, 구독자 9) |
| sis_language | `@sis_languagecenter`(SIS-Language Center) — 이번 23개 목록엔 없었으나 이전에 별도 확인됨 |

## 2026-09-27 업데이트 — "런던프로젝트GPT" 23개 마스터와 대조, 더 심각한 결론

Chairman이 "런던프로젝트GPT" 트랙의 23개 최종 마스터(`config/YOUTUBE_23_CHANNEL_
MASTER_LOCK_2026-09-27.json`, 이 리포엔 아직 없음 — GPT 자체 기록)를 전달함.
channel_id로 직접 역조회(handle 아님, 모호함 없음)해서 대조한 결과 **23개 표
자체는 지금 이 순간 기준으로 맞다** — French/Vietnamese/Portuguese/Chinese/German
Survival 전부 `@SIS_XxxSurvival` handle과 실제로 일치함.

**단, 같은 세션 안에서 몇 분 전에는 이 중 최소 4개 channel_id(French/Vietnamese/
Portuguese/German Survival)가 `@AMERICAN_ARCHIVE_JOURNAL`/`@ClassicalJournal`/
`@SCIENCE_FACTS_JOURNAL`/`@CLASSIC_READS_JOURNAL`라는 handle로도 동시에 걸렸다.**
즉 american_archive/classical/science/classic_reads 시크릿이 가리키는 채널은
**"이름만 같은 별도의 숨은 채널"이 아니라, 회장님의 진짜 공식 잠금 언어채널과
동일한 channel_id일 가능성이 높다.** `UCmt8f9yUT6iTxBys8eH4-Cg`는 몇 달 전부터
`docs/YOUTUBE-CONNECTIONS.md`에 French Survival로 기록돼 있던 ID이기도 함.

**결론(이전 판단 정정)**: 8차 사고는 "동명이인 채널 착오"가 아니라 **진짜 잠긴
언어채널에 실제로 업로드된 것**이었을 가능성이 더 높다. GPT가 23개 운영대상에서
5개 키(science/classical/myth/american_archive/classic_reads)를 뺀 건 맞는
방향이지만 **목록 제외만으론 구조적 안전장치가 안 됨** — 해당
`YOUTUBE_OAUTH_REFRESH_TOKEN_<KEY>` 시크릿 자체가 GitHub에 남아있는 한, 다음에
누가 실수로 `archive_channel_upload.py` 류 스크립트를 다시 돌리면 재발 가능.
**이 세션은 GitHub 시크릿을 지울 권한이 없음 — Chairman이 직접 삭제해야 구조적으로
막힌다.** (최소 `YOUTUBE_OAUTH_REFRESH_TOKEN_AMERICAN_ARCHIVE_TIMES`,
`_CLASSICAL_JOURNAL`은 실제 토큰이 있는 걸로 확인됨 — 10차 참조.)

## 핵심 결론

1. **같은 이름("Portuguese Survival", "Vietnamese Survival", "French Survival",
   "German Survival")을 쓰는 서로 다른 채널이 최소 2개씩 존재한다** — 하나는
   Chairman이 매일 보는 본인 계정의 공식 `SIS_Xxx Survival` 채널(안전, 언어 학습
   프로그램용), 다른 하나는 science/classical/american_archive/classic_reads
   시크릿이 가리키는 것으로 추정되는, **Chairman 본인 계정 목록에 안 뜨는** 별도
   채널. 이름만 보고 어느 쪽인지 절대 구분 불가 — 이게 8차 사고("French Survival에
   업로드됨")가 실제로는 공식 French Survival이 **아니라** 이 숨은 쪽이었을 가능성이
   높은 이유이자, 앞으로도 반복될 수 있는 위험이다.
2. **"LondonProject_Gemini"가 박제했다는 매핑은 절반만 맞다**: 언어 Survival 10개는
   맞았지만, archive 10개 + core 5개에 대한 주장(6~15번, 1~5번)은 **실측과 전부
   불일치** — 대조 없이 그대로 받아들이면 안 됨. 이 리포는 `list_repos`로 찾아지지
   않아 "깃허브에 봉인 완료"라는 주장도 이 세션에서는 검증 불가.
3. science/classical/myth/american_archive/classic_reads 5개는 **아직 안전하게
   업로드할 수 없다** — `archive_channel_upload.py`의 fail-closed 검사가 계속
   막고 있고(10차), 여기 적힌 candidate channel_id들도 Chairman이 직접 "이 계정이
   내가 관리하는 게 맞다"고 확인하기 전까지는 등록하지 않는다.

## 다음에 헷갈리지 않으려면

- **title은 절대 식별자로 쓰지 않는다** — 이번에 확인했듯 title은 중복된다.
  handle도 바뀔 수 있어서 100% 안전하진 않지만 title보다 훨씬 안정적이다.
  **유일하게 믿을 건 channel_id뿐이다.**
- 앞으로 이 표에 없는 매핑 주장(다른 AI 트랙 포함)은 이 문서를 갱신하는 방식으로만
  반영한다 — 별도 리포/문서에 "따로 박제"하지 않는다. 소스가 여러 개면 그 자체가
  혼동의 원인이다.
