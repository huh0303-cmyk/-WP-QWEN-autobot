# 런던프로젝트GPT Codex 연결 구성 — 2026-09-28 KST

## 목적

Codex에서 런던프로젝트GPT의 4-Agent 운영, 방문자·검색 색인·수익 보고를 근거별로 처리한다. Codex 연결은 운영 웹앱의 n8n/API 연결을 자동으로 바꾸지 않는다.

## 확인된 구성

| 항목 | 확인 상태 | 용도와 경계 |
| --- | --- | --- |
| OpenAI Docs MCP | Codex 전역에 `openaiDeveloperDocs`로 추가, streamable HTTP, enabled | OpenAI/Codex 개발 문서 조회 전용. 블로그 통계 접근 권한 없음. |
| GitHub 커넥터 | 설치됨 | 소스, PR, CI, 감사 기록. |
| WPVibe | 설치됨; 개별 WordPress 사이트 연결은 미검증 | 연결된 사이트에 한해 글/사이트 정보 관리. 런던프로젝트GPT의 자체 발행 상태와 혼동하지 않는다. |
| Google Drive·Gmail·Calendar | 설치됨 | 문서·메일·일정 작업에만 사용; GSC·GA4·AdSense 지표를 대신하지 않는다. |
| GSC Wizard | 추천함; 아직 연결/설치 확인 안 됨 | Google 로그인 후 Search Console 속성과 연결된 GA4 자료를 읽는 후보. 속성 권한과 실제 연결은 별도 확인 필요. |
| AdSense 수익 연결 | 적합한 설치형 연결 확인 못 함 | 실제 수익은 AdSense 날짜별 계정 보고서 또는 검증된 API 증거로만 기록. |
| n8n | 기존 VPS 오케스트레이터와 게이트웨이 운영 중; 별도 플러그인 검색 결과 없음 | 운영 웹앱의 네 Agent 실행 경로. 임의의 추가 MCP 서버를 만들지 않음. |
| `london-blog-ops` 스킬 | 이 저장소와 Codex 개인 스킬에 추가 | 방문자·색인·수익 출처 구분, 수동/자동 발행 상태, 중복 발행 방지 절차. |

첨부 화면의 STDIO `openai-dev-mcp serve-sqlite`는 빈 맞춤형 MCP 입력 예시이며, 이 프로젝트의 연결 설정으로 저장하지 않았다. 문서 MCP는 공식 HTTPS 주소 `https://developers.openai.com/mcp`를 사용한다. 로컬 SQLite 전체를 MCP로 노출하면 운영 데이터 범위가 불필요하게 넓어져 현재 필요하지 않다.

## 다음 계정 단계

1. 사용자가 GSC Wizard를 연결할 때 실제 Search Console 속성과 필요한 GA4 속성 권한을 확인한다. 연결 전에는 검색 색인 수나 GA4 방문자 수를 확정 값으로 보고하지 않는다.
2. 수익 보고는 AdSense 계정의 실제 보고서 접근이 마련될 때까지 `미확인`으로 둔다. 승인 여부와 수익을 분리한다.
3. WordPress 개별 사이트를 WPVibe로 다루려면 그 사이트의 연결 상태를 확인한다. 이미 존재하는 운영 서버 자격 증명을 Codex MCP 화면에 복사하지 않는다.

비밀 키, 토큰, 개인 로그인 정보는 GitHub에 기록하지 않는다.
