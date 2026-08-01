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
    get_tiktok_followers, get_facebook_followers,
    get_instagram_followers, get_threads_followers,
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

# 언어 채널 5개 + 플리/건강 후보 5개 - 전부 huh0303 계정 소속
YOUTUBE_CHANNELS = [
    ("한국어(TOPIK)", "UCdA24IuR-JE7qButWv5jLqA"),
    ("영어(Survival English)", "UCKZsfAWyCmY0jckf4IWZrqw"),
    ("일본어(Survival Japanese)", "UCC_PcHMv-Uxpr00Pjw_J2Wg"),
    ("스페인어(Survival Spanish)", "UCOWoNH_d6p45ywQ6W0Z1Jng"),
    ("베트남어(Survival Vietnamese)", "UCtNLZO07Oh3UnXPI2CjOgNg"),
    ("음악(globalmusic)", "UCbJfEtsffpgI5MsKkB7BYvQ"),
    ("힐링(healing)", "UC7yEsLM-HoXudngrD-4FIqg"),
    ("건강(Studio_Health)", "UCAizx0tPkRSol8sIhanN_QQ"),
    ("건강(Clinic_Health_EN)", "UC91BpNSb4nUwD6jrpthK7FQ"),
    ("여분(Studio_Global)", "UCRZ0uc_bxKDMwz3noBBi9KQ"),
]


def log(msg):
    print(msg, flush=True)


def now_kst_str():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


