# 플레이리스트 채널 고정 매핑

사용자 직접 지정. 업로드 대상은 채널 이름이나 로그인 계정이 아니라 아래 채널 ID로 확인한다.

| 내부 키 | 사용자 지정 이름 | 고정 채널 ID |
|---|---|---|
| `globalmusic` | 카페로맨틱 | [UCbJfEtsffpgI5MsKkB7BYvQ](https://www.youtube.com/channel/UCbJfEtsffpgI5MsKkB7BYvQ) |
| `kpop` | Kpop | [UCKZsfAWyCmY0jckf4IWZrqw](https://www.youtube.com/channel/UCKZsfAWyCmY0jckf4IWZrqw) |
| `mbb` | 카페 모짜르트 | [UC7jOhyMa-FIrzZuea97z1Pw](https://www.youtube.com/channel/UC7jOhyMa-FIrzZuea97z1Pw) |
| `starbucks` | 스타벅스바이브-노동요 | [UC_e-sbLkVgwJNYEeobolNog](https://www.youtube.com/channel/UC_e-sbLkVgwJNYEeobolNog) |
| `healing` | 힐링카페 | [UC7yEsLM-HoXudngrD-4FIqg](https://www.youtube.com/channel/UC7yEsLM-HoXudngrD-4FIqg) |

실행 설정: `config/youtube_channels.json`. 채널 ID가 OAuth 인증 결과와 다르면 업로드를 중단한다. 다른 채널로 자동 대체하지 않는다. 모든 자동 업로드는 비공개이며, 최종 공개는 사용자가 결정한다.
이 매핑은 사용자의 명시적인 변경 요청 없이 바꾸지 않는다.
