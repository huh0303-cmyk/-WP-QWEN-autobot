# Meta 게시 연결 및 운영

2026-09-07 사용자 요청: TOPIK 영상 생성 잠금을 복구하고 Instagram/Threads 실제 게시 및 계정 등록을 진행한다.

## 확인된 상태

- 2026-08-28 `1f46baa`가 10개 워크플로에 영상/썸네일 긴급 잠금을 추가했다. 커밋만으로 CEO 본인이 직접 지시했는지는 판단할 수 없다.
- TOPIK 수동 생성만 복구한다. `TOPIK_VIDEO_GENERATION_DISABLED=true` 저장소 변수로 다시 중지할 수 있다. 기존 다른 영상 워크플로의 잠금과 스케줄은 변경하지 않는다.
- TOPIK 생성기는 한국어 단어 문제를 ko/en/ja/es/vi로 설명한다. ENGLISH 브랜드용 영어 단어 생성기라는 의미가 아니다. 브랜드별 원본 콘텐츠를 검수해서 선택해야 한다.
- Instagram TOPIK 시크릿은 존재한다. 9월 3일 기존 조회 결과는 권한 부족이며 현재 게시 가능 여부는 미검증이다. Threads 및 ENGLISH/LANGUAGE별 시크릿은 없다.
- Facebook 로그인 후 개발자 플랫폼은 비정상 활동에 따른 계정 확인을 요구한다. 계정 확인 후 기존 앱부터 확인한다.

## 인증 방식

Instagram은 Business 또는 Creator 계정이 필요하다. Facebook Login 방식은 연결된 Facebook Page 및 instagram_basic, instagram_content_publish, pages_read_engagement, pages_show_list 권한을 사용한다. Instagram Login 방식도 지원하도록 IG_LOGIN_TYPE=instagram을 제공한다. 해당 방식은 instagram_business_basic, instagram_business_content_publish를 사용하며 Facebook Page 연결이 필수는 아니다.

Threads는 별도의 Threads OAuth 토큰과 threads_basic, threads_content_publish 권한을 사용한다. Facebook 토큰을 재사용하지 않는다. 앱 하나에 세 제품을 반드시 모두 추가해야 한다고 단정하지 않는다. 실제 대시보드에서 지원하는 use case 조합과 기존 앱을 확인한다. 앱 역할 계정 테스트와 외부 사용자용 앱 검수/고급 액세스는 구분한다.

## 설정

TOPIK: IG_ACCESS_TOKEN, IG_USER_ID, THREADS_ACCESS_TOKEN, THREADS_USER_ID.
ENGLISH/LANGUAGE는 각 이름 뒤에 _ENGLISH 또는 _LANGUAGE를 붙인다. 다른 브랜드의 자격 증명으로 대체하지 않는다.
IG_LOGIN_TYPE 저장소 변수는 facebook(기본) 또는 instagram, META_GRAPH_VERSION 기본값은 v25.0. 현재 로그인 방식은 전체 브랜드에 공통 적용된다.

토큰은 GitHub Actions secrets에만 저장한다. 코드, 결과 파일, 채팅에 기록하지 않는다. 토큰 만료/갱신은 실제 앱 인증 흐름을 확인한 후 연결해야 하며 현재 자동 갱신은 구현하지 않았다.

## 실행

1. topik-quiz-daily.yml을 언어/문항 수로 수동 실행한다. 생성은 유료 서비스 호출을 포함한다. run_social_review 기본값은 false다.
2. 영상/캡션 검수 후 social-publish-one.yml에 platform, brand, lang, source_run_id를 지정한다. source_run_id는 topik-review-<run_id> 영상 아티팩트를 다운로드한다. 기존 저장 파일은 meta_path로 지정할 수 있다.
3. Instagram/Threads 선택 실행은 공개 게시다. 생성 워크플로의 검토본 업로드에서는 META_PUBLISH_ENABLED를 켜지 않아 공개 게시하지 않는다.
4. Meta 서버가 직접 다운로드할 수 있는 HTTPS MP4 URL이 필요하다. Drive 링크는 로그인/확인 페이지나 다운로드 제한이 걸릴 수 있으므로 실제 컨테이너 처리 성공으로 검증한다.
5. 컨테이너 생성 -> FINISHED 확인 -> publish -> media_id 저장 순서다. 처리 실패 및 인증 실패는 워크플로 실패로 기록한다.

## 게시 기록 및 재실행

META_PUBLISH_STATE_DIR(기본 .meta-publish-state)에 계정/영상/캡션별 영수증을 저장한다. 같은 입력은 저장된 게시 ID를 반환하며, 응답 유실 시 자동 재게시하지 않는다. 컨테이너 ID로 실제 게시 상태를 먼저 확인해야 한다.

Actions 실행은 브랜드/플랫폼별 직렬화하고, 캐시 복원 및 항상 저장/영수증 아티팩트 업로드를 사용한다. GitHub 캐시는 영구 저장소가 아니므로 캐시 만료/삭제 또는 저장 실패 이후 재실행은 이전 영수증을 복원하고 실제 계정 상태를 확인해야 한다. 캐시 기반 중복 방지가 영구 exactly-once를 보장하지 않는다. 로컬 호출은 동일 계정에서 병렬로 실행하지 않는다. 상시 스케줄 운영 전에는 영구 공유 저장소와 토큰 갱신 연결이 필요하다.

## 검증

python -m unittest discover -s tests -p test_meta_publish.py -v

실제 공개 게시 및 계정 등록 완료는 Meta 계정 확인, 앱/계정 연결과 토큰 권한 확인 후 별도 검증한다. 모의 API 테스트 통과는 실계정 게시 성공을 뜻하지 않는다.

공식 자료:
- https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api
- https://www.postman.com/meta/threads/request/34203612-72c20362-5b0c-4f14-b9cd-4315ff91cd85
