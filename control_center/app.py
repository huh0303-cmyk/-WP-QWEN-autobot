from flask import Flask, render_template

from flask import Response, flash, jsonify, redirect, request, send_from_directory, url_for

from .keywords import tistory_seed_topics, top_keywords_by_category, weekly_suggestions
from .registry import load_wordpress_sites
from .models import IMAGE_MODELS, TEXT_MODELS

import json
import csv
import io
import os
import re
import subprocess
import html
import hmac
import secrets
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

import requests

REVIEW_QUEUE_CSV = "https://docs.google.com/spreadsheets/d/12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI/gviz/tq?tqx=out:csv&sheet=%EC%9E%90%EB%8F%99%ED%99%94_%EB%B0%9C%ED%96%89%EB%8C%80%EA%B8%B0&range=A1:Q500"
EDITORIAL_REVIEW_CSV = "https://docs.google.com/spreadsheets/d/12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI/gviz/tq?tqx=out:csv&sheet=%EC%98%A4%EB%8A%98_%EA%B8%80%EA%B2%80%EC%88%98&range=A1:I500"
ADSENSE_BLOGGER_URLS = {
    "https://skin.k-health365.com",
    "https://glow.k-health365.com",
}
HIDDEN_BLOGGER_URLS = {
    # Duplicate medical-tour test blog. The production destination is
    # https://koreamedicaltour365.blogspot.com (ID 270775542645307723).
    "https://koreamedicaltour1.blogspot.com",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("CONTROL_CENTER_SECRET_KEY") or secrets.token_hex(32)
app.config["CONTROL_CENTER_CSRF"] = os.environ.get("CONTROL_CENTER_CSRF") or secrets.token_urlsafe(24)


@app.template_filter("compact_category")
def compact_category(value: object, limit: int = 22) -> str:
    """Short dashboard label; the source category remains unchanged."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = {
        "international students": "intl students",
        "international student": "intl student",
        "Korean language programs": "Korean programs",
        "cultural adjustment": "culture tips",
        "government websites": "gov websites",
        "residence registration": "residence ID",
        "accommodation": "housing",
    }.get(text, text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def get_review_queue() -> list[dict[str, str]]:
    """Read reviewable drafts from the central Sheet without requiring a Google login."""
    try:
        response = requests.get(REVIEW_QUEUE_CSV, timeout=12)
        response.raise_for_status()
        rows = list(csv.reader(io.StringIO(response.text)))
    except (requests.RequestException, csv.Error):
        return []
    items = []
    for row in rows[1:]:
        row += [""] * (17 - len(row))
        created_at, job_id, site_id, status, publish_now, title = row[:6]
        review_url = row[9].strip()
        error_code = row[11].strip()
        message = row[12].strip()
        search_description = message.split("meta_description=", 1)[1].strip() if "meta_description=" in message else ""
        if not job_id.strip():
            continue
        # Superseded rows are retained in Sheets as an audit trail, but they
        # are not current work and must not clutter the CEO's recent inbox.
        if status.strip().casefold() in {"superseded", "historical"}:
            continue
        platform = "Tistory" if site_id.lower().startswith("tistory_") else "Blogspot" if "blogger" in job_id.lower() or "blogger" in site_id.lower() else "WordPress"
        failed = status.strip().casefold() == "failed" or bool(error_code)
        if failed:
            items.append({
                "created_at": created_at.replace("T", " ")[:16],
                "job_id": job_id,
                "site_id": site_id,
                "platform": platform,
                "title": message or error_code or "작업 실패",
                "review_url": "",
                "search_description": "",
                "status": f"실패 · {error_code}" if error_code else "실패",
                "retryable": platform == "Blogspot",
                "error": True,
            })
            continue
        if not title.strip():
            continue
        status_label = {
            "ready": "검토 대기열 등록",
            "queued": "실행 대기",
            "processing": "처리 중",
        }.get(status.strip().casefold(), status or "작업대기")
        items.append({
            "created_at": created_at.replace("T", " ")[:16],
            "job_id": job_id,
            "site_id": site_id,
            "platform": platform,
            "title": title,
            "review_url": review_url,
            "search_description": search_description,
            "status": "검토대기" if review_url.startswith("http") and publish_now.strip().upper() != "TRUE" else status_label,
            "retryable": False,
            "error": False,
        })
    # Blogger and WordPress editorial drafts use the compact review sheet.
    # Merge it into the same control-room list so the CEO has one inbox.
    try:
        editorial_response = requests.get(EDITORIAL_REVIEW_CSV, timeout=12)
        editorial_response.raise_for_status()
        editorial_rows = list(csv.reader(io.StringIO(editorial_response.text)))
    except (requests.RequestException, csv.Error):
        editorial_rows = []
    for index, row in enumerate(editorial_rows[1:], start=2):
        row += [""] * (9 - len(row))
        created_at, platform, channel, title, review_url, status, decision, note = row[:8]
        search_description = note.split("검색 설명(붙여넣기용):", 1)[1].strip() if "검색 설명(붙여넣기용):" in note else ""
        if not title.strip() or not review_url.strip().startswith("http"):
            continue
        items.append({
            "created_at": created_at.replace("T", " ")[:16],
            "job_id": f"editorial-{index}-{channel}",
            "site_id": channel,
            "platform": platform or "Blogspot",
            "title": title,
            "review_url": review_url,
            "search_description": search_description,
            "status": decision or status or "검토대기",
        })
    deduped = {item["review_url"] or item["job_id"]: item for item in items}
    return sorted(deduped.values(), key=lambda item: item["created_at"], reverse=True)[:100]


@app.get("/review/tistory/<path:job_id>")
def review_tistory_draft(job_id: str):
    """Render one queued Tistory draft with a usable approval hand-off."""
    try:
        response = requests.get(REVIEW_QUEUE_CSV, timeout=12)
        response.raise_for_status()
        rows = list(csv.reader(io.StringIO(response.text)))
    except (requests.RequestException, csv.Error):
        return Response("검토 대기열을 읽을 수 없습니다.", status=503)
    for row in rows[1:]:
        row += [""] * (17 - len(row))
        if row[1] != job_id or not row[2].startswith("tistory_"):
            continue
        body = row[6]
        body = re.sub(r"(?is)<(?:script|style|iframe|object|embed)[^>]*>.*?</(?:script|style|iframe|object|embed)>", "", body)
        body = re.sub(r"(?i)\s+on\w+\s*=\s*(['\"]).*?\1", "", body)
        body = re.sub(r"(?i)(href|src)\s*=\s*(['\"])\s*javascript:.*?\2", r'\1="#"', body)
        rooms = json.loads((Path(__file__).parents[1] / "config" / "automation_rooms.json").read_text(encoding="utf-8"))
        room = next((item for item in rooms.get("rooms", []) if item.get("room_id") == row[2]), {})
        destination = str(room.get("destination_id") or "https://www.tistory.com/").rstrip("/")
        manager_url = destination + "/manage/newpost/?type=post"
        return render_template(
            "tistory_review.html", job_id=job_id, site_id=row[2], title=row[5],
            body_html=body, category=row[14], description=row[15], visibility=row[16],
            manager_url=manager_url,
        )
    return Response("해당 Tistory 검토본을 찾을 수 없습니다.", status=404)


@app.post("/review/tistory/<path:job_id>/approve")
def approve_tistory_draft(job_id: str):
    """Record CEO approval, then hand off to the correct Tistory editor."""
    site_id = request.form.get("site_id", "").strip()
    manager_url = request.form.get("manager_url", "https://www.tistory.com/").strip()
    if not manager_url.startswith("https://"):
        manager_url = "https://www.tistory.com/"
    try:
        from scripts.gsheets_direct import get_sheets_service
        sheet_id = os.environ.get("SHEET_ID", "12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI").strip()
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="'자동화_발행대기'!A1:Q500"
        ).execute()
        rows = result.get("values", [])
        for index, row in enumerate(rows[1:], start=2):
            if len(row) > 1 and row[1] == job_id:
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=f"'자동화_발행대기'!D{index}:E{index}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [["승인완료", "TRUE"]]},
                ).execute()
                break
        flash(f"{site_id or 'Tistory'} 승인 기록 완료. 티스토리 편집기에서 최종 게시를 눌러주세요.", "success")
    except Exception as exc:
        flash(f"승인 기록 저장 실패: {exc}", "error")
    return redirect(manager_url)


@app.before_request
def require_control_center_login():
    """Protect every PWA route when deployment credentials are configured."""
    if request.path == "/healthz":
        return None
    username = os.environ.get("CONTROL_CENTER_USERNAME", "").strip()
    password = os.environ.get("CONTROL_CENTER_PASSWORD", "")
    if not username or not password:
        return None
    supplied = request.authorization
    if (
        supplied
        and hmac.compare_digest(supplied.username or "", username)
        and hmac.compare_digest(supplied.password or "", password)
    ):
        return None
    return Response(
        "CEO control-room login required",
        401,
        {"WWW-Authenticate": 'Basic realm="Korea365 CEO Control Room"'},
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/manifest.webmanifest")
def pwa_manifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")


@app.get("/service-worker.js")
def pwa_service_worker():
    response = send_from_directory(app.static_folder, "service-worker.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/offline")
def pwa_offline():
    return render_template("offline.html")


@app.context_processor
def inject_control_center_settings():
    return {"csrf_token": app.config["CONTROL_CENTER_CSRF"]}


@app.after_request
def disable_dashboard_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@lru_cache(maxsize=1)
def _github_secret_names() -> set[str]:
    try:
        completed = subprocess.run(
            ["gh", "secret", "list", "--repo", "huh0303-cmyk/-WP-QWEN-autobot"],
            capture_output=True, text=True, timeout=8, check=True,
        )
        return {line.split("\t", 1)[0].strip() for line in completed.stdout.splitlines() if line.strip()}
    except (OSError, subprocess.SubprocessError):
        return set()


@lru_cache(maxsize=128)
def _wp_category_counts(site_url: str, five_minute_bucket: int) -> list[dict[str, object]]:
    """Read the categories actually registered in WordPress, including zero-count ones.

    2026-09-03: had no time bucket, so one transient network hiccup got
    cached as "categories: []" (shown as "카테고리 수집 실패") for the rest
    of the Render dyno's lifetime — sites were actually fine on re-check.
    The bucket keeps page loads fast while retrying every five minutes."""
    del five_minute_bucket
    try:
        response = requests.get(
            f"{site_url.rstrip('/')}/wp-json/wp/v2/categories",
            params={"per_page": 100, "hide_empty": "false", "orderby": "name", "order": "asc"},
            timeout=8,
        )
        response.raise_for_status()
        categories = [
            {
                "name": (
                    str(row.get("slug", "")).replace("-", " ").title()
                    if "�" in html.unescape(str(row.get("name", "")))
                    else html.unescape(str(row.get("name", "")).strip())
                ),
                "count": int(row.get("count", 0)),
            }
            for row in response.json()
            if str(row.get("name", "")).strip()
        ]
        return sorted(categories, key=lambda row: (-int(row["count"]), str(row["name"]).casefold()))
    except (requests.RequestException, ValueError, TypeError):
        return []


@lru_cache(maxsize=128)
def _wp_visitor_stats(site_url: str, five_minute_bucket: int) -> dict[str, object]:
    """Read the public visitor counter deployed on each WordPress site.

    The bucket keeps Render page loads fast while refreshing every five minutes.
    Missing or malformed responses are never replaced with invented numbers.
    """
    del five_minute_bucket
    try:
        response = requests.get(
            f"{site_url.rstrip('/')}/wp-json/site-stats/v1/visitors",
            timeout=8,
            headers={"User-Agent": "Korea365-Control-Room/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        today = int(payload["count"])
        yesterday = int(payload["yesterday_count"])
        total = int(payload["total"])
        return {
            "connected": True,
            "date": payload.get("date"),
            "daily_visitors": today,
            "visitor_delta": today - yesterday,
            "yesterday_visitors": yesterday,
            "total_visitors": total,
            # The all-time counter grows by today's visits since midnight.
            "total_delta": today,
        }
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return {"connected": False}


@lru_cache(maxsize=128)
def _blogger_label_counts(blog_url: str, five_minute_bucket: int) -> list[dict[str, object]]:
    """Count labels used by publicly visible Blogger posts.

    2026-09-03: no time bucket meant one transient failure cached empty
    forever for that Render process's lifetime. See _wp_category_counts."""
    del five_minute_bucket
    try:
        response = requests.get(
            f"{blog_url.rstrip('/')}/feeds/posts/default",
            params={"alt": "json", "max-results": 500},
            timeout=8,
        )
        response.raise_for_status()
        counts: Counter[str] = Counter()
        for entry in response.json().get("feed", {}).get("entry", []) or []:
            for category in entry.get("category", []) or []:
                label = html.unescape(str(category.get("term", "")).strip())
                if label:
                    counts[label] += 1
        return [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))
        ]
    except (requests.RequestException, ValueError, TypeError):
        return []


