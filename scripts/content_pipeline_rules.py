"""
27개 사이트 자동발행 파이프라인(autopost_mega.py) — 고정 규칙
(2026-08-03 사용자 지시로 확정: "다시는 이런 실수가 반복 안 되게 AI티를
가장 안 나게 GIthub 박제해놔").

배경: 27개 사이트 전수 감사 결과 중복 제목 125건, 이미지-내용 불일치 504건이
쌓여 있었던 게 발견됨. 애드센스 심사에는 이런 "AI 대량생산" 흔적이 감점
요인이라, 재발 방지를 코드 레벨(프롬프트 지시뿐 아니라)로 강제한다.

이 파일은 규칙 문서 + 단일 소스이고, autopost_mega.py가 실제 로직을
담고 있다. 여기 적힌 임계값/정책을 바꾸려면 코드도 같이 바꿔야 한다.
"""

# 중복 제목 방지 ---------------------------------------------------------

# 2026-08-03 이전: 뉴스모드 2개 사이트(koreanews365/theseouljournal)만,
# 그것도 완전 일치(exact match)로만 중복을 걸렀음 → 표현이 조금만 달라도
# 통과되어 27개 사이트 합계 125건 중복 제목이 쌓임.
# 2026-08-03 이후: 27개 사이트 전체 + fuzzy 매칭(제목 앞 20자, 공백/대소문자
# 무시) + 전체 발행 이력(페이지네이션으로 전부 로드, 최근 N개 제한 없음).
DUPLICATE_TITLE_CHECK_SCOPE = "all_27_sites"
DUPLICATE_TITLE_MATCH_MODE = "fuzzy_prefix_20chars"
DUPLICATE_TITLE_HISTORY_LIMIT = None  # 제한 없음(전체 이력)

# 사이트당 최소 보유 게시글 수. 중복/저품질 글을 정리할 때도 이 밑으로는
# 절대 안 내려가게 방어한다(애드센스 "콘텐츠 부족" 탈락 방지).
MIN_POSTS_PER_SITE = 15

# 뉴스 사이트 출처 표기 ----------------------------------------------------

# koreanews365.com(한국어 뉴스), theseouljournal.com(영자 뉴스)는 인터넷신문
# 등록(언론사 신청) 대상이라, 타 언론 보도를 재가공한 기사는 원출처를 밝혀야
# 한다(2026-08-03 사용자 지시). RSS로 실제 기사를 가져온 경우에만 해당되고,
# 자체 생성 상시주제(NEWS_KO_FALLBACK/NEWS_EN_FALLBACK)는 특정 외부 보도를
# 재가공한 게 아니므로 출처 표기 대상이 아니다.
#
# AI 프롬프트 지시에만 맡기면 매번 표현이 다르거나 누락될 수 있어서, 제목/
# 의학 디스클레이머와 동일한 원칙으로 "실제 출처가 있을 때 코드가 본문 끝에
# 고정 문구를 확정 삽입"하는 방식으로 강제한다 (crawl_rss_news가 반환하는
# 3번째 값 news_source, process_one() 안의 삽입 로직 참고).
NEWS_SOURCE_ATTRIBUTION_REQUIRED_SITES = ["koreanews365.com", "theseouljournal.com"]
NEWS_SOURCE_ATTRIBUTION_KO = "※ 이 기사는 {source}의 보도를 참고하여 재구성되었습니다."
NEWS_SOURCE_ATTRIBUTION_EN = "※ This article was adapted based on reporting from {source}."

# 이미지-내용 불일치 -------------------------------------------------------

# 2026-08-02~03 감사(audit_image_relevance.py)에서 27개 사이트 2,435건 중
# 504건의 이미지가 본문 주제와 무관하다고 판정됨(Gemini Vision). 판정은
# image_audit_manifest.json에, 실제 제거는 apply_image_audit.py(워크플로
# apply-image-audit.yml)가 수행 — 조사와 실행을 분리해서 항상 재실행 가능.
#
# 근본 원인은 스톡사진(Pixabay/Pexels) 키워드 검색의 한계 — 완전한 사전
# 방지는 발행 시점마다 Vision 판정을 다시 돌려야 하는데 비용/속도 문제로
# 아직 안 넣었음. 대신 get_multiple_images()가 이미 테마 컨텍스트를 검색어에
# 붙여서(theme_ctx) 관련성 낮은 결과 확률을 낮추고 있고, 주기적으로
# audit_image_relevance.py를 재실행해서 사후 감사하는 걸 표준 운영으로 한다.
IMAGE_RELEVANCE_PREPUBLISH_CHECK = False  # 비용 문제로 미구현, 사후감사로 대체
IMAGE_RELEVANCE_AUDIT_SCRIPT = "scripts/audit_image_relevance.py"
IMAGE_RELEVANCE_APPLY_SCRIPT = "scripts/apply_image_audit.py"

# 삭제 작업 안전 원칙 ------------------------------------------------------

# 27개 사이트 정리성 삭제(중복 제목, 이미지 등)는 항상:
# 1) 조사(investigate) 스크립트가 manifest.json을 만들고 (읽기 전용, 언제든
#    재실행 가능)
# 2) apply 스크립트가 그 manifest를 읽어서 실제로 쓰기 작업을 수행하며
# 3) 글 삭제는 force=false(완전삭제 아니고 휴지통 이동)로 해서 실수 시
#    복구 가능하게 한다.
DELETE_PATTERN = "investigate_manifest_then_apply"
POST_DELETE_MODE = "trash_not_permanent"  # WP REST force=false
