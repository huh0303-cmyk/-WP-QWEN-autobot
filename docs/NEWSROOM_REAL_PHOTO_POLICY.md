# 뉴스룸 실제 사진 + AI 이미지 — 사용자 확정 2026-09-09

두 뉴스룸은 AI 이미지만 고집하지 않는다. 기사와 관련 있고 개별 사용 조건을 확인한 실제 사진을 우선 배치하고, AI 설명 이미지는 별도로 표시한다. 이 지시는 기존 뉴스룸 AI 전용 지침을 대체하며 일반 블로그의 이미지 설정은 유지한다.

- 실제 사진의 촬영일, 출처, 이용조건 링크를 함께 표시한다. 자료사진을 당일 현장 사진으로 설명하지 않는다.
- AI 이미지는 실제 사건의 증거로 사용하지 않고 AI 생성 설명 이미지임을 표시한다.
- RSS 언론사 사진을 자동 복사하지 않는다. 기사 이용과 사진 이용은 별도로 검증한다.
- 현재 자동 첨부는 `config/newsroom_real_photos.json`에 개별 검토된 DVIDS 자료사진으로 한정한다. 모든 전쟁 기사에 무관한 사진을 넣지 않는다. 사진 검증 실패는 속보 발행을 막지 않는다.

## 확인한 실제 사진 출처

| 출처 | 적합한 기사 | 확인 조건 |
|---|---|---|
| [DVIDS](https://www.dvidshub.net/about/copyright) | 군함·미군·군사 작전 | 개별 Public Domain 표시와 촬영자 확인, 비후원 고지, 제3자 권리 예외 확인 |
| [Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia/en) | 지역·건물·인물·기록 사진 | 파일별 PD/CC 조건, 저자·라이선스·변경 여부 표시. CC BY-SA는 동일조건 의무 확인 |
| [공공누리](https://www.kogl.or.kr/info/license.do) | 한국 정부·정책·문화·공공행사 | 개별 0/1유형 우선. 1유형 출처 표시. 상업적 이용 금지 유형은 자동 사용 제외 |
| [NASA](https://www.nasa.gov/images/) | 우주·위성·지구 관측 | 개별 이미지 크레딧과 미디어 이용지침 확인; 기관 로고·제3자 저작물 별도 |

현장성이 필요한 속보의 첫 적용 사진: [2026-04-20 아라비아해 미군 순찰](https://www.dvidshub.net/image/9628954/us-forces-patrol-arabian-sea-near-m-v-touska). 9월 공격 현장 사진이 아니므로 한·영 모두 자료사진과 촬영일을 명시한다.
