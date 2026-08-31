#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
situation_room_daily.py
─────────────────────────────────────────────────────────────
"종합상황실" — 27개 사이트 트래픽/색인 + 유튜브 전 채널 구독자 +
틱톡/페이스북/인스타그램/Threads 팔로워를 한 번에 모아서:
  1. 어제 대비 증감(diff) 계산
  2. Gemini로 오늘자 요약 분석 + 제안 생성
  3. 구글시트 전송
  4. 이메일 발송 (huh0303@gmail.com)
  5. 카카오톡 "나에게 보내기"로 요약 발송

daily_site_traffic.py(사이트별 상세)와 social_stats_daily.py(SNS 단일채널)를
그대로 두고, 이 스크립트는 "전체 요약 + AI 분석 + 카톡/이메일 발송" 역할만
추가로 담당한다 (기존 파이프라인과 충돌 없음).

필요 환경변수:
    GSC_SERVICE_ACCOUNT_JSON, YOUTUBE_API_KEY,
    TIKTOK_USERNAME, FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID,
    IG_ACCESS_TOKEN(or FB_PAGE_ACCESS_TOKEN), IG_USER_ID,
    THREADS_ACCESS_TOKEN, THREADS_USER_ID,
    GEMINI_API_KEY, SHEETS_WEBHOOK, SHEET_ID,
    GMAIL_APP_PASSWORD,
    KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, REPO_ROOT)


