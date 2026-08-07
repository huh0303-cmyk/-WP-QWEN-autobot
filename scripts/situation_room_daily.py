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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_site_traffic import (  # noqa: E402
    get_gsc_token, gsc_get, latest_daily_stats, get_index_coverage, SITES, weekday_kr,
)
from social_stats_daily import (  # noqa: E402
    get_tiktok_followers_multi, get_facebook_followers_multi,
    get_instagram_followers_multi, get_threads_followers_multi, BRANDS,
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KST = timezone(timedelta(hours=9))
HISTORY_FILE = "situation_room_history.json"

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SHEETS_WEBHOOK = os.environ.get("SHEETS_WEBHOOK", "")
SHEET_ID = os.environ.get("SHEET_ID", "")
GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN", "")

# 2026-08-06 확정: 언어 채널 3개(TOPIK/English/10개국어) + 플리 채널 5개.
# 예전 목록은 채널이 리네임/재배정되면서 라벨과 실제 채널이 어긋나 있었다
# (예: "스페인어(Survival Spanish)" 라벨이 실제로는 starbucks 채널을 가리키는 등) —
# 채널ID는 표시이름이 바뀌어도 안 바뀌므로 항상 ID를 기준으로 매칭한다.
# 상세 내역: memory project_playlist_channels / project_youtube_language_channels.
#
# 2026-08-07: MBB/K-pop을 원래 채널(Mozart-Bach-Beethoven/K-pop Studio, 둘 다
# 2026-08-02 개설)에서 더 오래된(2025-05-10 개설) 완전 빈 채널로 교체 —
# 새로 만든 채널 OAuth 인증 시 전화번호 재인증 벽에 막혀서, 오래된 채널이
# 그 벽에 덜 걸릴 거라는 가설로 바꿈. 실제 채널 표시이름은 아직
# "Studio-K7"/"Studio_Global"로 남아있어 리네임 필요(기능엔 지장 없음).
YOUTUBE_CHANNELS = [
    ("한국어(TOPIK)", "UCdA24IuR-JE7qButWv5jLqA"),
    ("영어(English Survival)", "UCrjkKWMHzAAvpLIFgHnwcWg"),
    ("다국어(Language, 10개국어)", "UCOWoNH_d6p45ywQ6W0Z1Jng"),
    ("플리-수노달달로맨틱(globalmusic)", "UCbJfEtsffpgI5MsKkB7BYvQ"),
    ("플리-힐링(healing)", "UC7yEsLM-HoXudngrD-4FIqg"),
    ("플리-MBB(Studio-K7 재배정)", "UCKZsfAWyCmY0jckf4IWZrqw"),
    ("플리-카페음악(starbucks)", "UC_e-sbLkVgwJNYEeobolNog"),
    ("플리-K-pop(Studio_Global 재배정)", "UCRZ0uc_bxKDMwz3noBBi9KQ"),
]

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
def collect_site_summary():
    if not os.environ.get("GSC_SERVICE_ACCOUNT_JSON"):
        return {"total_clicks": None, "total_indexed": None, "error_sites": [],
                "error": "GSC_SERVICE_ACCOUNT_JSON 없음", "site_details": []}
    try:
        token = get_gsc_token()
    except Exception as e:
        return {"total_clicks": None, "total_indexed": None, "error_sites": [],
                "error": str(e)[:200], "site_details": []}

    accessible_resp = gsc_get(token, "/sites")
    accessible = set()
    if accessible_resp.status_code == 200:
        accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])}
    log(f"   접근 가능한 GSC 사이트: {len(accessible)}개 / 전체 {len(SITES)}개")

    total_clicks = 0
    total_indexed = 0
    error_sites = []
    site_details = []
    for site_url in SITES:
        domain = site_url.rstrip("/").replace("https://", "")
        domain_property = f"sc-domain:{domain}"
        if site_url in accessible:
            query_site = site_url
        elif domain_property in accessible:
            query_site = domain_property
        else:
            error_sites.append(domain)
            site_details.append({"domain": domain, "url": site_url, "clicks": None,
                                  "indexed": None, "status": "권한없음"})
            continue
        status = "정상"
        clicks = None
        indexed = None
        stats, err = latest_daily_stats(token, query_site)
        if stats:
            total_clicks += stats["clicks"]
            clicks = stats["clicks"]
        else:
            error_sites.append(domain)
            status = "오류"
        coverage, _ = get_index_coverage(token, query_site)
        if coverage:
            total_indexed += coverage["indexed"]
            indexed = coverage["indexed"]
        site_details.append({"domain": domain, "url": site_url, "clicks": clicks,
                              "indexed": indexed, "status": status})
        time.sleep(0.2)

    return {"total_clicks": total_clicks, "total_indexed": total_indexed,
            "error_sites": error_sites, "error": None, "site_details": site_details}