@lru_cache(maxsize=32)
def _tistory_feed_summary(site_url: str, five_minute_bucket: int) -> dict[str, object]:
    """Read exact public category counts, falling back to the Tistory RSS feed.

    2026-09-03: no time bucket meant one transient failure cached empty
    forever for that Render process's lifetime. See _wp_category_counts."""
    del five_minute_bucket
    try:
        homepage = requests.get(site_url.rstrip("/") + "/", timeout=15)
        homepage.raise_for_status()
        category_matches = re.findall(
            r'<a\s+href="/category/([^"]+)"\s+class="link_(?:item|sub_item)"[^>]*>'
            r'.*?<span\s+class="c_cnt">\((\d+)\)</span>',
            homepage.text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        total_match = re.search(
            r'class="link_tit"[^>]*>.*?<span\s+class="c_cnt">\((\d+)\)</span>',
            homepage.text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if category_matches:
            categories = [
                {
                    "name": html.unescape(unquote(encoded_name)).strip(),
                    "count": int(count),
                }
                for encoded_name, count in category_matches
            ]
            categories.sort(key=lambda row: (-int(row["count"]), str(row["name"]).casefold()))
            return {
                "total_posts": int(total_match.group(1)) if total_match else sum(int(row["count"]) for row in categories),
                "categories": categories,
                "connected": True,
                "source": "public_category_counts",
            }

        response = requests.get(f"{site_url.rstrip('/')}/rss", timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall("./channel/item")
        categories: Counter[str] = Counter()
        for item in items:
            for node in item.findall("category"):
                name = html.unescape((node.text or "").strip())
                # Tistory RSS mixes post categories and free-form tags in the same
                # element. Existing category names are bracketed, so exclude tags
                # from the control-room category inventory.
                if name.startswith("[") and name.endswith("]"):
                    categories[name] += 1
        return {
            "total_posts": len(items),
            "categories": [
                {"name": name, "count": count}
                for name, count in sorted(categories.items(), key=lambda pair: (-pair[1], pair[0].casefold()))
            ][:8],
            "connected": True,
            "source": "rss",
        }
    except (requests.RequestException, ET.ParseError, ValueError):
        return {"total_posts": None, "categories": [], "connected": False, "source": "unavailable"}


def _attach_tistory_category_deltas(feed_results: dict[str, dict[str, object]]) -> None:
    """Attach day-over-day post/category deltas and persist today's five-site snapshot."""
    snapshot_path = Path(__file__).resolve().parents[1] / "data" / "tistory_category_counts_latest.json"
    today = date.today().isoformat()
    stored: dict = {}
    if snapshot_path.exists():
        try:
            stored = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored = {}
    previous = stored.get("previous", {}) if stored.get("date") == today else stored.get("sites", {})
    if not isinstance(previous, dict):
        previous = {}

    current: dict[str, dict[str, object]] = {}
    for site_id, summary in feed_results.items():
        prior = previous.get(site_id, {}) if isinstance(previous.get(site_id, {}), dict) else {}
        prior_categories = prior.get("categories", {}) if isinstance(prior.get("categories", {}), dict) else {}
        total_posts = summary.get("total_posts")
        prior_total = prior.get("total_posts")
        summary["total_delta"] = (
            int(total_posts) - int(prior_total)
            if total_posts is not None and prior_total is not None
            else None
        )
        for category in summary.get("categories", []) or []:
            old_value = prior_categories.get(str(category["name"]))
            category["delta"] = int(category["count"]) - int(old_value) if old_value is not None else None
        if total_posts is not None:
            current[site_id] = {
                "total_posts": int(total_posts),
                "categories": {
                    str(category["name"]): int(category["count"])
                    for category in summary.get("categories", []) or []
                },
            }

    payload = {"date": today, "previous": previous, "sites": current}
    try:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _attach_wp_category_deltas(category_results: dict[str, list[dict[str, object]]]) -> None:
    """Attach day-over-day deltas and retain one prior daily snapshot."""
    snapshot_path = Path(__file__).resolve().parents[1] / "data" / "wp_category_counts_latest.json"
    today = date.today().isoformat()
    stored: dict = {}
    if snapshot_path.exists():
        try:
            stored = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored = {}
    if stored.get("date") == today:
        previous = stored.get("previous", {})
    else:
        previous = stored.get("sites", {})
    for domain, categories in category_results.items():
        prior_counts = previous.get(domain, {}) if isinstance(previous, dict) else {}
        for category in categories:
            old_value = prior_counts.get(str(category["name"]))
            category["delta"] = int(category["count"]) - int(old_value) if old_value is not None else None
    current = {
        domain: {str(category["name"]): int(category["count"]) for category in categories}
        for domain, categories in category_results.items()
    }
    payload = {"date": today, "previous": previous, "sites": current}
    try:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def wordpress_cadence(site) -> dict[str, object]:
    """Return the locked WP27 cadence shown by the control room."""
    is_newsroom = bool(site and site.content_type in {"news_ko", "news_en"})
    if is_newsroom:
        return {
            "daily_min": 3,
            "daily_max": 10,
            "weekly_min": None,
            "weekly_max": None,
            "label": "RSS 하루 3~10회",
            "kind": "newsroom",
        }
    return {
        "daily_min": 1,
        "daily_max": 1,
        "weekly_min": 7,
        "weekly_max": 7,
        "label": "하루 1포스팅 · 주 7포스팅",
        "kind": "blog",
    }


def get_site_data():
    raw_sites = [
        {"domain": "k-health365.com", "today": 196, "total": 12450, "diff": -6, "persona": "건강정보 편집국", "tone": "근거 중심의 신중하고 이해하기 쉬운 설명체"},
        {"domain": "koreainvest365.com", "today": 399, "total": 28900, "diff": 324, "persona": "Korean markets analyst", "tone": "Data-led, balanced and risk-aware"},
        {"domain": "korea365.org", "today": 279, "total": 18300, "diff": 57, "persona": "Korea culture service journalist", "tone": "Practical, locally grounded and concise"},
        {"domain": "kfinance365.com", "today": 257, "total": 15400, "diff": 108, "persona": "", "tone": ""},
        {"domain": "jobkorea365.com", "today": 236, "total": 14200, "diff": 66, "persona": "", "tone": ""},
        {"domain": "k-trip365.com", "today": 226, "total": 13800, "diff": 32, "persona": "", "tone": ""},
        {"domain": "kskin365.com", "today": 210, "total": 11200, "diff": -12, "persona": "", "tone": ""},
        {"domain": "koreainsurance365.com", "today": 198, "total": 9800, "diff": 15, "persona": "", "tone": ""},
        {"domain": "koreataxnlaw.com", "today": 185, "total": 8900, "diff": -3, "persona": "", "tone": ""},
        {"domain": "kworld365.com", "today": 172, "total": 8100, "diff": 40, "persona": "", "tone": ""},
        {"domain": "koreawedding365.com", "today": 160, "total": 7500, "diff": 8, "persona": "", "tone": ""},
        {"domain": "ktech365.com", "today": 155, "total": 7100, "diff": -15, "persona": "", "tone": ""},
        {"domain": "kieca-korea.org", "today": 140, "total": 6400, "diff": 22, "persona": "", "tone": ""},
        {"domain": "ksa-korea.org", "today": 132, "total": 5900, "diff": 5, "persona": "", "tone": ""},
        {"domain": "ki-korea.com", "today": 125, "total": 5300, "diff": -2, "persona": "", "tone": ""},
        {"domain": "koreanews365.com", "today": 118, "total": 4800, "diff": 11, "persona": "", "tone": ""},
        {"domain": "koreacrypto365.com", "today": 110, "total": 4200, "diff": 18, "persona": "", "tone": ""},
        {"domain": "koreamedicaltour.com", "today": 105, "total": 3900, "diff": -8, "persona": "", "tone": ""},
        {"domain": "krealestate365.com", "today": 98, "total": 3500, "diff": 4, "persona": "", "tone": ""},
        {"domain": "kstudy365.com", "today": 92, "total": 3100, "diff": 7, "persona": "", "tone": ""},
        {"domain": "k-visa365.com", "today": 88, "total": 2800, "diff": -1, "persona": "", "tone": ""},
        {"domain": "jobinkorea365.com", "today": 82, "total": 2400, "diff": 10, "persona": "", "tone": ""},
        {"domain": "jobkoreaglobal.com", "today": 75, "total": 2100, "diff": 3, "persona": "", "tone": ""},
        {"domain": "oliveyoungkorea.com", "today": 70, "total": 1900, "diff": -4, "persona": "", "tone": ""},
        {"domain": "sis-korea.com", "today": 65, "total": 1600, "diff": 2, "persona": "", "tone": ""},
        {"domain": "studyinkorea365.com", "today": 60, "total": 1300, "diff": 1, "persona": "", "tone": ""},
        {"domain": "theseouljournal.com", "today": 55, "total": 1000, "diff": 0, "persona": "", "tone": ""}
    ]
    root = Path(__file__).resolve().parents[1]
    traffic_by_domain = {}
    traffic_path = root / "daily_site_traffic_result.json"
    if traffic_path.exists():
        try:
            traffic_by_domain = {
                row["domain"]: row
                for row in json.loads(traffic_path.read_text(encoding="utf-8")).get("records", [])
            }
        except (OSError, ValueError, KeyError):
            traffic_by_domain = {}
    history_sites = {}
    history_path = root / "situation_room_history.json"
    if history_path.exists():
        try:
            history_sites = json.loads(history_path.read_text(encoding="utf-8")).get("latest", {}).get("site_details", {})
        except (OSError, ValueError):
            history_sites = {}
    index_audit_sites = {}
    index_audit_path = root / "index_audit_manifest.json"
    if index_audit_path.exists():
        try:
            index_audit_sites = json.loads(index_audit_path.read_text(encoding="utf-8")).get("sites", {})
        except (OSError, ValueError):
            index_audit_sites = {}
    registry_by_domain = {
        site.url.replace("https://", "").replace("http://", "").rstrip("/"): site
        for site in load_wordpress_sites()
    }
    # Categories and visitor counters are independent public APIs. Fetch them
    # together so one slow site cannot serialize the entire 27-site dashboard.
    bucket = int(time.time() // 300)
    with ThreadPoolExecutor(max_workers=32) as executor:
        category_futures = {
            domain: executor.submit(_wp_category_counts, site.url, bucket)
            for domain, site in registry_by_domain.items()
        }
        visitor_futures = {
            domain: executor.submit(_wp_visitor_stats, site.url, bucket)
            for domain, site in registry_by_domain.items()
        }
        category_results = {domain: future.result() for domain, future in category_futures.items()}
        visitor_results = {domain: future.result() for domain, future in visitor_futures.items()}
    _attach_wp_category_deltas(category_results)
    secret_names = _github_secret_names()
    sites = []
    for item in raw_sites:
        registered = registry_by_domain.get(item["domain"])
        live_traffic = visitor_results.get(item["domain"], {})
        stored_traffic = traffic_by_domain.get(item["domain"], {})
        traffic = live_traffic if live_traffic.get("connected") else stored_traffic
        detail = history_sites.get(item["domain"], {})
        today_visitors = traffic.get("daily_visitors")
        visitor_delta = traffic.get("visitor_delta")
        total_visitors = traffic.get("total_visitors")
        total_posts = traffic.get("total_posts")
        if total_posts is None:
            total_posts = detail.get("total_posts")
        previous_posts = detail.get("total_posts")
        posts_delta = (
            total_posts - previous_posts
            if total_posts is not None and previous_posts is not None
            else None
        )
        audit_entry = (
            index_audit_sites.get(f"https://{item['domain']}")
            or index_audit_sites.get(f"https://{item['domain']}/")
            or index_audit_sites.get(item["domain"])
            or {}
        )
        audit_summary = audit_entry.get("summary") or {}
        indexed = audit_summary.get("indexed")
        indexed_delta = audit_summary.get("indexed_delta")
        index_unknown = audit_summary.get("unknown")
        index_checked_at = audit_entry.get("audited_at") or ""
        if indexed is not None:
            index_status = (
                f"Google URL별 확인 · 미확인 {index_unknown}개"
                if index_unknown else "Google URL별 전수 확인"
            )
        elif audit_entry.get("error") == "gsc_property_not_accessible":
            index_status = "Search Console 권한 연결 필요"
        else:
            index_status = "정밀 집계 중"
        sites.append({
            "site_id": registered.site_id if registered else item["domain"],
            "domain": item["domain"],
            "admin_review_url": f"https://{item['domain']}/wp-admin/edit.php?post_status=draft&post_type=post",
            "today_visitors": today_visitors,
            "today_delta": visitor_delta,
            "total_visitors": total_visitors,
            "total_delta": traffic.get("total_delta"),
            "total_posts": total_posts,
            "posts_delta": posts_delta,
            "indexed": indexed,
            "indexed_delta": indexed_delta,
            "index_unknown": index_unknown,
            "index_checked_at": index_checked_at,
            "index_status": index_status,
            "visitor_connected": bool(live_traffic.get("connected")),
            "visitor_checked_at": live_traffic.get("date") or stored_traffic.get("checked_at") or "",
            "category": registered.theme if registered else "미분류",
            "cadence": wordpress_cadence(registered),
            "official_categories": category_results.get(item["domain"], []),
            "auth_ready": bool(registered and (
                os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip() or
                registered.secret_name in secret_names or os.environ.get(registered.secret_name, "").strip()
            )),
            "google_approved": item["domain"] == "k-health365.com",
            "persona": registered.persona if registered else item["persona"],
            "tone": registered.tone if registered else item["tone"],
            "default_text_model": "gpt-5-mini",
            "default_image_model": "bytedance/sdxl-lightning-4step",
        })
    return sorted(sites, key=lambda site: (
        site["today_visitors"] is None,
        -(site["today_visitors"] or 0),
        -(site["total_visitors"] or 0),
        site["domain"],
    ))


def _site_rows(_sites=None):
    """Compatibility hook used by tests and the richer control-center shell."""
    return get_site_data(), None


def get_blogger_data():
    path = Path(__file__).resolve().parents[1] / "config" / "blogger_portfolio.json"
    rows = [
        row for row in json.loads(path.read_text(encoding="utf-8")).get("channels", [])
        if row.get("blogspot", "").rstrip("/") not in HIDDEN_BLOGGER_URLS
    ]
    stats_path = Path(__file__).resolve().parents[1] / "data" / "blogger_traffic_latest.json"
    stats = {}
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8")).get("sites", {})
        except (OSError, ValueError):
            stats = {}
    history_bloggers = {}
    history_path = Path(__file__).resolve().parents[1] / "situation_room_history.json"
    if history_path.exists():
        try:
            history_bloggers = json.loads(history_path.read_text(encoding="utf-8")).get("latest", {}).get("blogger_details", {})
        except (OSError, ValueError):
            history_bloggers = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        blogger_labels = dict(executor.map(
            lambda row: (row.get("blogspot", ""), _blogger_label_counts(row.get("blogspot", ""), int(time.time() // 300))),
            rows,
        ))
    wp_registry = {
        site.url.rstrip("/"): site for site in load_wordpress_sites()
    }
    profiles_path = Path(__file__).resolve().parents[1] / "config" / "content_engine_profiles.json"
    profile_by_order = {}
    if profiles_path.exists():
        try:
            profile_by_order = {
                int(profile["order"]): profile["site_key"]
                for profile in json.loads(profiles_path.read_text(encoding="utf-8")).get("profiles", [])
            }
        except (OSError, ValueError, KeyError, TypeError):
            profile_by_order = {}
    result = [{
        "site_id": f"blogger_{profile_by_order.get(int(row.get('order') or 0), '')}",
        "order": row.get("order"),
        "name": row.get("title") or row.get("name") or f"Blogger {row.get('order', '')}",
        "wp_url": row.get("wp") or row.get("wordpress") or row.get("wp_url", ""),
        "url": row.get("blogspot", ""),
        "google_approved": row.get("blogspot", "").rstrip("/") in ADSENSE_BLOGGER_URLS,
        "status": row.get("status", "UNKNOWN"),
        "connected": bool(row.get("destination_id") and row.get("status") in {"EXISTING", "CREATED", "SCHEDULED"}),
        "blog_id": row.get("destination_id", ""),
        "admin_review_url": f"https://www.blogger.com/blog/posts/{row.get('destination_id', '')}" if row.get("destination_id") else "https://www.blogger.com/",
        "category": row.get("topic") or "미분류",
        "official_categories": blogger_labels.get(row.get("blogspot", ""), []),
        "persona": getattr(wp_registry.get((row.get("wp") or "").rstrip("/")), "persona", "Specialist editorial desk"),
        "tone": getattr(wp_registry.get((row.get("wp") or "").rstrip("/")), "tone", "Clear, practical and source-aware"),
        "default_text_model": "gpt-5-mini",
        "default_image_model": "bytedance/sdxl-lightning-4step",
        "today_visitors": (stats.get(row.get("blogspot", ""), {}) or {}).get("today"),
        "today_delta": (stats.get(row.get("blogspot", ""), {}) or {}).get("today_delta"),
        "total_visitors": (stats.get(row.get("blogspot", ""), {}) or {}).get("total"),
        "total_delta": (stats.get(row.get("blogspot", ""), {}) or {}).get("total_delta"),
        "total_posts": (history_bloggers.get(row.get("blogspot", "").replace("https://", ""), {}) or {}).get("public_posts"),
        "posts_delta": None,
        "indexed": (history_bloggers.get(row.get("blogspot", "").replace("https://", ""), {}) or {}).get("indexed"),
        "indexed_delta": None,
    } for row in rows]
    return sorted(
        result,
        key=lambda item: (
            item["today_visitors"] is None,
            -(item["today_visitors"] or 0),
            -(item["total_visitors"] or 0),
            item["order"] or 999,
        ),
    )


def get_tistory_data() -> list[dict[str, object]]:
    """Build five Tistory control-room cards without inferring unavailable traffic data."""
    path = Path(__file__).resolve().parents[1] / "config" / "tistory_portfolio.json"
    rows = json.loads(path.read_text(encoding="utf-8")).get("sites", [])
    latest_by_site: dict[str, dict[str, object]] = {}
    latest_path = Path(__file__).resolve().parents[1] / "output" / "tistory_5_drafts_2026-09-01.json"
    if latest_path.exists():
        try:
            latest_by_site = {
                str(draft.get("site_id", "")): draft
                for draft in json.loads(latest_path.read_text(encoding="utf-8")).get("drafts", [])
            }
        except (OSError, ValueError, TypeError):
            latest_by_site = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        feed_results = dict(executor.map(
            lambda row: (row.get("site_id", ""), _tistory_feed_summary(row.get("url", ""), int(time.time() // 300))),
            rows,
        ))
    _attach_tistory_category_deltas(feed_results)
    personas = {
        "tistory_insurance_lab": ("보험·의료비 소비자보호 편집자", "약관·공식자료 우선, 치과비용까지 과장 없이 실제 확인 순서 중심"),
        "tistory_finance_housing": ("주거금융 실무 편집자", "규제 변동을 명시하고 계약 전 확인사항을 구체적으로 설명"),
        "tistory_health_info": ("근거중심 건강정보 편집자", "진단을 단정하지 않고 검진·증상·생활습관을 공식 의료정보로 설명"),
        "tistory_life365": ("생활행정 정보 큐레이터", "신청기한·대상·공식 조회 경로를 빠르고 명료하게 안내"),
        "tistory_ktrip365": ("한국여행 실무 편집자", "한국어 검색 의도에 맞춰 교통·예약·숙소·비용을 구체적으로 안내"),
    }
    result = []
    for row in rows:
        summary = feed_results.get(row.get("site_id", ""), {})
        latest = latest_by_site.get(row.get("site_id", ""), {})
        persona, tone = personas.get(row.get("site_id", ""), ("전문 편집자", "공식 출처 중심의 실용적 설명"))
        result.append({
            "site_id": row.get("site_id", ""),
            "order": row.get("launch_order"),
            "name": row.get("title", ""),
            "url": row.get("url", ""),
            "admin_review_url": f"{row.get('url', '').rstrip('/')}/manage/posts",
            "status": "READY" if row.get("launch_enabled") else "PAUSED",
            "category": " · ".join(row.get("categories", [])),
            "official_categories": summary.get("categories", []),
            "persona": persona,
            "tone": tone,
            "default_text_model": "gpt-5-mini",
            "default_image_model": "bytedance/sdxl-lightning-4step",
            "today_visitors": None,
            "today_delta": None,
            "total_visitors": None,
            "total_delta": None,
            "total_posts": summary.get("total_posts"),
            "posts_delta": summary.get("total_delta"),
            "indexed": None,
            "indexed_delta": None,
            "feed_connected": bool(summary.get("connected")),
            "publish_policy": row.get("publish_policy", "awaiting_approval"),
            "reference_wp": row.get("reference_wp", ""),
            "latest_draft_title": latest.get("title"),
            "latest_draft_score": latest.get("quality_score"),
            "latest_draft_status": latest.get("status"),
        })
    return sorted(result, key=lambda item: item["order"] or 999)


def get_youtube_data() -> list[dict[str, object]]:
    """Expose the ten locked YouTube rooms without bypassing Sheet scheduling."""
    root = Path(__file__).resolve().parents[1]
    path = root / "config" / "automation_rooms.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        channel_payload = json.loads((root / "config" / "youtube_channels.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    registry_channel_by_id = {
        str(channel.get("channel_id", "")).strip(): channel
        for channel in channel_payload.get("channels", [])
        if str(channel.get("channel_id", "")).strip()
    }
    rows = []
    for room in payload.get("rooms", []):
        if room.get("platform") != "youtube":
            continue
        channel_id = str(room.get("destination_id", "")).strip()
        registry_channel = registry_channel_by_id.get(channel_id, {})
        channel_key = str(registry_channel.get("channel_key", "")).strip()
        enabled = bool(room.get("enabled", False))
        status = str(room.get("status", "UNKNOWN"))
        workflow = str(room.get("workflow", ""))
        registry_workflow = str(registry_channel.get("workflow", ""))
        rows.append({
            "room_id": str(room.get("room_id", "")),
            "channel_key": channel_key,
            "name": str(room.get("name", "")),
            "group": str(room.get("group", "")),
            "channel_id": channel_id,
            "channel_url": f"https://www.youtube.com/channel/{channel_id}" if channel_id else "",
            "admin_review_url": "https://studio.youtube.com/channel/" + channel_id + "/videos/upload?filter=%5B%7B%22name%22%3A%22VISIBILITY%22%2C%22value%22%3A%5B%22PRIVATE%22%5D%7D%5D" if channel_id else "https://studio.youtube.com/",
            "workflow": workflow,
            "publish_policy": str(room.get("publish_policy", "private")),
            "status": status,
            "enabled": enabled,
            "action_ready": bool(
                channel_key and channel_id and workflow and enabled and status == "READY"
                and registry_channel.get("enabled", False) and registry_workflow == workflow
            ),
            "sheet_controlled": True,
        })
    return sorted(rows, key=lambda row: (row["group"] != "PLAYLIST", row["name"].casefold()))


def get_sns_data() -> list[dict[str, object]]:
    """Return the four CEO metrics for every configured SNS account."""
    history_path = Path(__file__).resolve().parents[1] / "situation_room_history.json"
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = {}
    latest, previous = history.get("latest", {}), history.get("previous", {})
    handles = {
        "tiktok": {"TOPIK": "sis_topik"},
        "instagram": {"TOPIK": "sis__topik", "ENGLISH": "sis_english1", "LANGUAGE": "sis_language"},
        "threads": {"TOPIK": "sis__topik", "ENGLISH": "sis_english1", "LANGUAGE": "sis_language"},
        "facebook": {"TOPIK": "61588777439380", "ENGLISH": "61592457107609", "LANGUAGE": "61593057083167"},
    }
    labels = {"tiktok": "TikTok", "instagram": "Instagram", "threads": "Threads", "facebook": "Facebook 페이지"}
    metric_keys = (("followers", "count"), ("likes", "likes"), ("content", "content_count"), ("watch_time", "watch_time"))
    rows = []
    for platform in ("tiktok", "instagram", "facebook", "threads"):
        current_platform = latest.get(platform, {}) if isinstance(latest.get(platform, {}), dict) else {}
        previous_platform = previous.get(platform, {}) if isinstance(previous.get(platform, {}), dict) else {}
        for brand in ("TOPIK", "ENGLISH", "LANGUAGE"):
            current = current_platform.get(brand, {}) if isinstance(current_platform.get(brand, {}), dict) else {}
            old = previous_platform.get(brand, {}) if isinstance(previous_platform.get(brand, {}), dict) else {}
            metrics = {}
            for display_key, source_key in metric_keys:
                value, old_value = current.get(source_key), old.get(source_key)
                metrics[display_key] = value
                metrics[display_key + "_delta"] = value - old_value if isinstance(value, (int, float)) and isinstance(old_value, (int, float)) else None
            handle = handles.get(platform, {}).get(brand, "")
            if platform == "tiktok": url = f"https://www.tiktok.com/@{handle}" if handle else ""
            elif platform == "instagram": url = f"https://www.instagram.com/{handle}/" if handle else ""
            elif platform == "threads": url = f"https://www.threads.net/@{handle}" if handle else ""
            else: url = f"https://www.facebook.com/{handle}" if handle else ""
            rows.append({
                "platform": labels[platform],
                "platform_key": platform,
                "brand": brand,
                "handle": handle,
                "url": url,
                "error": current.get("error"),
                # There is no enabled, account-selectable SNS publishing workflow.
                # Keep this explicit so the dashboard cannot present a fake action.
                "publish_connected": False,
                "publish_unavailable_reason": "이 계정에 연결된 콘텐츠 발행 실행이 없습니다.",
                **metrics,
            })
    return rows


@lru_cache(maxsize=1)
def _automatic_blogger_targets() -> dict[str, str]:
    """Return the exact enabled Blogspot site-id/domain pairs accepted by the one-click UI."""
    path = Path(__file__).resolve().parents[1] / "config" / "content_engine_profiles.json"
    try:
        profiles = json.loads(path.read_text(encoding="utf-8")).get("profiles", [])
    except (OSError, json.JSONDecodeError):
        return {}
    targets = {}
    for profile in profiles:
        blogspot = profile.get("blogspot", {})
        url = str(blogspot.get("url", "")).rstrip("/")
        if not blogspot.get("ready_for_automation") or url in HIDDEN_BLOGGER_URLS:
            continue
        site_key = str(profile.get("site_key", "")).strip()
        domain = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
        if site_key and domain:
            targets[f"blogger_{site_key}"] = domain
    return targets


def _queue_draft_trigger(payload: dict[str, object]) -> str:
    """Persist a draft-only request for the worker; never publish from the UI."""
    trigger_id = f"draft-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    payload.update({
        "trigger_id": trigger_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
        "publish_mode": "draft_only",
    })
    queue_path = Path(__file__).resolve().parents[1] / "data" / "control_center_trigger_queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return trigger_id


def _dispatch_draft_workflow(payload: dict[str, object]) -> str:
    """Dispatch the selected site's real generation and publication workflow."""
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-wp-qwen-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    automatic_blogger_topic = payload.get("platform") == "blogger" and payload.get("selection_mode") == "auto"
    if automatic_blogger_topic:
        site_key = str(payload["site_id"]).removeprefix("blogger_")
        profiles_path = Path(__file__).resolve().parents[1] / "config" / "content_engine_profiles.json"
        try:
            profiles = json.loads(profiles_path.read_text(encoding="utf-8")).get("profiles", [])
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Blogger profile registry is unavailable") from exc
        profile = next((item for item in profiles if item.get("site_key") == site_key), None)
        if not profile:
            raise RuntimeError(f"No Blogger profile for {payload['site_id']}")
        blogspot = profile.get("blogspot", {})
        workflow_name = "blogger-rewrite.yml"
        inputs = {
            "source_wp_url": "",
            "blogger_site_id": str(payload["site_id"]),
            "language": str(profile.get("language") or "en"),
            "persona": str(blogspot.get("persona") or "helpful specialist editor"),
            "tone": str(blogspot.get("tone") or "practical and clear"),
            "target_chars": str(blogspot.get("target_chars") or 1800),
            "publish_now": "true",
            # 2026-09-04 CEO: "키워드보고발행" — a chip picked from the paired
            # WP site's own category pool; blank keeps "바이럴자동발행"
            # (the workflow's own live cross-media research).
            "force_keyword": str(payload.get("keyword") or ""),
        }
    else:
        workflow_name = "sheet-triggered-auto-write.yml"
        inputs = {
            "site_id": str(payload["site_id"]),
            "keyword": str(payload["keyword"]),
            "source_wp_url": str(payload.get("source_wp_url") or ""),
            "text_model": str(payload["text_model"]),
            "image_model": str(payload["image_model"]),
        }
    if token:
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_name}/dispatches",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"ref": "main", "inputs": inputs},
            timeout=30,
        )
        if response.status_code != 204:
            raise RuntimeError(f"GitHub API dispatch failed ({response.status_code})")
        return f"https://github.com/{repo}/actions/workflows/{workflow_name}"
    command = [
        "gh", "workflow", "run", workflow_name,
        "--repo", repo,
        *[part for key, value in inputs.items() for part in ("-f", f"{key}={value}")],
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "GitHub workflow dispatch failed").strip())
    return f"https://github.com/{repo}/actions/workflows/{workflow_name}"


@app.post("/trigger/draft")
def trigger_draft():
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index"))

    platform = request.form.get("platform", "").strip().lower()
    domain = request.form.get("domain", "").strip()
    keyword = request.form.get("keyword", "").strip()
    text_model = request.form.get("text_model", "").strip()
    image_model = request.form.get("image_model", "").strip()
    source_wp_url = request.form.get("source_wp_url", "").strip()
    selection_mode = request.form.get("selection_mode", "manual").strip().lower()
    automatic_blogger_topic = platform == "blogger" and selection_mode == "auto"
    anchor = "blogspot" if platform == "blogger" else "wordpress"

    if platform not in {"wordpress", "blogger"} or not domain:
        flash("사이트 정보가 올바르지 않습니다.", "error")
    elif not automatic_blogger_topic and len(keyword) < 2:
        flash(f"{domain}: 핵심 키워드를 2자 이상 입력하세요.", "error")
    elif text_model not in TEXT_MODELS or image_model not in IMAGE_MODELS:
        flash(f"{domain}: 지원하지 않는 엔진입니다.", "error")
    elif platform == "blogger" and not automatic_blogger_topic and not source_wp_url.startswith("https://"):
        flash(f"{domain}: 검증된 WP 공개 글 URL을 먼저 입력하세요.", "error")
    else:
        payload = {
            "platform": platform,
            "site_id": request.form.get("site_id", "").strip(),
            "domain": domain,
            "keyword": keyword,
            "text_model": text_model,
            "image_model": image_model,
            "source_wp_url": source_wp_url or None,
            "selection_mode": "auto" if automatic_blogger_topic else "manual",
        }
        if not payload["site_id"].startswith(("wp_", "blogger_")):
            flash(f"{domain}: 실행용 사이트 ID 연결이 완료되지 않았습니다.", "error")
            return redirect(url_for("index") + f"#{anchor}")
        if automatic_blogger_topic and _automatic_blogger_targets().get(str(payload["site_id"])) != domain.rstrip("/"):
            flash(f"{domain}: 자동 주제 실행이 연결된 Blogspot 사이트가 아닙니다.", "error")
            return redirect(url_for("index") + "#blogspot")
        trigger_id = _queue_draft_trigger(payload)
        try:
            workflow_url = _dispatch_draft_workflow(payload)
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            flash(f"{domain}: 로컬 대기열에는 저장했지만 GitHub 실행 요청 실패 · {exc}", "error")
        else:
            if automatic_blogger_topic:
                picked = f' — "{keyword}"' if keyword else ""
                flash(f"{domain}: 당일 주요 매체에서 최고 주제를 골라 실제 발행하는 작업을 접수했습니다{picked}. 실패하면 해당 사이트 카드에서 다시 실행하세요. · {trigger_id} · {workflow_url}", "success")
            else:
                flash(f"{domain}: 실제 비공개 초안 작업 시작 · {trigger_id} · {workflow_url}", "success")
    return redirect(url_for("index") + f"#{anchor}")


@app.post("/trigger/tistory-plan")
def trigger_tistory_plan():
    """Start one fresh live-topic Tistory job for the selected site.

    Tistory has no supported unattended cloud write API. The hosted control
    room creates the finished article; a logged-in local registrar owns the
    final editor save so the UI never claims a cloud publication that did not
    happen.
    """
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#tistory")
    site_id = request.form.get("site_id", "").strip()
    keyword = request.form.get("keyword", "").strip()
    # A fresh key prevents a second click on the same day from overwriting or
    # reusing the first job. Every click therefore performs a new discovery run.
    run_key = f"manual-{site_id or 'all'}-{int(time.time())}-{secrets.token_hex(3)}"
    allowed_site_ids = {str(site["site_id"]) for site in get_tistory_data()}
    if site_id and site_id not in allowed_site_ids:
        flash("등록되지 않은 Tistory 사이트입니다.", "error")
        return redirect(url_for("index") + "#tistory")
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-wp-qwen-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    dispatch_inputs = {"site_ids": site_id, "run_key": run_key}
    if keyword:
        dispatch_inputs["force_topic"] = keyword
    try:
        if token:
            response = requests.post(
                f"https://api.github.com/repos/{repo}/actions/workflows/tistory-daily-plan.yml/dispatches",
                headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
                json={"ref": "main", "inputs": dispatch_inputs}, timeout=30,
            )
            if response.status_code != 204:
                raise RuntimeError(f"GitHub API dispatch failed ({response.status_code})")
            completed = None
        else:
            command = ["gh", "workflow", "run", "tistory-daily-plan.yml", "--repo", repo]
            for key, value in dispatch_inputs.items():
                if value:
                    command.extend(["-f", f"{key}={value}"])
            completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError, requests.RequestException, RuntimeError) as exc:
        flash(f"Tistory 5개 검토본 실행 요청 실패 · {exc}", "error")
    else:
        if completed is None or completed.returncode == 0:
            target = site_id or "5개 전체"
            picked = f' — "{keyword}"' if keyword else ""
            flash(f"Tistory {target}: 오늘의 바이럴 신호 재조사와 새 글 생성을 시작했습니다{picked}. Tistory 공개 저장은 로그인된 로컬 등록기가 이어서 처리합니다.", "success")
        else:
            detail = (completed.stderr or completed.stdout or "GitHub workflow dispatch failed").strip()
            flash(f"Tistory 5개 검토본 실행 요청 실패 · {detail}", "error")
    return redirect(url_for("index") + "#tistory")


@app.post("/trigger/youtube-batch")
def trigger_youtube_batch():
    """Ask the central scheduler for at most one private upload per channel."""
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#youtube")
    channel_key = request.form.get("channel_key", "").strip()
    allowed_channel_keys = {
        str(channel["channel_key"])
        for channel in get_youtube_data()
        if channel.get("action_ready")
    }
    if not channel_key or channel_key not in allowed_channel_keys:
        flash("콘텐츠 실행이 연결된 YouTube 채널이 아닙니다.", "error")
        return redirect(url_for("index") + "#youtube")
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    if not token:
        flash("YouTube 중앙 스케줄러 실행용 GitHub 연결이 필요합니다.", "error")
        return redirect(url_for("index") + "#youtube")
    try:
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/youtube-control-scheduler.yml/dispatches",
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
            json={"ref": "main", "inputs": {"dry_run": "false", "max_dispatch": "1", "channel_key": channel_key, "run_now": "true"}},
            timeout=30,
        )
        if response.status_code != 204:
            raise RuntimeError(f"GitHub API dispatch failed ({response.status_code})")
    except (requests.RequestException, RuntimeError) as exc:
        flash(f"YouTube 10채널 실행 요청 실패 · {exc}", "error")
    else:
        target = channel_key or "전체 채널"
        flash(f"YouTube {target} 영상 제작을 시작했습니다. 다음 준비 항목 1개를 만들어 비공개로 업로드합니다.", "success")
    return redirect(url_for("index") + "#youtube")


@app.post("/trigger/publish-now")
def trigger_publish_now():
    """CEO clicked '지금 발행' on one already-reviewed WordPress post.

    This is the only place in the control room that ever flips a post
    public; it always targets exactly one post_id chosen by a human.
    """
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#wordpress")
    domain = request.form.get("domain", "").strip()
    review_url = request.form.get("review_url", "").strip()
    match = re.search(r"[?&]post=(\d+)", review_url)
    registered = next(
        (site for site in load_wordpress_sites() if site.url.replace("https://", "").replace("http://", "").rstrip("/") == domain),
        None,
    )
    if not registered or not match:
        flash(f"{domain}: 발행 대상을 확인할 수 없습니다 (사이트 등록 또는 글 번호 누락).", "error")
        return redirect(url_for("index") + "#wordpress")
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    if not token:
        flash("발행 실행용 GitHub 연결이 필요합니다.", "error")
        return redirect(url_for("index") + "#wordpress")
    try:
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/publish-now.yml/dispatches",
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
            json={"ref": "main", "inputs": {
                "domain": registered.url, "post_id": match.group(1), "secret_name": registered.secret_name,
            }},
            timeout=30,
        )
        if response.status_code != 204:
            raise RuntimeError(f"GitHub API dispatch failed ({response.status_code})")
    except (requests.RequestException, RuntimeError) as exc:
        flash(f"{domain}: 발행 요청 실패 · {exc}", "error")
    else:
        flash(f"{domain}: 글 #{match.group(1)} 발행을 시작했습니다.", "success")
    return redirect(url_for("index") + "#wordpress")


@app.post("/trigger/publish-site-now")
def trigger_publish_site_now():
    """CEO clicked '이 사이트만 지금 바로 1건 발행(공개)' on one WP card.

    Writes a brand-new article from that site's own keyword pool and
    publishes it publicly immediately — no keyword input, no review
    step. This is the same direct-publish path a-group-sequential-publish.yml
    already uses per site (daily-network-publish.yml with
    publication_approved=true); this just lets the CEO fire it for one
    chosen site on demand instead of waiting for the batch chain to
    reach it. The scheduled batch sequence is unaffected.
    """
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#wordpress")
    domain = request.form.get("domain", "").strip()
    keyword = request.form.get("keyword", "").strip()
    registered = next(
        (site for site in load_wordpress_sites() if site.url.replace("https://", "").replace("http://", "").rstrip("/") == domain),
        None,
    )
    if not registered:
        flash(f"{domain}: 등록되지 않은 사이트입니다.", "error")
        return redirect(url_for("index") + "#wordpress")
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    if not token:
        flash("발행 실행용 GitHub 연결이 필요합니다.", "error")
        return redirect(url_for("index") + "#wordpress")
    if registered.url.rstrip("/") == "https://koreanews365.com":
        workflow_name = "newsrooms-daily-publisher.yml"
        workflow_inputs = {"newsroom": "koreanews365", "preferred_category": ""}
        success_message = "koreanews365.com: 실시간 주요 뉴스 이슈를 다시 수집해 바이럴 발행을 시작했습니다."
    else:
        workflow_name = "daily-network-publish.yml"
        workflow_inputs = {
            "target_site_url": registered.url,
            "publication_approved": "true",
            "room_id": f"manual-onebutton-{registered.site_id}",
        }
        # 2026-09-04 CEO: "키워드보고발행" — pick one of the 3-per-category
        # chips (see /api/keyword-suggestions-by-category) so the CEO sees
        # the topic before committing; force_keyword overrides the
        # workflow's own live cross-media research for this one run. Blank
        # keyword keeps the original "바이럴자동발행" behavior.
        if keyword:
            workflow_inputs["force_keyword"] = keyword
        picked = f' — "{keyword}"' if keyword else ""
        success_message = f"{domain}: 오늘의 주요매체 언급량과 검색 추세를 다시 조사해 바이럴 글 1건 공개 발행을 시작했습니다{picked}."
    try:
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_name}/dispatches",
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
            json={"ref": "main", "inputs": workflow_inputs},
            timeout=30,
        )
        if response.status_code != 204:
            raise RuntimeError(f"GitHub API dispatch failed ({response.status_code})")
    except (requests.RequestException, RuntimeError) as exc:
        flash(f"{domain}: 발행 요청 실패 · {exc}", "error")
    else:
        flash(success_message, "success")
    return redirect(url_for("index") + "#wordpress")