def _load_dotenv():
    """CI(깃허브 액션)에서는 시크릿이 이미 환경변수로 들어와 있지만, 로컬에서
    직접 실행할 때는 .env를 안 읽으면 아무 것도 안 채워진다 — 이미 설정된
    실제 환경변수는 덮어쓰지 않고, 없는 것만 .env에서 채운다."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(repo_root, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k and k not in os.environ:
                os.environ[k] = v.strip()


_load_dotenv()

from daily_site_traffic import (  # noqa: E402
    get_gsc_token, gsc_get, latest_daily_stats, get_index_coverage, SITES, weekday_kr,
)
from social_stats_daily import (  # noqa: E402
    get_tiktok_followers_multi, get_facebook_followers_multi,
    get_instagram_followers_multi, get_threads_followers_multi, BRANDS,
)
from automation_hub.youtube_registry import load_channels  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KST = timezone(timedelta(hours=9))
HISTORY_FILE = "situation_room_history.json"
DAILY_SITE_RESULT_FILE = "daily_site_traffic_result.json"

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SHEETS_WEBHOOK = os.environ.get("SHEETS_WEBHOOK", "")
SHEET_ID = os.environ.get("SHEET_ID", "")
GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN", "")


def collect_adsense_khealth_revenue():
    """Read K-health365 AdSense estimates in KRW through the read-only API."""
    client_id = os.environ.get("GOOGLE_METRICS_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_METRICS_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GOOGLE_METRICS_REFRESH_TOKEN", "")
    empty = {"today": None, "month": None, "cumulative": None, "currency": "KRW"}
    if not all((client_id, client_secret, refresh_token)):
        return {**empty, "status": "AdSense 읽기 인증 연결 필요"}
    try:
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={"client_id": client_id, "client_secret": client_secret,
                  "refresh_token": refresh_token, "grant_type": "refresh_token"}, timeout=20,
        )
        token_response.raise_for_status()
        headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
        accounts_response = requests.get(
            "https://adsense.googleapis.com/v2/accounts", headers=headers, timeout=20,
        )
        accounts_response.raise_for_status()
        accounts = accounts_response.json().get("accounts", [])
        if not accounts:
            return {**empty, "status": "AdSense 계정 없음"}
        account = accounts[0]["name"]

        def report(date_range):
            response = requests.get(
                f"https://adsense.googleapis.com/v2/{account}/reports:generate",
                headers=headers,
                params=[("metrics", "ESTIMATED_EARNINGS"), ("dateRange", date_range),
                        ("filters", "DOMAIN_NAME==k-health365.com"), ("currencyCode", "KRW")],
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            cells = (payload.get("totals") or {}).get("cells", [])
            return round(float(cells[0].get("value", 0)), 2) if cells else 0.0

        return {
            "today": report("TODAY"), "month": report("MONTH_TO_DATE"),
            "cumulative": report("YEAR_TO_DATE"), "currency": "KRW",
            "status": "수익화 승인 · AdSense 정상",
        }
    except Exception as exc:
        return {**empty, "status": f"AdSense 수익 수집 실패: {str(exc)[:120]}"}

def load_reporting_channels():
    """Combine the canonical scheduler registry with explicit strategic-only channels."""
    channels = [(c.display_name, c.channel_id) for c in load_channels() if c.enabled]
    path = Path(__file__).resolve().parents[1] / "config" / "youtube_reporting_channels.json"
    extra = json.loads(path.read_text(encoding="utf-8"))["channels"]
    channels.extend((c["display_name"], c["channel_id"]) for c in extra if c.get("enabled", True))
    labels = [label for label, _ in channels]
    ids = [channel_id for _, channel_id in channels]
    if len(labels) != len(set(labels)) or len(ids) != len(set(ids)):
        raise ValueError("duplicate YouTube label/channel_id in reporting registries")
    return channels


YOUTUBE_CHANNELS = load_reporting_channels()

# 3개 언어 브랜드(TOPIK/English/Language)의 SNS 계정 표시용 이름 + 확인된 핸들.
# 핸들을 모르는(아직 안 만들었거나 미확인인) 항목은 None으로 두고 리포트에
# "미설정"으로 명시한다 — 틀린 URL을 지어내지 않는다.
BRAND_LABELS_KR = {"TOPIK": "TOPIK", "ENGLISH": "English", "LANGUAGE": "Language(10개국어)"}
# 2026-08-06 확인된 핸들만 채움(대화 중 실제 조회로 확인된 것만):
KNOWN_HANDLES = {
    "youtube": {"TOPIK": "seoultopik", "ENGLISH": "English_Survival", "LANGUAGE": "Studio_starbucks"},
    # 2026-08-06: English/Language 신규 계정 확정(사용자 확인). seoultopik=TOPIK은
    # 원래 표시이름이 "Language center"로 잘못 박혀있었으나 소개글/콘텐츠(TOPIK 단어
    # 퀴즈, 팔로워 1,670)로 확인 후 사용자가 직접 이름을 TOPIK Center로 수정 중.
    # ENGLISH는 실제로 "sis_english1"로 생성됨(sis_english가 이미 있어서 "1" 자동첨가로 추정).
    # LANGUAGE는 2026-08-06 기준 아직 생성 전 — 만들어지면 채워야 함.
    # 2026-08-06: 사용자이름을 seoultopik -> sis__topik(언더바 2개! sis_topik 1개는
    # 다른/빈 계정이라 실제로 못 씀)으로 개명. TikTok(sis_topik, 언더바 1개)이랑
    # 미묘하게 다른 철자니 주의. 표시이름("이름" 필드)은 아직 "Language center"인
    # 채로 남아있음 — 별도 수정 필요.
    "instagram": {"TOPIK": "sis__topik", "ENGLISH": "sis_english1", "LANGUAGE": "sis_language"},
    "threads": {"TOPIK": "sis__topik", "ENGLISH": "sis_english1", "LANGUAGE": "sis_language"},
    # 2026-08-06 페이스북 공개검색으로 3개 브랜드 페이지ID 전부 확인됨(핸들 없이 숫자ID URL 사용).
    "facebook_ids": {"TOPIK": "61588777439380", "ENGLISH": "61592457107609", "LANGUAGE": "61593057083167"},
    # 2026-08-06: TOPIK<->Language 사이에서 두 번 왔다갔다 하다가 최종 확정.
    # sis_topik(팔로워 28.5K, TOPIK VOCAB 재생목록이 메인)이 TOPIK 계정.
    # Business Center 표시이름이 "Language Center"로 뜨는 건 그냥 stale 라벨이고
    # 실제 핸들(sis_topik)과 콘텐츠가 진짜 정체를 말해준다 — 표시이름 믿지 말 것.
    # Language 브랜드 계정은 Business Center의 "서울국제대학SIS-LANGUAGEcenter"
    # (ID 7670386948028252176)이고 핸들은 아직 미확인.
    "tiktok": {"TOPIK": "sis_topik"},
}


def _platform_url(platform, brand, fallback_id=None):
    handle = KNOWN_HANDLES.get(platform, {}).get(brand)
    if handle:
        if platform == "tiktok":
            return f"https://www.tiktok.com/@{handle}"
        if platform in ("youtube",):
            return f"https://www.youtube.com/@{handle}"
        if platform == "instagram":
            return f"https://www.instagram.com/{handle}/"
        if platform == "threads":
            return f"https://www.threads.net/@{handle}"
    if platform == "facebook" and fallback_id:
        return f"https://www.facebook.com/{fallback_id}"
    return "(URL 미확인)"


def log(msg):
    print(msg, flush=True)


def now_kst_str():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


# ════════════════════════════════════════════════════════════
# 1) 27개 사이트 요약 (상세 아니라 합계만)
# ════════════════════════════════════════════════════════════
def get_visitor_metrics(site_url):
    """Return today's live visitors, yesterday comparison, and total.

    User-facing display is ``오늘방문 120(+30)`` and
    ``누적방문 1,053(+2)``. The cumulative increase for today equals
    today's visitor count because the footer counter adds each visit to
    both today's count and the cumulative total.
    """
    try:
        r = requests.get(f"{site_url}/wp-json/site-stats/v1/visitors",
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            today_count = int(data.get("count", 0))
            yesterday_count = int(data.get("yesterday_count", 0))
            day_before_count = int(data.get("day_before_yesterday_count", 0))
            total_count = int(data.get("total", today_count))
            return {
                "today": today_count,
                "yesterday": yesterday_count,
                "day_before_yesterday": day_before_count,
                "daily_delta": today_count - yesterday_count,
                "total": total_count,
                "total_delta": today_count,
            }
    except Exception:
        pass
    return None


def get_total_published(site_url):
    """공개 글 수(status=publish) — 인증 없이 조회 가능한 공개 REST 엔드포인트라
    사이트별 WP 비밀번호가 없어도 된다. 2026-08-19: AI티/미색인 글을 대량으로
    비공개 전환하는 작업을 시작해서, 이 숫자가 0에 가깝게 나오는 사이트가
    생길 수 있음 — 버그가 아니라 의도된 결과이니 리포트에도 그대로 노출한다."""
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                          params={"per_page": 1, "status": "publish"},
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            return int(r.headers.get("X-WP-Total", "0"))
    except Exception:
        pass
    return None


def _blogger_slug(room):
    """Return the intended blogspot subdomain for all 27 Blogger rooms."""
    aliases = {
        "blogger_khealth365": "k-health365",
        "blogger_ktrip365": "k-trip365",
        "blogger_kvisa365": "k-visa365",
        "blogger_kikorea": "ki-korea",
        "blogger_kieca": "kieca-korea",
        "blogger_ksa": "ksa-korea",
        "blogger_sis": "sis-korea",
        "blogger_koreanews365": "koreanews365",
    }
    room_id = room.get("room_id", "")
    return aliases.get(room_id, room_id.removeprefix("blogger_") or room.get("name", ""))


def load_blogger_rooms():
    path = Path(REPO_ROOT) / "config" / "automation_rooms.json"
    try:
        rooms = json.loads(path.read_text(encoding="utf-8")).get("rooms", [])
    except (OSError, ValueError):
        return []
    return [room for room in rooms if room.get("platform") == "blogger"]


def get_blogger_published_count(blog_url):
    """Count publicly visible Blogger posts through the public JSON feed."""
    try:
        response = requests.get(
            f"{blog_url.rstrip('/')}/feeds/posts/default",
            params={"alt": "json", "max-results": 1},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
        )
        if response.status_code != 200:
            return None, f"공개피드 HTTP {response.status_code}"
        total = response.json().get("feed", {}).get("openSearch$totalResults", {}).get("$t")
        return int(total or 0), None
    except Exception as exc:
        return None, f"공개피드 오류: {str(exc)[:100]}"


def collect_blogger_summary():
    """Collect public-post and sitemap-index counts for all 27 Blogger rooms."""
    rooms = load_blogger_rooms()
    token = None
    accessible = set()
    try:
        token = get_gsc_token()
        response = gsc_get(token, "/sites")
        if response.status_code == 200:
            accessible = {item.get("siteUrl") for item in response.json().get("siteEntry", [])}
    except Exception:
        token = None

    details = []
    for room in rooms:
        slug = _blogger_slug(room)
        blog_url = f"https://{slug}.blogspot.com"
        public_posts, feed_error = get_blogger_published_count(blog_url)
        indexed = None
        errors = []
        if feed_error:
            errors.append(feed_error)
        property_candidates = (blog_url + "/", f"sc-domain:{slug}.blogspot.com")
        query_site = next((candidate for candidate in property_candidates if candidate in accessible), None)
        if token and query_site:
            coverage, coverage_error = get_index_coverage(token, query_site)
            if coverage:
                indexed = coverage.get("sitemap_indexed")
            elif coverage_error:
                errors.append(coverage_error)
        else:
            errors.append("GSC 속성 연결 필요")
        details.append({
            "site_id": room.get("room_id"), "name": room.get("name"),
            "domain": f"{slug}.blogspot.com", "url": blog_url,
            "public_posts": public_posts, "indexed": indexed,
            "status": "정상" if not errors else " | ".join(errors),
        })
    return details


def collect_site_summary():
    if not os.environ.get("GSC_SERVICE_ACCOUNT_JSON"):
        return {"total_clicks": None, "total_indexed": None, "total_posts": None, "error_sites": [],
                "error": "GSC_SERVICE_ACCOUNT_JSON 없음", "site_details": []}
    try:
        token = get_gsc_token()
    except Exception as e:
        return {"total_clicks": None, "total_indexed": None, "total_posts": None, "error_sites": [],
                "error": str(e)[:200], "site_details": []}

    accessible_resp = gsc_get(token, "/sites")
    accessible = set()
    if accessible_resp.status_code == 200:
        accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])}
    log(f"   접근 가능한 GSC 사이트: {len(accessible)}개 / 전체 {len(SITES)}개")

    total_clicks = 0
    total_indexed = 0
    total_posts = 0
    clicks_sites = 0
    indexed_sites = 0
    posts_sites = 0
    error_sites = []
    site_details = []
    for site_url in SITES:
        domain = site_url.rstrip("/").replace("https://", "")
        total_published = get_total_published(site_url)
        if total_published is not None:
            total_posts += total_published
            posts_sites += 1
        visitor_metrics = get_visitor_metrics(site_url)
        visitor_count = visitor_metrics.get("today") if visitor_metrics else None
        domain_property = f"sc-domain:{domain}"
        if site_url in accessible:
            query_site = site_url
        elif domain_property in accessible:
            query_site = domain_property
        else:
            error_sites.append(domain)
            site_details.append({"domain": domain, "url": site_url, "clicks": None,
                                  "indexed": None, "total_posts": total_published,
                                  "visitor_count": visitor_count, "visitor_metrics": visitor_metrics,
                                  "status": "권한없음"})
            continue
        status = "정상"
        clicks = None
        indexed = None
        stats, err = latest_daily_stats(token, query_site)
        if stats:
            total_clicks += stats["clicks"]
            clicks_sites += 1
            clicks = stats["clicks"]
        else:
            error_sites.append(domain)
            status = "오류"
        coverage, _ = get_index_coverage(token, query_site)
        if coverage:
            total_indexed += coverage["indexed"]
            indexed_sites += 1
            indexed = coverage["indexed"]
        site_details.append({"domain": domain, "url": site_url, "clicks": clicks,
                              "indexed": indexed, "total_posts": total_published,
                              "visitor_count": visitor_count, "visitor_metrics": visitor_metrics,
                              "status": status})
        time.sleep(0.2)

    return {"total_clicks": total_clicks if clicks_sites else None,
            "total_indexed": total_indexed if indexed_sites else None,
            "total_posts": total_posts if posts_sites else None,
            "coverage": {"clicks": clicks_sites, "indexed": indexed_sites,
                         "posts": posts_sites, "visitors": sum(
                             1 for d in site_details if d.get("visitor_count") is not None)},
            "error_sites": error_sites, "error": None, "site_details": site_details}


# ════════════════════════════════════════════════════════════
# 2) 유튜브 전 채널 구독자 (한 번의 API 호출로 전부 조회)
# ════════════════════════════════════════════════════════════
def collect_youtube_all():
    """유튜브 채널 통계는 공개정보라, 21개 채널 개별 토큰이 없어도
    아무 채널이나 하나의 broad-scope OAuth 토큰으로 channels().list(id=...)
    조회가 가능하다 — YOUTUBE_API_KEY 없이도 동작하도록 이 방식을 우선 쓴다."""
    ids = [cid for _, cid in YOUTUBE_CHANNELS]

    # 우선 OAuth(broad-scope) 토큰으로 시도 — 채널 소유 여부와 무관하게 공개 통계 조회 가능.
    oauth_token_env = None
    for env_name in os.environ:
        if env_name.startswith("YOUTUBE_OAUTH_REFRESH_TOKEN_") and env_name.endswith("_BROAD"):
            oauth_token_env = env_name
            break

    items = {}
    if oauth_token_env:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(
                token=None,
                refresh_token=os.environ[oauth_token_env],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
                client_secret=os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"],
                scopes=["https://www.googleapis.com/auth/youtube"],
            )
            youtube = build("youtube", "v3", credentials=creds)
            # channels.list는 id 파라미터에 최대 50개까지 콤마로 묶어 한 번에 조회 가능.
            for i in range(0, len(ids), 50):
                chunk = ids[i:i + 50]
                resp = youtube.channels().list(part="statistics,snippet", id=",".join(chunk)).execute()
                for it in resp.get("items", []):
                    items[it["id"]] = it
        except Exception as e:
            items = {}
            oauth_err = str(e)[:200]
        else:
            oauth_err = None
    else:
        oauth_err = "broad-scope YOUTUBE_OAUTH_REFRESH_TOKEN_*_BROAD 없음"

    if not items and YOUTUBE_API_KEY:
        try:
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "statistics,snippet", "id": ",".join(ids), "key": YOUTUBE_API_KEY},
                timeout=15,
            )
            r.raise_for_status()
            items = {it["id"]: it for it in r.json().get("items", [])}
        except Exception as e:
            return {}, f"OAuth 실패({oauth_err}) / API키 실패({str(e)[:150]})"

    if not items:
        return {}, oauth_err or "YOUTUBE_API_KEY 없음"

    result = {}
    for label, cid in YOUTUBE_CHANNELS:
        it = items.get(cid)
        if it:
            result[label] = {
                "subs": int(it["statistics"].get("subscriberCount", 0)),
                "views": int(it["statistics"].get("viewCount", 0)),
            }
        else:
            result[label] = {"subs": None, "views": None}
    return result, None


# ════════════════════════════════════════════════════════════
# 3) 어제 기록과 비교
# ════════════════════════════════════════════════════════════
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def diff(today_val, yesterday_val):
    if today_val is None or yesterday_val is None:
        return None
    return today_val - yesterday_val


# ════════════════════════════════════════════════════════════
# 4) Gemini 분석
# ════════════════════════════════════════════════════════════
def gemini_analysis(summary_text):
    if not GEMINI_API_KEY:
        return "(GEMINI_API_KEY 없어서 분석 생략)", "(GEMINI_API_KEY 없어서 원포인트레슨 생략)"
    prompt = f"""아래는 개인 미디어 사업의 오늘자 종합 현황이다. 사이트 트래픽, 유튜브/SNS