# ════════════════════════════════════════════════════════════
# 1) 27개 사이트 요약 (상세 아니라 합계만)
# ════════════════════════════════════════════════════════════
def collect_site_summary():
    if not os.environ.get("GSC_SERVICE_ACCOUNT_JSON"):
        return {"total_clicks": None, "total_indexed": None, "error_sites": [], "error": "GSC_SERVICE_ACCOUNT_JSON 없음"}
    try:
        token = get_gsc_token()
    except Exception as e:
        return {"total_clicks": None, "total_indexed": None, "error_sites": [], "error": str(e)[:200]}

    accessible_resp = gsc_get(token, "/sites")
    accessible = set()
    if accessible_resp.status_code == 200:
        accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])}
    log(f"   접근 가능한 GSC 사이트: {len(accessible)}개 / 전체 {len(SITES)}개")

    total_clicks = 0
    total_indexed = 0
    error_sites = []
    for site_url in SITES:
        domain = site_url.rstrip("/").replace("https://", "")
        domain_property = f"sc-domain:{domain}"
        if site_url in accessible:
            query_site = site_url
        elif domain_property in accessible:
            query_site = domain_property
        else:
            error_sites.append(domain)
            continue
        stats, err = latest_daily_stats(token, query_site)
        if stats:
            total_clicks += stats["clicks"]
        else:
            error_sites.append(domain)
        coverage, _ = get_index_coverage(token, query_site)
        if coverage:
            total_indexed += coverage["indexed"]
        time.sleep(0.2)

    return {"total_clicks": total_clicks, "total_indexed": total_indexed,
            "error_sites": error_sites, "error": None}


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
        return "(GEMINI_API_KEY 없어서 분석 생략)"
    prompt = f"""아래는 개인 미디어 사업의 오늘자 종합 현황이다. 사이트 트래픽, 유튜브/SNS
구독자 변화를 보고 핵심만 짚어서 3~4문장으로 분석하고, 오늘 당장 해볼 만한 행동 제안을
1~2개만 짧게 제시해라. 과장된 칭찬이나 뻔한 소리 없이 담백하게, 실제 숫자 근거로 말해라.

{summary_text}

한국어로, 총 5문장 이내로 답해라."""
    try:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"(분석 생성 실패: {str(e)[:150]})"


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
        gsheets_direct.append_tab_row(SHEET_ID, "종합상황실_기록", header, row)
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
        # Youtube-tiktok/종합상황실_기록과 같은 방향 — 날짜가 아래로 쌓이고(행),
        # 채널명은 오른쪽으로(열) 나열. 채널마다 구독자수/증가/조회수/증가 4컬럼.
        header = ["날짜"]
        row = [date_label]
        for label in channel_names:
            v = yt_stats.get(label, {})
            d = yt_diffs.get(label, {})
            header += [f"{label} 구독자", f"{label} 증가", f"{label} 조회수", f"{label} 증가"]
            row += [v.get("subs"), _fmt_diff_cell(d.get("subs")),
                    v.get("views"), _fmt_diff_cell(d.get("views"))]
        gsheets_direct.append_tab_row(SHEET_ID, "유튜브채널현황", header, row)
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

    log("3/4 기타 SNS 수집 중...")
    tiktok, _ = get_tiktok_followers()
    facebook, _ = get_facebook_followers()
    instagram, _ = get_instagram_followers()
    threads, _ = get_threads_followers()
    log(f"   TikTok {tiktok} / Facebook {facebook} / Instagram {instagram} / Threads {threads}")

    today = {
        "site_clicks": site_summary["total_clicks"],
        "site_indexed": site_summary["total_indexed"],
        "youtube": yt_stats,
        "tiktok": tiktok, "facebook": facebook, "instagram": instagram, "threads": threads,
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
    d_tiktok = diff(today["tiktok"], yesterday.get("tiktok"))
    d_facebook = diff(today["facebook"], yesterday.get("facebook"))
    d_instagram = diff(today["instagram"], yesterday.get("instagram"))
    d_threads = diff(today["threads"], yesterday.get("threads"))

    def fmt_diff(d):
        if d is None:
            return ""
        return f"(+{d})" if d >= 0 else f"({d})"

    summary_lines = [
        f"[{checked_at}] 종합상황실",
        f"사이트 클릭 합계: {today['site_clicks']} {fmt_diff(d_site_clicks)}",
        f"사이트 색인 합계: {today['site_indexed']} {fmt_diff(d_site_indexed)}",
    ]
    for label, v in today["youtube"].items():
        d = yt_diffs.get(label, {})
        summary_lines.append(f"유튜브 {label}: 구독자 {v['subs']} {fmt_diff(d.get('subs'))} "
                              f"/ 조회수 {v['views']} {fmt_diff(d.get('views'))}")
    summary_lines.append(f"TikTok: {today['tiktok']} {fmt_diff(d_tiktok)}")
    summary_lines.append(f"Facebook: {today['facebook']} {fmt_diff(d_facebook)}")
    summary_lines.append(f"Instagram: {today['instagram']} {fmt_diff(d_instagram)}")
    summary_lines.append(f"Threads: {today['threads']} {fmt_diff(d_threads)}")
    summary_text = "\n".join(summary_lines)
    log(summary_text)

    log("4/4 Gemini 분석 생성 중...")
    analysis = gemini_analysis(summary_text)
    log(analysis)

    sheet_link = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit" if SHEET_ID else ""

    # 시트 전송용 레코드(플랫한 dict)
    record = {"checked_at": checked_at, "site_clicks": today["site_clicks"],
              "site_indexed": today["site_indexed"], "tiktok": today["tiktok"],
              "facebook": today["facebook"], "instagram": today["instagram"],
              "threads": today["threads"], "analysis": analysis}
    for label, v in today["youtube"].items():
        record[f"yt_{label}_subs"] = v["subs"]
        record[f"yt_{label}_views"] = v["views"]
    send_to_sheets(record)
    send_youtube_status_to_sheets(yt_stats, yt_diffs, checked_at)

    send_email(f"[종합상황실] {checked_at[:10]} 현황 리포트",
               summary_text + "\n\n[AI 분석]\n" + analysis +
               (f"\n\n시트: {sheet_link}" if sheet_link else ""))

    kakao_text = (summary_lines[0] + "\n" +
                  f"사이트클릭 {today['site_clicks']}{fmt_diff(d_site_clicks)} / "
                  f"색인 {today['site_indexed']}{fmt_diff(d_site_indexed)}\n" +
                  analysis[:80])
    send_kakao(kakao_text, sheet_link or "https://github.com/huh0303-cmyk/-WP-QWEN-autobot")

    history["latest"] = today
    history["updated_at"] = checked_at
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    log("완료")


if __name__ == "__main__":
    main()