def build_problem_summary(sites, bloggers, tistory_sites, youtube_channels, sns_accounts) -> dict:
    """One-glance rollup of what needs attention, computed from the same
    per-platform data already shown further down the page. CEO explicitly
    asked (2026-09-03) for problems to surface before having to scan every
    card one by one."""
    wp_issues = []
    for site in sites:
        reasons = []
        # A visitor endpoint timeout is transient infrastructure state. It is
        # retried automatically and is not an action the operator can fix.
        if not site.get("official_categories"):
            reasons.append("카테고리 수집 실패")
        if site.get("indexed") is None and "권한" in (site.get("index_status") or ""):
            reasons.append("GSC 권한 연결 필요")
        if not site.get("auth_ready"):
            reasons.append("WP 인증 미연결")
        if reasons:
            wp_issues.append({"domain": site["domain"], "reasons": reasons})

    blogger_issues = [b.get("name", "") for b in bloggers if not b.get("connected")]
    tistory_issues = [t.get("name", "") for t in tistory_sites if not t.get("feed_connected")]
    youtube_issues = [y.get("name", "") for y in youtube_channels if y.get("enabled") and not y.get("channel_id")]
    sns_issues = [f"{s.get('platform', '')}({s.get('brand', '')})" for s in sns_accounts if s.get("error")]

    return {
        "wp_total": len(sites), "wp_issues": wp_issues,
        "blogger_total": len(bloggers), "blogger_issues": blogger_issues,
        "tistory_total": len(tistory_sites), "tistory_issues": tistory_issues,
        "youtube_total": len(youtube_channels), "youtube_issues": youtube_issues,
        "sns_total": len(sns_accounts), "sns_issues": sns_issues,
        "all_clear": not (wp_issues or blogger_issues or tistory_issues or youtube_issues or sns_issues),
    }