구독자 변화를 보고 핵심만 짚어서 분석하고, 오늘 당장 해볼 만한 구체적 행동 제안을 1개
뽑아라. 과장된 칭찬이나 뻔한 소리 없이 담백하게, 실제 숫자 근거로 말해라.

{summary_text}

반드시 아래 두 줄 형식으로만, 한국어로 답해라(다른 텍스트 없이):
분석: <3~4문장 분석>
원포인트레슨: <오늘 바로 해볼 구체적 행동 제안 1문장>"""
    try:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if "원포인트레슨:" in text:
            analysis_part, lesson_part = text.split("원포인트레슨:", 1)
            analysis = analysis_part.replace("분석:", "").strip()
            lesson = lesson_part.strip()
        else:
            analysis, lesson = text.replace("분석:", "").strip(), "(추출 실패 — 원문 참고)"
        return analysis, lesson
    except Exception as e:
        err = f"(분석 생성 실패: {str(e)[:150]})"
        return err, err


# ════════════════════════════════════════════════════════════
# 5) 발송
# ════════════════════════════════════════════════════════════
def send_to_sheets(record):
    if not SHEETS_WEBHOOK:
        log("⚠️ SHEETS_WEBHOOK 없음 — 웹훅 전송 스킵")
    else:
        try:
            r = requests.post(SHEETS_WEBHOOK, json={"type": "situation_room", "records": [record]}, timeout=20)
            log(f"📊 구글시트 웹훅 전송 완료 HTTP {r.status_code}")
        except Exception as e:
            log(f"⚠️ 구글시트 웹훅 전송 실패: {e}")

    # 웹훅(Apps Script)이 situation_room 타입을 실제로는 어느 탭에도 기록하지
    # 않는 것으로 확인되어, 같은 스프레드시트에 Sheets API로 직접 쓴다.
    import gsheets_direct
    if not SHEET_ID or not gsheets_direct.has_credentials():
        log("⚠️ SHEET_ID 또는 GOOGLE_OAUTH_* 시크릿 없음 — 시트 직접 쓰기 스킵")
        return
    try:
        # 기존 "Youtube-tiktok" 탭과 같은 구조(날짜가 아래로 쌓이고, 오른쪽으로
        # YouTube/TikTok/Facebook/Instagram/Threads가 나열)로 단순화해서 기록.
        # YouTube는 대표 채널(한국어 TOPIK)의 구독자수를 사용.
        now = datetime.now(KST)
        date_label = f"{now.year}-{now.month}-{now.day}-{weekday_kr(now.strftime('%Y-%m-%d'))}"
        header = ["날짜", "YouTube", "TikTok", "Facebook", "Instagram", "Threads"]
        row = [date_label, record.get("yt_한국어(TOPIK)_subs"), record.get("tiktok"),
               record.get("facebook"), record.get("instagram"), record.get("threads")]
        gsheets_direct.append_or_update_tab_row(SHEET_ID, "종합상황실_기록", header, row)
        log("📊 구글시트 직접 쓰기 완료 — 탭: 종합상황실_기록")
    except Exception as e:
        log(f"⚠️ 구글시트 직접 쓰기 실패: {e}")


def _fmt_diff_cell(d):
    if d is None:
        return ""
    return f"+{d}" if d >= 0 else str(d)


def _fmt_value_delta(value, delta):
    if value is None:
        return "미집계(증감 미확인)"
    value_text = f"{value:,}" if isinstance(value, int) else str(value)
    delta_text = "증감 미확인" if delta is None else "0" if delta == 0 else _fmt_diff_cell(delta)
    return f"{value_text}({delta_text})"


def send_youtube_status_to_sheets(yt_stats, yt_diffs, checked_at):
    import gsheets_direct
    if not SHEET_ID or not gsheets_direct.has_credentials():
        return
    try:
        now = datetime.now(KST)
        date_label = f"{now.year}-{now.month}-{now.day}-{weekday_kr(now.strftime('%Y-%m-%d'))}"
        channel_names = [label for label, _ in YOUTUBE_CHANNELS]
        values_by_channel = {}
        for label in channel_names:
            v = yt_stats.get(label, {})
            d = yt_diffs.get(label, {})
            values_by_channel[label] = [
                _fmt_value_delta(v.get("subs"), d.get("subs")),
                _fmt_value_delta(v.get("views"), d.get("views")),
            ]
        # 채널이 10개가 넘고 이름도 길어서, 27개사이트_트래픽처럼 채널명을
        # A열에 세로로 고정하고 날짜를 오른쪽으로 늘려가는 방식이 더 적합.
        gsheets_direct.append_dated_metric_columns(
            SHEET_ID, "유튜브채널현황", channel_names, date_label,
            ["구독자(전일대비)", "누적조회(전일대비)"], values_by_channel,
        )
        log("📊 구글시트 직접 쓰기 완료 — 탭: 유튜브채널현황")
    except Exception as e:
        log(f"⚠️ 구글시트 직접 쓰기 실패: {e}")


def send_morning_asset_dashboard(site_details, blogger_details, yt_stats, yt_diffs,
                                 social_stats, sns_diffs, totals, checked_at):
    """Write one compact summary plus per-asset daily comparison tables."""
    import gsheets_direct
    if not SHEET_ID or not gsheets_direct.has_credentials():
        return
    now = datetime.now(KST)
    date_label = f"{now.year}-{now.month:02d}-{now.day:02d} {weekday_kr(now.strftime('%Y-%m-%d'))}"
    try:
        summary_header = [
            "기준일(KST)", "수집시각(KST)", "WP수집", "WP전체", "오늘방문자합계(전일대비)",
            "누적방문자합계", "검색클릭합계(전일대비)", "색인합계(전일대비)", "공개글합계(전일대비)",
            "YouTube수집", "YouTube전체", "구독자합계", "조회수합계",
            "SNS수집", "SNS전체", "Blogger연결", "Blogger목표", "Tistory연결",
            "Tistory목표", "상태"
        ]
        summary_row = [
            date_label, checked_at, totals["wp_collected"], totals["wp_total"],
            _fmt_value_delta(totals["daily_visitors"], totals["daily_visitors_delta"]),
            _fmt_value_delta(totals["cumulative_visitors"], totals["cumulative_visitors_delta"]),
            _fmt_value_delta(totals["search_clicks"], totals["search_clicks_delta"]),
            _fmt_value_delta(totals["indexed"], totals["indexed_delta"]),
            _fmt_value_delta(totals["posts"], totals["posts_delta"]), totals["youtube_collected"],
            totals["youtube_total"], totals["youtube_subscribers"], totals["youtube_views"],
            totals["sns_collected"], totals["sns_total"], totals["blogger_connected"], 27,
            totals["tistory_connected"], 5, totals["status"],
        ]
        gsheets_direct.append_or_update_tab_row(
            SHEET_ID, "아침_자산요약", summary_header, summary_row
        )

        wp_values = {}
        for item in site_details:
            vm = item.get("visitor_metrics") or {}
            wp_values[item["domain"]] = [
                _fmt_value_delta(vm.get("today"), vm.get("daily_delta")),
                _fmt_value_delta(vm.get("total"), vm.get("total_delta")),
                _fmt_value_delta(item.get("total_posts"), item.get("published_delta")),
                _fmt_value_delta(item.get("indexed"), item.get("indexed_delta")),
                _fmt_value_delta(item.get("clicks"), item.get("clicks_delta")), item.get("status"),
            ]
        gsheets_direct.append_dated_metric_columns(
            SHEET_ID, "아침_WP상세", [item["domain"] for item in site_details], date_label,
            ["오늘방문(전일대비)", "누적방문(오늘증가)", "공개글(전일대비)",
             "구글색인(전일대비)", "검색클릭(전일대비)", "수집상태"],
            wp_values,
        )

        blogger_values = {
            item["domain"]: [
                _fmt_value_delta(item.get("public_posts"), item.get("published_delta")),
                _fmt_value_delta(item.get("indexed"), item.get("indexed_delta")),
                item.get("url"), item.get("status"),
            ]
            for item in blogger_details
        }
        gsheets_direct.append_dated_metric_columns(
            SHEET_ID, "아침_Blogger상세", [item["domain"] for item in blogger_details], date_label,
            ["공개글(전일대비)", "구글색인(전일대비)", "Blogger URL", "수집상태"],
            blogger_values,
        )

        sns_values = {}
        for platform_key, platform_label in (
            ("tiktok", "TikTok"), ("facebook", "Facebook"),
            ("instagram", "Instagram"), ("threads", "Threads"),
        ):
            for brand in BRANDS:
                key = f"{platform_label} · {BRAND_LABELS_KR[brand]}"
                info = social_stats[platform_key][brand]
                sns_values[key] = [
                    _fmt_value_delta(info.get("count"), sns_diffs[platform_key].get(brand)),
                    info.get("error") or ("공개 프로필 참고값; 공식 인사이트 아님" if platform_key == "tiktok" else "공식 API 조회 성공"),
                ]
        gsheets_direct.append_dated_metric_columns(
            SHEET_ID, "아침_SNS상세", list(sns_values), date_label,
            ["팔로워(전일대비)", "상태"], sns_values,
        )
        log("📊 아침 통합 대시보드 4개 탭 갱신 완료")
    except Exception as exc:
        log(f"⚠️ 아침 통합 대시보드 갱신 실패: {exc}")


def send_master_62_dashboard(site_details, blogger_details, checked_at):
    """Write the confirmed 62-asset master snapshot in one numbered table."""
    import gsheets_direct
    if not SHEET_ID or not gsheets_direct.has_credentials():
        return

    rooms_path = Path(REPO_ROOT) / "config" / "automation_rooms.json"
    try:
        rooms = json.loads(rooms_path.read_text(encoding="utf-8")).get("rooms", [])
    except (OSError, ValueError):
        rooms = []
    tistory_rooms = [room for room in rooms if room.get("platform") == "tistory"]
    naver_rooms = [room for room in rooms if room.get("platform") == "naver"]

    rows = []
    number = 1
    for item in site_details:
        vm = item.get("visitor_metrics") or {}
        rows.append([
            number, "WP", item["domain"], item.get("url", ""),
            _fmt_value_delta(item.get("total_posts"), item.get("published_delta")),
            _fmt_value_delta(item.get("indexed"), item.get("indexed_delta")),
            _fmt_value_delta(vm.get("today"), vm.get("daily_delta")),
            _fmt_value_delta(vm.get("total"), vm.get("total_delta")),
            _fmt_value_delta(item.get("clicks"), item.get("clicks_delta")),
            item.get("status", ""), checked_at,
        ])
        number += 1

    # Blogger rows follow the corresponding WP order and reuse its confirmed name.
    for index, item in enumerate(blogger_details):
        wp_name = site_details[index]["domain"] if index < len(site_details) else item.get("name", item["domain"])
        rows.append([
            number, "BLOGSPOT", wp_name, item.get("url", ""),
            _fmt_value_delta(item.get("public_posts"), item.get("published_delta")),
            _fmt_value_delta(item.get("indexed"), item.get("indexed_delta")),
            "", "", "", item.get("status", ""), checked_at,
        ])
        number += 1

    for room in tistory_rooms:
        rows.append([
            number, "TISTORY", room.get("report_code", f"T{number - 54}"),
            room.get("destination_id", ""), "", "", "", "", "",
            "등록완료 · 수치수집 연결 필요", checked_at,
        ])
        number += 1

    for room in naver_rooms:
        rows.append([
            number, "NAVER", room.get("report_code", f"N{number - 59}"),
            room.get("destination_id", ""), "", "", "", "", "",
            "계정 주소 등록 필요", checked_at,
        ])
        number += 1

    if len(rows) != 62:
        raise RuntimeError(f"종합상황실 자산 수 불일치: {len(rows)} (기대 62)")

    header = [
        "번호", "플랫폼", "관리명", "사이트 주소", "공개글(전일대비)",
        "구글색인(전일대비)", "오늘방문(전일대비)", "누적방문(오늘증가)",
        "검색클릭(전일대비)", "수집상태", "기준시각(KST)",
    ]
    gsheets_direct.replace_tab_rows(SHEET_ID, "종합_62개현황", header, rows)
    log("📊 종합_62개현황 갱신 완료 — WP27 + Blogspot27 + Tistory5 + Naver3")


def send_monetization_dashboard(adsense, topik_stats, topik_diff, khealth_metrics, checked_at):
    """Write the two currently monetized assets with audience and revenue KPIs."""
    import gsheets_direct
    if not SHEET_ID or not gsheets_direct.has_credentials():
        return
    vm = khealth_metrics or {}
    currency = adsense.get("currency", "KRW")

    def money(value):
        if value is None:
            return ""
        return f"{value:,.0f} {currency}"

    rows = [
        ["M1", "WEB", "K-health365", "k-health365.com", "AdSense 승인",
         _fmt_value_delta(vm.get("today"), vm.get("daily_delta")), "",
         money(adsense.get("today")), money(adsense.get("month")),
         money(adsense.get("cumulative")), adsense.get("status", ""), checked_at],
        ["M2", "YOUTUBE", "한국어(TOPIK)", "https://www.youtube.com/@seoultopik", "수익화 승인",
         _fmt_value_delta(topik_stats.get("views"), topik_diff.get("views")),
         _fmt_value_delta(topik_stats.get("subs"), topik_diff.get("subs")),
         "", "", "", "YouTube 수익 OAuth 연결 필요", checked_at],
    ]
    header = [
        "번호", "플랫폼", "수익화 자산", "주소", "승인상태", "조회·방문(증감)",
        "구독자·회원(증감)", "오늘 추정수익", "이번달 추정수익",
        "올해 누적 추정수익", "수집상태", "기준시각(KST)",
    ]
    gsheets_direct.replace_tab_rows(SHEET_ID, "수익화_현황", header, rows)
    log("💰 수익화_현황 갱신 완료 — K-health365 + YouTube TOPIK")


def send_email(subject, body):
    if not GMAIL_APP_PASSWORD:
        log("⚠️ GMAIL_APP_PASSWORD 없음 — 이메일 스킵")
        return
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, [GMAIL_USER], msg.as_string())
        log("📧 이메일 발송 완료")
    except Exception as e:
        log(f"⚠️ 이메일 발송 실패: {e}")


def get_kakao_access_token():
    r = requests.post("https://kauth.kakao.com/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN,
    }, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def send_kakao(text, link_url):
    if not (KAKAO_REST_API_KEY and KAKAO_REFRESH_TOKEN):
        log("⚠️ KAKAO 시크릿 없음 — 카카오톡 발송 스킵")
        return
    try:
        access_token = get_kakao_access_token()
        template = {
            "object_type": "text",
            "text": text[:190],
            "link": {"web_url": link_url, "mobile_web_url": link_url},
        }
        r = requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {access_token}"},
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=15,
        )
        log(f"💬 카카오톡 발송 {'완료' if r.status_code == 200 else '실패'} HTTP {r.status_code} {r.text[:150]}")
    except Exception as e:
        log(f"⚠️ 카카오톡 발송 실패: {e}")


# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def main():
    checked_at = now_kst_str()
    history = load_history()
    yesterday = history.get("latest", {})

    log("1/4 사이트 트래픽 요약 수집 중...")
    site_summary = collect_site_summary()
    log(f"   전체글수 합계 {site_summary['total_posts']} / 클릭 합계 {site_summary['total_clicks']} "
        f"/ 색인 합계 {site_summary['total_indexed']} / 오류사이트 {len(site_summary['error_sites'])}개")

    log("   Blogger 27개 공개글·색인 현황 수집 중...")
    blogger_details = collect_blogger_summary()
    log(f"   Blogger {len(blogger_details)}개 목록 확인")

    log("2/4 유튜브 전 채널 구독자 수집 중...")
    yt_stats, yt_err = collect_youtube_all()
    for label, v in yt_stats.items():
        log(f"   {label}: 구독자 {v['subs']} / 조회수 {v['views']}")

    adsense_metrics = collect_adsense_khealth_revenue()
    log(f"   AdSense K-health365: {adsense_metrics.get('status')}")

    log("3/4 틱톡/페이스북/인스타그램/Threads 3개 브랜드씩 수집 중...")
    tiktok_m = get_tiktok_followers_multi()
    facebook_m = get_facebook_followers_multi()
    instagram_m = get_instagram_followers_multi()
    threads_m = get_threads_followers_multi()
    for plat_name, m in (("TikTok", tiktok_m), ("Facebook", facebook_m),
                         ("Instagram", instagram_m), ("Threads", threads_m)):
        configured = sum(1 for b in BRANDS if m[b]["count"] is not None)
        log(f"   {plat_name}: {configured}/3 설정됨")

    site_details_list = site_summary.get("site_details", [])
    today = {
        "site_clicks": site_summary["total_clicks"],
        "site_indexed": site_summary["total_indexed"],
        "site_posts": site_summary["total_posts"],
        "site_details": {d["domain"]: {"clicks": d["clicks"], "indexed": d["indexed"],
                                        "total_posts": d.get("total_posts"), "status": d["status"],
                                        "visitor_count": d.get("visitor_count")}
                          for d in site_details_list},
        "blogger_details": {
            d["domain"]: {"public_posts": d.get("public_posts"), "indexed": d.get("indexed"),
                          "status": d.get("status")}
            for d in blogger_details
        },
        "youtube": yt_stats,
        "adsense_khealth365": adsense_metrics,
        "tiktok": tiktok_m, "facebook": facebook_m,
        "instagram": instagram_m, "threads": threads_m,
    }

    # 증감 계산
    yesterday_yt = yesterday.get("youtube", {})

    def _yesterday_metric(label, key):
        # situation_room_history.json의 예전 기록은 채널당 값이 dict가 아니라
        # 구독자수 정수 하나였다(조회수 구분 이전 형식) — dict가 아니면 구독자수로
        # 취급하고 조회수는 그 시절엔 기록이 없었으므로 None으로 처리한다.
        y = yesterday_yt.get(label)
        if isinstance(y, dict):
            return y.get(key)
        return y if key == "subs" else None

    yt_diffs = {
        label: {
            "subs": diff(v.get("subs"), _yesterday_metric(label, "subs")),
            "views": diff(v.get("views"), _yesterday_metric(label, "views")),
        }
        for label, v in today["youtube"].items()
    }
    d_site_clicks = diff(today["site_clicks"], yesterday.get("site_clicks"))
    d_site_indexed = diff(today["site_indexed"], yesterday.get("site_indexed"))
    d_site_posts = diff(today["site_posts"], yesterday.get("site_posts"))
    yesterday_sites = yesterday.get("site_details", {})
    yesterday_bloggers = yesterday.get("blogger_details", {})

    for item in site_details_list:
        previous = yesterday_sites.get(item["domain"], {})
        item["published_delta"] = diff(item.get("total_posts"), previous.get("total_posts"))
        item["indexed_delta"] = diff(item.get("indexed"), previous.get("indexed"))
        item["clicks_delta"] = diff(item.get("clicks"), previous.get("clicks"))
    for item in blogger_details:
        previous = yesterday_bloggers.get(item["domain"], {})
        item["published_delta"] = diff(item.get("public_posts"), previous.get("public_posts"))
        item["indexed_delta"] = diff(item.get("indexed"), previous.get("indexed"))

    def _site_comment(status, clicks, d_clicks, indexed, total_posts):
        if status != "정상":
            return "⚠️ 접근 오류/권한 확인 필요"
        if total_posts == 0:
            return "🚫 공개글 0건 (비공개 정리 진행 중이거나 완료됨)"
        if clicks is None:
            return "데이터 없음(신규 사이트 또는 검색 유입 없음)"
        if d_clicks is None:
            return "첫 기록 시작"
        if d_clicks > 0:
            return f"방문자 증가 중(+{d_clicks})"
        if d_clicks < 0:
            return f"방문자 감소({d_clicks}) — 점검 필요"
        if not indexed:
            return "변동 없음, 색인 확인 필요"
        return "안정적 유지"

    def fmt_diff(d):
        if d is None:
            return ""
        return f"(+{d})" if d >= 0 else f"({d})"

    def _sns_diffs(platform_key, today_m):
        yesterday_m = yesterday.get(platform_key, {})
        if not isinstance(yesterday_m, dict):
            yesterday_m = {}
        out = {}
        for b in BRANDS:
            y = yesterday_m.get(b, {})
            y_count = y.get("count") if isinstance(y, dict) else None
            out[b] = diff(today_m[b]["count"], y_count)
        return out

    sns_diffs = {
        "tiktok": _sns_diffs("tiktok", tiktok_m),
        "facebook": _sns_diffs("facebook", facebook_m),
        "instagram": _sns_diffs("instagram", instagram_m),
        "threads": _sns_diffs("threads", threads_m),
    }

    topik_stats = today["youtube"].get("한국어(TOPIK)", {})
    topik_diff = yt_diffs.get("한국어(TOPIK)", {})
    khealth_item = next(
        (item for item in site_details_list if item["domain"] == "k-health365.com"), {}
    )
    khealth_vm = khealth_item.get("visitor_metrics") or {}

    def fmt_money(value):
        return "-" if value is None else f"{value:,.0f} KRW"

    yt_channel_id = dict(YOUTUBE_CHANNELS)

    site_count = len(SITES)
    youtube_count = len(YOUTUBE_CHANNELS)
    sns_platform_count = 4
    sns_account_count = len(BRANDS) * sns_platform_count
    ok_sites = sum(1 for d in site_details_list if d["status"] == "정상")
    total_yt_subs = sum(v["subs"] for v in today["youtube"].values() if v.get("subs") is not None)
    total_yt_views = sum(v["views"] for v in today["youtube"].values() if v.get("views") is not None)
    sns_connected = sum(
        1 for m in (tiktok_m, facebook_m, instagram_m, threads_m) for b in BRANDS
        if m[b]["count"] is not None
    )

    visitor_sites = sum(1 for d in site_details_list if d.get("visitor_count") is not None)
    total_real_visitors = sum(
        d["visitor_count"] for d in site_details_list if d.get("visitor_count") is not None
    )
    total_cumulative_visitors = sum(
        (d.get("visitor_metrics") or {}).get("total", 0) for d in site_details_list
    )
    total_today_delta = sum(
        (d.get("visitor_metrics") or {}).get("daily_delta", 0) for d in site_details_list
    )
    total_cumulative_delta = sum(
        (d.get("visitor_metrics") or {}).get("total_delta", 0) for d in site_details_list
    )
    summary_lines = [
        f"[{checked_at}] 종합상황실",
        "",
        "📊 한눈에 보기",
        f"  사이트 {ok_sites}/{site_count} 정상 | 전체글수 {today['site_posts']} {fmt_diff(d_site_posts)} | "
        f"Google 검색 클릭 합계 {today['site_clicks']} {fmt_diff(d_site_clicks)} | "
        f"사이트맵 색인 합계 {today['site_indexed']} {fmt_diff(d_site_indexed)} | "
        f"오늘방문 합계 {total_real_visitors}{fmt_diff(total_today_delta)}명(수집 {visitor_sites}/{site_count})",
        f"  WP 누적방문 합계 {total_cumulative_visitors}{fmt_diff(total_cumulative_delta)}명",
        f"  유튜브 {youtube_count}채널 구독자합계 {total_yt_subs}명 | 조회수합계 {total_yt_views}회",
        f"  SNS 연결계정 {sns_connected}/{sns_account_count}개",
        "",
        "💰 수익화 핵심 2개",
        f"  K-health365 | 오늘 {fmt_money(adsense_metrics.get('today'))} | "
        f"이번달 {fmt_money(adsense_metrics.get('month'))} | "
        f"올해 누적 {fmt_money(adsense_metrics.get('cumulative'))} | "
        f"방문 {_fmt_value_delta(khealth_vm.get('today'), khealth_vm.get('daily_delta')) or '-'} | "
        f"{adsense_metrics.get('status', '')}",
        f"  YouTube TOPIK | 구독자 "
        f"{_fmt_value_delta(topik_stats.get('subs'), topik_diff.get('subs')) or '-'} | "
        f"누적조회 {_fmt_value_delta(topik_stats.get('views'), topik_diff.get('views')) or '-'} | "
        "YouTube 수익 OAuth 연결 필요",
        "",
        f"■ 사이트 {site_count}개 — 전체글수 {today['site_posts']} {fmt_diff(d_site_posts)} / "
        f"Google 검색 클릭 합계 {today['site_clicks']} {fmt_diff(d_site_clicks)} / "
        f"사이트맵 색인 합계 {today['site_indexed']} {fmt_diff(d_site_indexed)} / "
        f"오늘방문 합계 {total_real_visitors}{fmt_diff(total_today_delta)}명(수집 {visitor_sites}/{site_count})",
    ]
    for d in site_details_list:
        domain = d["domain"]
        y = yesterday_sites.get(domain, {})
        d_clicks = diff(d["clicks"], y.get("clicks"))
        d_posts = diff(d.get("total_posts"), y.get("total_posts"))
        d_indexed = diff(d["indexed"], y.get("indexed"))
        # 방문자 증감은 사이트 카운터가 제공하는 오늘-어제 값을 직접 사용한다.
        vm = d.get("visitor_metrics") or {}
        d_visitors = vm.get("daily_delta")
        if d_visitors is None:
            d_visitors = diff(d.get("visitor_count"), y.get("visitor_count"))
        comment = _site_comment(d["status"], d["clicks"], d_clicks, d["indexed"], d.get("total_posts"))
        clicks_str = d["clicks"] if d["clicks"] is not None else "-"
        posts_str = d.get("total_posts") if d.get("total_posts") is not None else "-"
        indexed_str = d["indexed"] if d["indexed"] is not None else "-"
        visitors_str = d.get("visitor_count") if d.get("visitor_count") is not None else "미배포"
        total_visitors = vm.get("total")
        total_visitors_str = total_visitors if total_visitors is not None else "미배포"
        total_delta = vm.get("total_delta")
        summary_lines.append(
            f"  - {domain} | {d['url']} | 전체글 {posts_str}{fmt_diff(d_posts)} | "
            f"사이트맵 색인 {indexed_str}{fmt_diff(d_indexed)} | Google 검색 클릭 {clicks_str}{fmt_diff(d_clicks)} | "
            f"오늘방문 {visitors_str}{fmt_diff(d_visitors)} | "
            f"누적방문 {total_visitors_str}{fmt_diff(total_delta)} | {comment}")
    summary_lines += [
        "",
        f"■ 유튜브 전체 운영채널 (총 {youtube_count}개)",
    ]
    for label, v in today["youtube"].items():
        d = yt_diffs.get(label, {})
        cid = yt_channel_id.get(label, "")
        url = f"https://www.youtube.com/channel/{cid}" if cid else "(URL 미확인)"
        summary_lines.append(
            f"  - {label} | {url} | 구독자 {v['subs']} {fmt_diff(d.get('subs'))} | 조회수 {v['views']} {fmt_diff(d.get('views'))}")
    yt_configured = sum(1 for v in today["youtube"].values() if v.get("subs") is not None)
    summary_lines.append(f"  => 총평: {yt_configured}/{youtube_count}개 채널 수집됨. "
                          f"{'TOPIK이 압도적 1위, 나머지는 초기 단계' if yt_configured else '수집 실패'}")

    def _sns_section(title, platform_key, today_m, url_platform):
        lines = [f"", f"■ {title} (3개 브랜드: TOPIK/English/Language)"]
        configured = 0
        for b in BRANDS:
            info = today_m[b]
            d = sns_diffs[platform_key].get(b)
            label_kr = BRAND_LABELS_KR[b]
            if info["count"] is not None:
                configured += 1
                fallback_id = info.get("page_id") if platform_key == "facebook" else None
                url = _platform_url(url_platform, b, fallback_id=fallback_id)
                lines.append(f"  - {label_kr} | {url} | 팔로워 {info['count']} {fmt_diff(d)}")
            else:
                lines.append(f"  - {label_kr} | 미설정 ({info['error']})")
        lines.append(f"  => 총평: {configured}/3개 브랜드 계정 연결됨"
                      + ("" if configured == 3 else f" — {3 - configured}개는 계정 생성/시크릿 등록 필요"))
        return lines

    summary_lines += _sns_section("TikTok", "tiktok", tiktok_m, "tiktok")
    summary_lines += _sns_section("Facebook 페이지", "facebook", facebook_m, "facebook")
    summary_lines += _sns_section("Instagram", "instagram", instagram_m, "instagram")
    summary_lines += _sns_section("Threads", "threads", threads_m, "threads")

    summary_lines += ["", "■ 전체 계정 URL 모음"]
    summary_lines.append(f"  [사이트 {site_count}개]")
    for d in site_details_list:
        summary_lines.append(f"    - {d['domain']}: {d['url']}")
    summary_lines.append(f"  [유튜브 {youtube_count}채널]")
    for label, cid in YOUTUBE_CHANNELS:
        summary_lines.append(f"    - {label}: https://www.youtube.com/channel/{cid}")
    for title, platform_key, url_platform in (
        ("TikTok", "tiktok", "tiktok"), ("Facebook", "facebook", "facebook"),
        ("Instagram", "instagram", "instagram"), ("Threads", "threads", "threads"),
    ):
        summary_lines.append(f"  [{title} 3브랜드]")
        for b in BRANDS:
            info = (tiktok_m if platform_key == "tiktok" else facebook_m if platform_key == "facebook"
                    else instagram_m if platform_key == "instagram" else threads_m)[b]
            fallback_id = info.get("page_id") if platform_key == "facebook" else None
            url = _platform_url(url_platform, b, fallback_id=fallback_id)
            summary_lines.append(f"    - {BRAND_LABELS_KR[b]}: {url}")

    summary_text = "\n".join(summary_lines)
    log(summary_text)

    log("4/4 Gemini 분석 생성 중...")
    analysis, one_point_lesson = gemini_analysis(summary_text)
    log(analysis)
    log(f"[원포인트레슨] {one_point_lesson}")

    sheet_link = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit" if SHEET_ID else ""

    # 시트 전송용 레코드(플랫한 dict). "tiktok"/"facebook"/"instagram"/"threads"는
    # 기존 시트 탭 구조(단일 채널 시절)와 호환을 위해 TOPIK 브랜드 값을 대표로 넣고,
    # 브랜드별 상세는 별도 키로 전부 남긴다.
    record = {"checked_at": checked_at, "site_clicks": today["site_clicks"],
              "site_indexed": today["site_indexed"], "site_posts": today["site_posts"],
              "tiktok": today["tiktok"]["TOPIK"]["count"],
              "facebook": today["facebook"]["TOPIK"]["count"],
              "instagram": today["instagram"]["TOPIK"]["count"],
              "threads": today["threads"]["TOPIK"]["count"],
              "analysis": analysis, "one_point_lesson": one_point_lesson}
    for label, v in today["youtube"].items():
        record[f"yt_{label}_subs"] = v["subs"]
        record[f"yt_{label}_views"] = v["views"]
    for platform_key in ("tiktok", "facebook", "instagram", "threads"):
        for b in BRANDS:
            record[f"{platform_key}_{b}_count"] = today[platform_key][b]["count"]
    send_to_sheets(record)
    send_youtube_status_to_sheets(yt_stats, yt_diffs, checked_at)

    registry_path = Path(REPO_ROOT) / "config" / "automation_hub_sites.json"
    tistory_path = Path(REPO_ROOT) / "config" / "tistory_portfolio.json"
    try:
        registry_sites = json.loads(registry_path.read_text(encoding="utf-8")).get("sites", [])
        blogger_connected = sum(1 for site in registry_sites if site.get("platform") == "blogger")
    except Exception:
        blogger_connected = 0
    try:
        tistory_connected = sum(
            1 for site in json.loads(tistory_path.read_text(encoding="utf-8")).get("sites", [])
            if site.get("launch_enabled") is True
        )
    except Exception:
        tistory_connected = 0
    dashboard_totals = {
        "wp_collected": visitor_sites,
        "wp_total": site_count,
        "daily_visitors": total_real_visitors,
        "daily_visitors_delta": total_today_delta,
        "cumulative_visitors": total_cumulative_visitors,
        "cumulative_visitors_delta": total_cumulative_delta,
        "search_clicks": today["site_clicks"],
        "search_clicks_delta": d_site_clicks,
        "indexed": today["site_indexed"],
        "indexed_delta": d_site_indexed,
        "posts": today["site_posts"],
        "posts_delta": d_site_posts,
        "youtube_collected": yt_configured,
        "youtube_total": youtube_count,
        "youtube_subscribers": total_yt_subs,
        "youtube_views": total_yt_views,
        "sns_collected": sns_connected,
        "sns_total": sns_account_count,
        "blogger_connected": blogger_connected,
        "tistory_connected": tistory_connected,
        "status": "정상" if visitor_sites == site_count and yt_configured == youtube_count else "일부수집",
    }
    send_morning_asset_dashboard(
        site_details_list, blogger_details, yt_stats, yt_diffs,
        {"tiktok": tiktok_m, "facebook": facebook_m, "instagram": instagram_m, "threads": threads_m},
        sns_diffs, dashboard_totals, checked_at,
    )
    send_master_62_dashboard(site_details_list, blogger_details, checked_at)
    send_monetization_dashboard(
        adsense_metrics, topik_stats, topik_diff, khealth_vm, checked_at
    )

    send_email(f"[종합상황실] {checked_at[:10]} 오늘 방문자·증감 리포트",
               summary_text + "\n\n[AI 분석]\n" + analysis +
               "\n\n[오늘의 원포인트레슨]\n" + one_point_lesson +
               (f"\n\n시트: {sheet_link}" if sheet_link else ""))

    kakao_text = (summary_lines[0] + "\n" +
                  f"사이트 {ok_sites}/{site_count}정상 전체글{today['site_posts']}{fmt_diff(d_site_posts)} "
                  f"클릭{today['site_clicks']}{fmt_diff(d_site_clicks)} / "
                  f"색인{today['site_indexed']}{fmt_diff(d_site_indexed)}\n" +
                  f"[원포인트레슨] {one_point_lesson}"[:80])
    send_kakao(kakao_text, sheet_link or "https://github.com/huh0303-cmyk/-WP-QWEN-autobot")

    history["latest"] = today
    history["updated_at"] = checked_at
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    log("완료")


if __name__ == "__main__":
    main()
