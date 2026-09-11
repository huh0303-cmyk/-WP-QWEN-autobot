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

# SEO 점수 하드 게이트 (2026-08-04) --------------------------------------

# 사용자 지시: "SEO 90점 이상만 올려. 이미지도 없으면.. 이미지 없이 가고
# 억지로 넣지 마." 두 가지 다 코드에 반영됨:
# 1) process_one()에서 score(estimate_seo_score 결과) < SEO_TARGET(90)이면
#    postprocess로 보정해도 발행 자체를 스킵(이전엔 best-effort로 그냥 발행).
# 2) get_multiple_images() 실패 + 인포그래픽 생성도 실패하면 관련없는 범용
#    사진으로 억지로 채우지 않고 이미지 없이 발행 (기존 로직 유지 확인됨).
#
# ⚠️ 중요한 한계 — 반드시 알고 있을 것: wp_post()가 WP에 저장하는
# rank_math_seo_score 메타값은 **이 스크립트 자신의 estimate_seo_score()
# 추정치를 그대로 문자열로 박아넣은 것**이다. RankMath 플러그인이 REST API로
# 만들어진 글을 열어서 실제로 재분석해 갱신해주는 게 아니다(RankMath의 진짜
# 분석 로직은 주로 워드프레스 편집기 화면에서 사람이 열었을 때 JS로 도는
# 방식이라, API로만 발행된 글은 절대 재계산되지 않음). 즉 2026-08-03 감사에서
# 본 "SEO 평균 72.2점" 같은 수치도 사실은 RankMath의 독립적 판정이 아니라
# 이 파이프라인이 스스로 매긴 점수였다. estimate_seo_score()의 배점 기준
# (분량/메타길이/이미지수/구조 등)이 RankMath의 실제 채점 기준(키워드 밀도,
# 가독성, 내부/외부링크, alt텍스트 등)과 다르므로 완전히 신뢰할 순 없지만,
# 현재로선 발행 전에 확인 가능한 유일한 사전 신호라 게이트로 사용한다.
# 진짜 RankMath 분석이 필요하면 사람이 워드프레스 편집기를 직접 열어야 한다.
SEO_TARGET = 90  # autopost_mega.py의 SEO_TARGET과 반드시 동일하게 유지
SEO_SCORE_IS_SELF_REPORTED_NOT_REAL_RANKMATH = True
NO_FORCED_UNRELATED_IMAGES = True

# 발행 빈도/시각 (2026-08-04) ----------------------------------------------

# 사용자 지시: "내일부터는 완전 랜덤한 시간으로. 글 1개씩만."
# - SITES_CONFIG 전체 사이트 daily=1로 통일(예전엔 사이트별 3~10개/일,
#   특히 kworld365.com은 10개/일이라 품질이 가장 나빴음 — SEO평균 23.7,
#   AI위험의심 30건으로 27개 사이트 중 압도적 최악).
# - publish_scheduler.py: 예전엔 하루 3슬롯(07:25/13:07/19:50 KST ±60분
#   랜덤)이었는데, 하루 1슬롯 + 완전랜덤시각(00:00~23:59 중 아무때나,
#   앵커 없음)으로 변경. get_slot_posts()도 3분할 없이 daily 값을 그대로 반환.
DAILY_POSTS_PER_SITE = 1
SCHEDULE_MODE = "fully_random_once_daily"  # 이전: "3_fixed_anchors_jittered"

# 삭제 작업 안전 원칙 ------------------------------------------------------

# 27개 사이트 정리성 삭제(중복 제목, 이미지 등)는 항상:
# 1) 조사(investigate) 스크립트가 manifest.json을 만들고 (읽기 전용, 언제든
#    재실행 가능)
# 2) apply 스크립트가 그 manifest를 읽어서 실제로 쓰기 작업을 수행하며
# 3) 글 삭제는 force=false(완전삭제 아니고 휴지통 이동)로 해서 실수 시
#    복구 가능하게 한다.
DELETE_PATTERN = "investigate_manifest_then_apply"
POST_DELETE_MODE = "trash_not_permanent"  # WP REST force=false