@app.route("/")
def index():
    # 2026-09-03: WP cards no longer show a manual keyword-entry form (WP
    # auto-publishes from its own keyword pool once the GPT gate approves),
    # so per-site keyword_suggestions is no longer rendered — drop the
    # per-site weekly_suggestions() computation instead of paying for 27
    # unused API calls on every page load.
    sites = get_site_data()
    bloggers = get_blogger_data()
    tistory_sites = get_tistory_data()
    youtube_channels = get_youtube_data()
    sns_accounts = get_sns_data()
    return render_template(
        "index.html", sites=sites, bloggers=bloggers, tistory_sites=tistory_sites,
        youtube_channels=youtube_channels, sns_accounts=sns_accounts,
        problem_summary=build_problem_summary(sites, bloggers, tistory_sites, youtube_channels, sns_accounts),
        text_models=TEXT_MODELS, image_models=IMAGE_MODELS,
    )


@app.get("/api/keyword-suggestions/<path:domain>")
def keyword_suggestions(domain: str):
    items = weekly_suggestions(domain)
    return jsonify({
        "domain": domain,
        "count": len(items),
        "recommendations": [
            {"keyword": item.keyword, "category": item.category,
             "verification": item.verification}
            for item in items
        ],
    })


@app.get("/api/keyword-suggestions-by-category/<path:domain>")
def keyword_suggestions_by_category(domain: str):
    """3 keyword chips per category for the '키워드보고발행' button — today's
    top search-volume/virality picks (see refresh_keyword_pool.py), shown
    before publishing so the CEO can choose the topic instead of the
    '바이럴자동발행' button's blind live auto-research."""
    return jsonify({
        "domain": domain,
        "groups": top_keywords_by_category(domain, per_category=3),
    })


@app.get("/api/tistory-seed-topics/<path:site_id>")
def tistory_seed_topics_route(site_id: str):
    """Chips for a Tistory card's '키워드보고발행' button — that site's own
    configured seed topics, shown before creating the review draft."""
    return jsonify({
        "site_id": site_id,
        "groups": tistory_seed_topics(site_id),
    })


def main() -> None:
    port = int(os.environ.get("CONTROL_CENTER_PORT", "8766"))
    print(f"Korea 365 Control Center: http://127.0.0.1:{port}")
    from waitress import serve
    serve(app, host="127.0.0.1", port=port, threads=4)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8766, debug=True)
