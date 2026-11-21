# SNS 6개 브랜드 실계정 감사 및 재시작 기준 — 2026-11-21 KST

상태: **현재 운영 기준 / 기존 이름표 대체**

이 문서는 2026-11-21 로그인된 Chrome·Meta 계정 센터·공개 프로필·Metricool 연결을 직접 대조한 결과다. 비밀번호, 인증 코드, 토큰, 전화번호는 기록하지 않는다.

## 1. 확정된 Instagram 6개

| 브랜드 | Instagram | Meta 프로필 ID | 확인 |
|---|---|---:|---|
| Korean SOS | `@korean_sos1` | `17841410825136018` | Meta 계정 센터 |
| English SOS | `@english_sos1` | `17841441355349874` | Meta 계정 센터 |
| Japanese SOS | `@japanese_sos1` | `17841411813216531` | Meta 계정 센터 |
| Chinese SOS | `@chinese.sos1` | `17841411010918367` | Meta 계정 센터 |
| Seoul Jisoo | `@seoul_jisoo1` | `17841404970616486` | Meta 계정 센터 |
| 서울저널 | `@seoul_journal1` | `17841449179626171` | Meta 계정 센터 + 공개 프로필 직접 확인 |

`@seoul_journal1`은 2026-11-21 직접 열어 실제 Instagram 프로필이 표시되는 것을 재확인했다. 당시 공개 메타데이터는 팔로워 4명, 팔로잉 6명, 게시물 1개였다.

## 2. 확정된 Threads 6개와 계정 센터 차이

| 브랜드 | Threads | 상태 |
|---|---|---|
| Korean SOS | `@korean_sos1` | Meta 계정 센터 표시, ID `17841443859544848` |
| English SOS | `@english_sos1` | 공개 프로필 존재, 공개 ID `49399536420`; 현재 Meta 계정 센터에는 미표시 |
| Japanese SOS | `@japanese_sos1` | Meta 계정 센터 표시, ID `17841413573916402`; 실제 로그인 성공 확인 |
| Chinese SOS | `@chinese.sos1` | Meta 계정 센터 표시, ID `17841478047108255` |
| Seoul Jisoo | `@seoul_jisoo1` | Meta 계정 센터 표시, ID `17841472145325611` |
| 서울저널 | `@seoul_journal1` | 공개 프로필 존재, 공개 ID `55327914621`; 현재 Meta 계정 센터에는 미표시 |

English SOS와 서울저널 Threads는 삭제된 계정이 아니다. 공개 프로필은 존재하지만 현재 주 Meta 계정 센터의 네 Threads 목록에 포함되지 않는다. 두 계정 모두 별도/구형 Meta 로그인으로 보이며 같은 2단계 SMS 인증 단계에서 막혔다. 2026-11-21 SMS가 도착하지 않았고, 화면에서 제공된 다른 방법은 백업 코드뿐이었다. 보안 설정, 번호, 계정 이동·분리·삭제는 변경하지 않았다.

## 3. TikTok 및 Facebook 확정

- TikTok: `@seoultopik`, 표시명 `KOREAN_SOS1`. 공개 프로필을 직접 열어 팔로워 약 31.1K, 좋아요 약 511.8K를 확인했다. Metricool 브랜드 `7080348`에도 `tiktokData=seoultopik`으로 연결되어 있다.
- Facebook: `서울국제대학 SIS - TOPIK Center`. 공개 프로필 ID `61588777439380`, 페이지 자산 ID `1128119143729384`. 직접 연 페이지에서 팔로워 약 11K를 확인했고 Metricool 브랜드 `7080348`의 Facebook 연결과 일치한다.
- Meta Business Suite에서 현재 보이는 `Westlake Vietnam`(자산 ID `103960881944000`)은 위 TOPIK Facebook 페이지가 아니다. 자동발행 대상을 고를 때 서로 바꾸어 연결하면 안 된다.
- 나머지 5개 브랜드의 TikTok/Facebook 실계정은 오늘 확정하지 않았다. 존재·소유권·게시 권한을 확인하기 전에는 6개가 연결됐다고 표시하지 않는다.

## 4. 자동발행 연결 감사

- Metricool 브랜드 `7080348`(`Korean SOS | TOPIK`, Asia/Seoul)은 현재 Instagram `korean_sos1`, TikTok `seoultopik`, Facebook 페이지 자산 `1128119143729384`를 반환했다. 세 플랫폼의 읽기 데이터 확인은 성공했다.
- 같은 브랜드의 현재 설정 응답에는 Threads 연결이 없었다.
- 2026-11-05 과거 작업은 Facebook과 TikTok을 발행했지만, Instagram은 `The Instagram account is restricted`로 실패했고 Threads는 오늘의 6개 기준이 아닌 옛 `@englishsurvival1`로 발행했다. 이 작업을 현재 6+6 연결 성공 증거로 재사용하지 않는다.
- 2026-11-21 이후 Metricool 예약 대기열은 0건이었다. 삭제할 예약 적체는 없었다.
- FikaClip은 Creator 월간 플랜 유지 결정이다. 소셜 자동 업로드는 현 플랜에서 사용할 수 없고, Pro 업그레이드는 하지 않는다. 자동화 화면은 최종 검토까지 준비됐지만 생성 버튼을 누르지 않았고, 목적지 미연결·크레딧 미사용 상태다.

## 5. 오늘부터 재시작하는 기준

- 기준 시각: **2026-11-21 00:00 KST**.
- 이 시각 이전의 놓친 SNS 회차나 옛 이름 기반 작업은 자동으로 따라잡아 발행하지 않는다.
- 오늘 이후에는 이 문서와 `config/SNS_SIX_BRAND_IDENTITY_LOCK_2026-11-21.json`의 정확한 계정만 사용한다.
- 오래된 계정명을 현재 로그인·연결·예약·발행 대상으로 대체 사용하지 않는다.
- 실제 Meta 계정 삭제, 분리, 이동, 보안 설정 변경은 별도 사용자 승인 전에는 하지 않는다.
- English SOS와 서울저널 Threads 인증이 풀리고, 계정별 쓰기 권한 및 시험 발행 URL이 확인되기 전에는 6+6 자동발행 완료로 표시하지 않는다.

## 6. 폐기되는 이전 활성 이름표

다음 이름은 과거 감사 기록에서만 읽을 수 있으며 현재 6+6 운영 매핑으로 사용하지 않는다: `seoul_topik`, `seoultopik`(Threads 옛 역할명), `english_pick1`, `japanese_pick`, `seoul_chris1`, `sis_topik`, `englishsurvival1`, `japanese_survival1`, `seoul_item365`.

단, 실제 외부 계정 자체를 삭제했다는 뜻은 아니다. GitHub 감사 기록은 보존하되 현재 기준에서 완전히 제외한다.