# ════════════════════════════════════════════════════════════
# 2) 유튜브 전 채널 구독자 (한 번의 API 호출로 전부 조회)
# ════════════════════════════════════════════════════════════
def collect_youtube_all():
    if not YOUTUBE_API_KEY:
        return {}, "YOUTUBE_API_KEY 없음"
    ids = ",".join(cid for _, cid in YOUTUBE_CHANNELS)
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics,snippet", "id": ids, "key": YOUTUBE_API_KEY},
            timeout=15,
        )
        r.raise_for_status()
        items = {it["id"]: it for it in r.json().get("items", [])}
    except Exception as e:
        return {}, str(e)[:200]

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
                v.get("subs"), _fmt_diff_cell(d.get("subs")),
                v.get("views"), _fmt_diff_cell(d.get("views")),
            ]
        # 채널이 10개가 넘고 이름도 길어서, 27개사이트_트래픽처럼 채널명을
        # A열에 세로로 고정하고 날짜를 오른쪽으로 늘려가는 방식이 더 적합.
        gsheets_direct.append_dated_metric_columns(
            SHEET_ID, "유튜브채널현황", channel_names, date_label,
            ["구독자수", "증가", "조회수", "증가"], values_by_channel,
        )
        log("📊 구글시트 직접 쓰기 완료 — 탭: 유튜브채널현황")
    except Exception as e:
        log(f"⚠️ 구글시트 직접 쓰기 실패: {e}")


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
    log(f"   클릭 합계 {site_summary['total_clicks']} / 색인 합계 {site_summary['total_indexed']} "
        f"/ 오류사이트 {len(site_summary['error_sites'])}개")

    log("2/4 유튜브 전 채널 구독자 수집 중...")
    yt_stats, yt_err = collect_youtube_all()
    for label, v in yt_stats.items():
        log(f"   {label}: 구독자 {v['subs']} / 조회수 {v['views']}")

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
        "site_details": {d["domain"]: {"clicks": d["clicks"], "indexed": d["indexed"], "status": d["status"]}
                          for d in site_details_list},
        "youtube": yt_stats,
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
    yesterday_sites = yesterday.get("site_details", {})

    def _site_comment(status, clicks, d_clicks, indexed):
        if status != "정상":
            return "⚠️ 접근 오류/권한 확인 필요"
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

    yt_channel_id = dict(YOUTUBE_CHANNELS)

    ok_sites = sum(1 for d in site_details_list if d["status"] == "정상")
    total_yt_subs = sum(v["subs"] for v in today["youtube"].values() if v.get("subs") is not None)
    total_yt_views = sum(v["views"] for v in today["youtube"].values() if v.get("views") is not None)
    sns_connected = sum(
        1 for m in (tiktok_m, facebook_m, instagram_m, threads_m) for b in BRANDS
        if m[b]["count"] is not None
    )

    summary_lines = [
        f"[{checked_at}] 종합상황실",
        "",
        "📊 한눈에 보기",
        f"  사이트 {ok_sites}/27 정상 | 클릭합계 {today['site_clicks']} {fmt_diff(d_site_clicks)} | "
        f"색인합계 {today['site_indexed']} {fmt_diff(d_site_indexed)}",
        f"  유튜브 8채널 구독자합계 {total_yt_subs}명 | 조회수합계 {total_yt_views}회",
        f"  SNS 연결계정 {sns_connected}/12개",
        "",
        f"■ 사이트 27개 — 클릭 합계 {today['site_clicks']} {fmt_diff(d_site_clicks)} / "
        f"색인 합계 {today['site_indexed']} {fmt_diff(d_site_indexed)}",
    ]
    for d in site_details_list:
        domain = d["domain"]
        y = yesterday_sites.get(domain, {})
        d_clicks = diff(d["clicks"], y.get("clicks"))
        comment = _site_comment(d["status"], d["clicks"], d_clicks, d["indexed"])
        clicks_str = d["clicks"] if d["clicks"] is not None else "-"
        summary_lines.append(
            f"  - {domain} | {d['url']} | 방문자 {clicks_str}{fmt_diff(d_clicks)} | {comment}")
    summary_lines += [
        "",
        "■ 유튜브 (언어채널 3 + 플리채널 5, 총 8개)",
    ]
    for label, v in today["youtube"].items():
        d = yt_diffs.get(label, {})
        cid = yt_channel_id.get(label, "")
        url = f"https://www.youtube.com/channel/{cid}" if cid else "(URL 미확인)"
        summary_lines.append(
            f"  - {label} | {url} | 구독자 {v['subs']} {fmt_diff(d.get('subs'))} | 조회수 {v['views']} {fmt_diff(d.get('views'))}")
    yt_configured = sum(1 for v in today["youtube"].values() if v.get("subs") is not None)
    summary_lines.append(f"  => 총평: {yt_configured}/8개 채널 수집됨. "
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
    summary_lines.append("  [사이트 27개]")
    for d in site_details_list:
        summary_lines.append(f"    - {d['domain']}: {d['url']}")
    summary_lines.append("  [유튜브 8채널]")
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
              "site_indexed": today["site_indexed"],
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

    send_email(f"[종합상황실] {checked_at[:10]} 현황 리포트",
               summary_text + "\n\n[AI 분석]\n" + analysis +
               "\n\n[오늘의 원포인트레슨]\n" + one_point_lesson +
               (f"\n\n시트: {sheet_link}" if sheet_link else ""))

    kakao_text = (summary_lines[0] + "\n" +
                  f"사이트 {ok_sites}/27정상 클릭{today['site_clicks']}{fmt_diff(d_site_clicks)} / "
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
