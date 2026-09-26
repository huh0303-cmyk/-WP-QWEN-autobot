# 런던프로젝트GPT — YouTube 15채널 최종 OWNER LOCK

Updated: 2026-09-27 KST  
Authority: owner-confirmed account-selector mapping + owner-confirmed current channel name/handle + existing GitHub locked UC IDs.

## 핵심 규칙

1. **계정선택 화면 이름은 채널 이름이 아니다.** OAuth/Google 계정 선택용 내비게이션 힌트다.
2. **실제 채널 정체성은 현재 채널명 + @handle + UC channel ID**로 판정한다.
3. 이름이 충돌할 때는 이 문서의 현재 owner-confirmed handle을 우선한다.
4. UC ID가 이미 과거 직접 잠겨 있는 10개는 그대로 승계한다.
5. UC ID를 현재 GitHub에서 찾을 수 없는 5개는 추측 금지. 실제 로그인 후 `channels.list(mine=true)` 또는 YouTube Studio URL로 캡처할 때까지 업로드 금지.
6. 모든 자동 업로드는 PRIVATE. 업로드 전 authenticated channel ID가 expected ID와 다르면 즉시 중단.
7. **Studio_K3가 두 번 보이는 것은 정상**이다. 선택화면의 1번째/2번째 위치를 구분해야 한다.
8. **K-pop Studio는 Studio_K3와 다른 항목**이다.

## 최종 매핑

| # | 내부 키 | 계정선택 화면에서 클릭 | 실제 채널명 | 실제 핸들 | 고정/승계 UC ID | 판정 |
|---:|---|---|---|---|---|---|
| 1 | `globalmusic` | **Studio_K3 (2번째)** | **cafe_K** | **@cafe_K1** | `UCbJfEtsffpgI5MsKkB7BYvQ` | LOCKED |
| 2 | `healing` | **K-ISSUE** | **Studio_healing** | **@Studio_k3** | `UC7yEsLM-HoXudngrD-4FIqg` | LOCKED |
| 3 | `starbucks` | **Chinese Survival** | **Starbucks vibes** | **@Starbucksvibes** | `UC_e-sbLkVgwJNYEeobolNog` | LOCKED |
| 4 | `mbb` | **Mozart-Bach-Beethoven** | **Mozart-Bach-Beethoven** | **@Mozart_Bach_Beethoven** | `UC7jOhyMa-FIrzZuea97z1Pw` | LOCKED |
| 5 | `kpop` | **Studio_K3 (1번째)** | **kpop_studio7** | **@kpop_studio7** | `UCKZsfAWyCmY0jckf4IWZrqw` | LOCKED |
| 6 | `nasa` | **K-RELAX** | **NASA_SPACE_JOURNAL** | **@NASA_SPACE_JOURNAL** | `UCtNLZO07Oh3UnXPI2CjOgNg` | LOCKED · 이름/핸들 최신화 |
| 7 | `history` | **Spanish Survival** | **HISTORY_TODAY_JOURNAL** | **@HISTORY_TODAY_JOURNAL** | `UCVBvZwodUF4s57KeNicxQ3w` | LOCKED · 이름/핸들 최신화 |
| 8 | `science` | **K-health 365** | **SCIENCE_FACTS_JOURNAL** | **@SCIENCE_FACTS_JOURNAL** | — | HANDLE LOCKED · UC ID 확인 대기 |
| 9 | `classical` | **비영리한국유학협회KSA** | **Classical Journal** | **@ClassicalJournal** | — | HANDLE LOCKED · UC ID 확인 대기 |
| 10 | `myth` | **Arabic Survival** | **MYTH_LEGEND_JOURNAL** | **@MYTH_LEGEND_JOURNAL** | — | HANDLE LOCKED · UC ID 확인 대기 |
| 11 | `invention` | **K-pop Studio** | **INVENTION_JOURNAL** | **@INVENTION_JOURNAL** | `UCgNj-yS93A_fOHXXvG49fww` | LOCKED · 이름/핸들 최신화 |
| 12 | `american_archive` | **AMERICAN_ARCHIVE_TIMES** | **AMERICAN_ARCHIVE_JOURNAL** | **@AMERICAN_ARCHIVE_JOURNAL** | — | HANDLE LOCKED · UC ID 확인 대기 |
| 13 | `silent_era` | **SILENT_ERA_TIMES** | **SILENT_ERA_JOURNAL** | **@SILENT_ERA_JOURNAL** | `UCLvy6kSpC8-7o3hnSrfQ47g` | LOCKED · 이름/핸들 최신화 |
| 14 | `retro_reels` | **RETRO_REELS_TIMES** | **RETRO_REELS_JOURNAL** | **@RETRO_REELS_JOURNAL** | `UCwh49EokdWFJqYFE_zA6XDQ` | LOCKED · 이름/핸들 최신화 |
| 15 | `classic_reads` | **CLASSIC_READS_TIMES** | **CLASSIC_READS_JOURNAL** | **@CLASSIC_READS_JOURNAL** | — | HANDLE LOCKED · UC ID 확인 대기 |

## 교차검증 근거

### 플레이리스트 5
현재 코드 `scripts/apply_thumbnail_bank_to_live_videos.py`에 이미 다음 실제 핸들이 존재한다.
- globalmusic -> cafe_K1
- healing -> Studio_k3
- starbucks -> Starbucksvibes
- mbb -> Mozart_Bach_Beethoven
- kpop -> kpop_studio7

따라서 오래된 `youtube_channels.json`의 `cafe_romantic / cafe_healing1 / cafe_mozart` 핸들은 최종 owner lock과 충돌할 때 **stale 표시명**으로 취급한다.

### 인증선택명
GitHub에는 이미 다음 불일치가 기록돼 있다.
- healing OAuth brand = K-ISSUE
- starbucks old Google brand = Chinese Survival
- 계정선택 브랜드명만 보고 실제 채널 정체성을 판단하면 안 됨

### 기존 UC ID 승계
과거 lock에서 직접 고정된 내부 키의 ID를 유지:
- globalmusic, healing, starbucks, mbb, kpop
- nasa, history, invention, silent_era, retro_reels

이 10개는 owner-confirmed 최신 이름/핸들에 연결해 사용한다.

## 절대 업로드 금지 상태

아래 5개는 **실제 핸들은 확정**, UC ID만 미확정:
- science
- classical
- myth
- american_archive
- classic_reads

이 5개는 인증을 마친 뒤 실제 `UC...`를 캡처하기 전까지 자동 업로드를 시작하지 않는다.

## 오래된 값 처리

다음은 내부 키 자체가 바뀐 것이 아니라 **과거 표시명/핸들**이다. 자동으로 다시 되돌리지 않는다.
- NASA_XFILES
- HISTORY_TV_TODAY
- INVENTION_STORY1
- OLD_HOLLYWOOD1
- RETRO_USA1
- cafe_romantic
- cafe_healing1
- cafe_mozart

현재 owner-confirmed 채널명/핸들이 이 문서의 정본이다.

## 사고방지

특히 `american_archive`는 과거 Secret/브랜드가 다른 Survival 채널로 연결된 사례가 있었으므로,
**브랜드명 일치만으로 업로드 금지**. UC ID 확인 후에만 enable 한다.
