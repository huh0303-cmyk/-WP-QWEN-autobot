from flask import Flask, render_template

from flask import Response, flash, jsonify, redirect, request, send_from_directory, url_for

from .keywords import tistory_seed_topics, top_keywords_by_category, weekly_suggestions
from .registry import load_wordpress_sites
from .models import IMAGE_MODELS, TEXT_MODELS
from automation_hub.youtube_vps_queue import enqueue as enqueue_youtube_vps

import json
import csv
import io
import os
import random
import re
import subprocess
import html
import hmac
import secrets
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import date, datetime, timedelta, timezone
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
    """Display one queued Tistory draft with a usable approval hand-off."""
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
    of the web process lifetime — sites were actually fine on re-check.
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

    The bucket keeps VPS page loads fast while refreshing every five minutes.
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
    forever for that web process's lifetime. See _wp_category_counts."""
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
    forever for that web process's lifetime. See _wp_category_counts."""
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
    index_audit_sites = _current_index_manifest(int(time.time() // 300)).get("sites", {})
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
        traffic_date = str(traffic.get("date") or traffic.get("checked_at") or "")[:10]
        current_day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        traffic_fresh = traffic_date == current_day
        today_visitors = traffic.get("daily_visitors") if traffic_fresh else None
        visitor_delta = traffic.get("visitor_delta") if traffic_fresh else None
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
        if index_unknown:
            indexed_delta = None
            if not indexed and not audit_summary.get("unindexed"):
                indexed = None
        if audit_entry.get("error"):
            indexed = None
            indexed_delta = None
        if indexed is not None:
            index_status = (
                f"Google URL별 확인 · 미확인 {index_unknown}개"
                if index_unknown else "Google URL별 전수 확인"
            )
        elif audit_entry.get("error") == "gsc_property_not_accessible":
            index_status = "Search Console 권한 연결 필요"
        else:
            index_status = "확인 실패 · 재검사 필요" if index_unknown or audit_entry.get("error") else "정밀 집계 중"
        sites.append({
            "site_id": registered.site_id if registered else item["domain"],
            "domain": item["domain"],
            "admin_review_url": f"https://{item['domain']}/wp-admin/edit.php?post_status=draft&post_type=post",
            "today_visitors": today_visitors,
            "today_delta": visitor_delta,
            "total_visitors": total_visitors,
            "total_delta": traffic.get("total_delta") if traffic_fresh else None,
            "total_posts": total_posts,
            "posts_delta": posts_delta,
            "indexed": indexed,
            "indexed_delta": indexed_delta,
            "index_unknown": index_unknown,
            "index_unindexed": audit_summary.get("unindexed"),
            "index_total": audit_summary.get("total_published"),
            "index_partial": bool(index_unknown),
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
    stats_at = ""
    if stats_path.exists():
        try:
            stats_payload = json.loads(stats_path.read_text(encoding="utf-8"))
            stats = stats_payload.get("sites", {})
            stats_at = stats_payload.get("generated_at", "")
            if stats_at[:10] != datetime.now(timezone(timedelta(hours=9))).date().isoformat():
                stats = {url: {**values, "today": None, "today_delta": None, "total_delta": None} for url, values in stats.items()}
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
        "visitor_checked_at": stats_at,
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
            �~���$z{-���jם          runs_response.raise_for_status()
            candidates = [
                row for row in runs_response.json().get("workflow_runs", [])
                if datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")) >= dispatch_time - timedelta(seconds=15)
            ]
        except (requests.RequestException, ValueError, KeyError):
            continue
        if candidates:
            newest = max(candidates, key=lambda row: row["created_at"])
            item.update(run_id=newest["id"], run_url=newest.get("html_url", ""), status="running")
            return item
    # Run not found yet — still let the poller keep watching for completion
    # by conclusion never resolving; mark it unresolved instead of failed.
    item.update(status="done", conclusion="unknown", reason="실행 ID를 확인하지 못했습니다 · GitHub Actions에서 직접 확인 필요")
    return item


def _poll_bulk_items(group: str, repo: str, token: str, timeout_seconds: int = 1500) -> None:
    """Update each dispatched item's real conclusion as its GitHub Actions run finishes."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = _bulk_read(group)
        items = state.get("items", [])
        pending = [item for item in items if item["status"] == "running" and item.get("run_id")]
        if not pending:
            break
        changed = False
        for item in pending:
            try:
                run_response = requests.get(
                    f"https://api.github.com/repos/{repo}/actions/runs/{item['run_id']}",
                    headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
                    timeout=15,
                )
                run_response.raise_for_status()
                run_data = run_response.json()
            except (requests.RequestException, ValueError):
                continue
            if run_data.get("status") != "completed":
                continue
            conclusion = str(run_data.get("conclusion") or "unknown")
            reason = "" if conclusion == "success" else (_first_failed_step_label(repo, token, item["run_id"]) or conclusion)
            item.update(status="done", conclusion=conclusion, reason=reason)
            changed = True
        if changed:
            state["items"] = items
            _bulk_write(group, state)
        time.sleep(20)
    state = _bulk_read(group)
    items = state.get("items", [])
    changed = False
    for item in items:
        if item["status"] == "running":
            item.update(status="done", conclusion="timeout", reason="완료 확인 시간 초과 · GitHub Actions/시트에서 직접 확인 필요")
            changed = True
    if changed:
        state["items"] = items
        _bulk_write(group, state)


def _run_group_publish(group: str) -> None:
    """Background worker for one of the six group-level publish buttons.

    2026-09-06 CEO: the single combined '전체글발행' button mixed WP(25) +
    Blogspot(33) + Tistory(5) into one 63-item queue, which made it
    impossible to tell which stage a long run was actually stuck on.
    Split into independently-triggerable, independently-tracked groups:
    wp25, news2 (the 2 newsroom sites), tistory5, blogspot33, and two
    YouTube bundles (youtube_playlist5 / youtube_archive5, split along the
    same PLAYLIST-vs-지식 grouping already used for the channel cards).
    Every site within a group ALSO gets its own individual button and
    tracker elsewhere on the page (_run_single_blogspot_publish,
    _run_single_wp_publish, _run_single_tistory_publish,
    _run_youtube_publish) - the group button here is a convenience to fire
    a whole platform at once without waiting on 5-33 separate clicks."""
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    state: dict[str, object] = {"status": "dispatching", "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None, "items": []}
    _bulk_write(group, state)

    if not token and not group.startswith("youtube_"):
        state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat(), items=[{
            "label": _BULK_GROUP_TITLES.get(group, group), "platform": group, "site_id": "", "workflow": "",
            "run_id": None, "run_url": "", "status": "done", "conclusion": "dispatch_failed",
            "reason": "GitHub 연결(CONTROL_CENTER_GITHUB_TOKEN)이 설정되어 있지 않습니다.",
        }])
        _bulk_write(group, state)
        return

    dispatched: list[dict[str, object]] = []

    def _record(item: dict[str, object]) -> None:
        dispatched.append(item)
        state["items"] = list(dispatched)
        _bulk_write(group, state)

    if group == "wp25":
        targets = [site for site in get_site_data() if site["cadence"]["kind"] != "newsroom" and site["auth_ready"]]
        random.shuffle(targets)
        for site in targets:
            _record(_dispatch_and_track(
                repo, token, "daily-network-publish.yml",
                {
                    "target_site_url": f"https://{site['domain']}",
                    "publication_approved": "true",
                    "room_id": f"bulk-wp25-{site['site_id']}",
                },
                label=site["domain"], platform="wordpress", site_id=site["site_id"],
            ))
            time.sleep(8)  # stagger dispatches so shared GPT/Gemini/GH-Actions capacity doesn't 429 all at once

    elif group == "news2":
        newsrooms = [("koreanews365", "koreanews365.com"), ("theseouljournal", "theseouljournal.com")]
        random.shuffle(newsrooms)
        for newsroom_key, domain in newsrooms:
            _record(_dispatch_and_track(
                repo, token, "newsrooms-daily-publisher.yml",
                {"newsroom": newsroom_key, "preferred_category": ""},
                label=domain, platform="news", site_id=newsroom_key,
            ))
            time.sleep(8)

    elif group == "tistory5":
        _record(_dispatch_and_track(
            repo, token, "tistory-daily-plan.yml",
            {"site_ids": "", "run_key": f"bulk-{int(time.time())}"},
            label="Tistory 5개 전체", platform="tistory",
        ))

    elif group == "blogspot33":
        targets = [blog for blog in get_blogger_data() if blog["connected"]]
        random.shuffle(targets)
        for blog in targets:
            try:
                workflow_name, inputs = _build_draft_workflow_call({
                    "platform": "blogger", "selection_mode": "auto", "site_id": blog["site_id"], "keyword": "",
                    "jitter_max_seconds": "60",
                })
            except RuntimeError as exc:
                _record({
                    "label": blog["name"], "platform": "blogger", "site_id": blog["site_id"], "workflow": "blogger-rewrite.yml",
                    "run_id": None, "run_url": "", "status": "done", "conclusion": "dispatch_failed", "reason": str(exc),
                    "dispatched_at": datetime.now(timezone.utc).isoformat(),
                })
                continue
            _record(_dispatch_and_track(repo, token, workflow_name, inputs, label=blog["name"], platform="blogger", site_id=blog["site_id"]))
            time.sleep(8)

    elif group in ("youtube_playlist5", "youtube_archive5"):
        want_playlist = group == "youtube_playlist5"
        targets = [ch for ch in get_youtube_data() if ch.get("action_ready") and (ch.get("group") == "PLAYLIST") == want_playlist]
        for channel in targets:
            label = str(channel.get("official_name") or channel["channel_key"])
            try:
                job = enqueue_youtube_vps(channel["channel_key"], label, group, run_now=True)
                _record({"job_id": job["job_id"], "label": label, "platform": "youtube",
                         "site_id": channel["channel_key"], "workflow": "youtube-vps-worker", "run_id": None,
                         "run_url": "", "status": "queued", "conclusion": None, "reason": "VPS 제작 대기"})
            except RuntimeError as exc:
                _record({"label": label, "platform": "youtube", "site_id": channel["channel_key"],
                         "workflow": "youtube-vps-worker", "run_id": None, "run_url": "", "status": "done",
                         "conclusion": "queue_failed", "reason": str(exc)})

    if group.startswith("youtube_"):
        state["status"] = "polling" if any(item.get("status") != "done" for item in state["items"]) else "done"
        _bulk_write(group, state)
        return
    state["status"] = "polling"
    _bulk_write(group, state)
    # Video render + upload can run long, same reasoning as the per-channel
    # YouTube button (_run_youtube_publish) - everything else keeps the
    # shorter default. The youtube_* groups already polled each channel to
    # completion above; this call is a no-op for them (nothing left
    # "running") and only does real work for the non-YouTube groups.
    poll_timeout = 1800 * 5 if group.startswith("youtube_") else 1500
    _poll_bulk_items(group, repo, token, timeout_seconds=poll_timeout)
    state = _bulk_read(group)
    state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat())
    _bulk_write(group, state)


def _run_single_blogspot_publish(site_id: str, label: str) -> None:
    """Background worker for one Blogspot site's dedicated publish button.

    2026-09-06 CEO: once the shared-concurrency-slot bug in
    blogger-rewrite.yml was fixed, asked for Blogspot's 33 sites to each
    get their own button and live tracker exactly like YouTube's 10
    channels, instead of one 33-in-one-click group where a stall on one
    site hid the other 32. Reuses '바이럴자동발행''s own dispatch (auto
    topic selection, no keyword) so behavior is identical - only the
    visibility of the result changes."""
    group = f"blogspot_{site_id}"
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    state: dict[str, object] = {"status": "dispatching", "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None, "items": []}
    _bulk_write(group, state)

    if not token:
        state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat(), items=[{
            "label": label, "platform": "blogger", "site_id": site_id, "workflow": "",
            "run_id": None, "run_url": "", "status": "done", "conclusion": "dispatch_failed",
            "reason": "GitHub 연결(CONTROL_CENTER_GITHUB_TOKEN)이 설정되어 있지 않습니다.",
        }])
        _bulk_write(group, state)
        return

    try:
        workflow_name, inputs = _build_draft_workflow_call({
            "platform": "blogger", "selection_mode": "auto", "site_id": site_id, "keyword": "",
        })
    except RuntimeError as exc:
        state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat(), items=[{
            "label": label, "platform": "blogger", "site_id": site_id, "workflow": "blogger-rewrite.yml",
            "run_id": None, "run_url": "", "status": "done", "conclusion": "dispatch_failed", "reason": str(exc),
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
        }])
        _bulk_write(group, state)
        return

    item = _dispatch_and_track(repo, token, workflow_name, inputs, label=label, platform="blogger", site_id=site_id)
    state["items"] = [item]
    state["status"] = "polling"
    _bulk_write(group, state)
    _poll_bulk_items(group, repo, token)
    state = _bulk_read(group)
    state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat())
    _bulk_write(group, state)


@app.post("/trigger/blogspot-single")
def trigger_blogspot_single():
    """One Blogspot site's dedicated live-tracked '바이럴자동발행' button."""
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#blogspot")
    site_id = request.form.get("site_id", "").strip()
    blogs_by_id = {str(blog["site_id"]): blog for blog in get_blogger_data() if blog["connected"]}
    if not site_id or site_id not in blogs_by_id:
        flash("발행이 연결된 Blogspot 사이트가 아닙니다.", "error")
        return redirect(url_for("index") + "#blogspot")
    group = f"blogspot_{site_id}"
    already_running = _bulk_read(group).get("status") in {"dispatching", "polling"}
    label = str(blogs_by_id[site_id].get("name") or site_id)
    if already_running:
        flash(f"{label} 발행이 이미 진행 중입니다. 완료될 때까지 기다려주세요.", "error")
        return redirect(url_for("index") + "#blogspot")
    threading.Thread(target=_run_single_blogspot_publish, args=(site_id, label), daemon=True).start()
    flash(f"{label} 발행을 시작했습니다 — 카드 아래에서 실시간으로 확인하세요.", "success")
    return redirect(url_for("index") + "#blogspot")


def _run_single_wp_publish(site_id: str, domain: str, label: str) -> None:
    """Background worker for one WordPress site's dedicated publish button.

    2026-09-06 CEO: wanted every one of the 27 WP sites to get its own
    button and live tracker exactly like Blogspot's 33 and YouTube's 10,
    instead of the per-card '바이럴자동발행' firing a one-shot flash with no
    completion visibility. Dispatches the same daily-network-publish.yml
    with publication_approved=true the WP25 bulk group and single-site
    quick-publish button already use."""
    group = f"wp_{site_id}"
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    state: dict[str, object] = {"status": "dispatching", "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None, "items": []}
    _bulk_write(group, state)

    if not token:
        state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat(), items=[{
            "label": label, "platform": "wordpress", "site_id": site_id, "workflow": "",
            "run_id": None, "run_url": "", "status": "done", "conclusion": "dispatch_failed",
            "reason": "GitHub 연결(CONTROL_CENTER_GITHUB_TOKEN)이 설정되어 있지 않습니다.",
        }])
        _bulk_write(group, state)
        return

    item = _dispatch_and_track(
        repo, token, "daily-network-publish.yml",
        {"target_site_url": f"https://{domain}", "publication_approved": "true", "room_id": f"manual-single-{site_id}"},
        label=label, platform="wordpress", site_id=site_id,
    )
    state["items"] = [item]
    state["status"] = "polling"
    _bulk_write(group, state)
    _poll_bulk_items(group, repo, token)
    state = _bulk_read(group)
    state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat())
    _bulk_write(group, state)


@app.post("/trigger/wp-single")
def trigger_wp_single():
    """One WordPress site's dedicated live-tracked '바이럴자동발행' button."""
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#wordpress")
    site_id = request.form.get("site_id", "").strip()
    sites_by_id = {str(site["site_id"]): site for site in get_site_data() if site["auth_ready"]}
    if not site_id or site_id not in sites_by_id:
        flash("발행이 연결된 WordPress 사이트가 아닙니다.", "error")
        return redirect(url_for("index") + "#wordpress")
    group = f"wp_{site_id}"
    already_running = _bulk_read(group).get("status") in {"dispatching", "polling"}
    site = sites_by_id[site_id]
    label = str(site["domain"])
    if already_running:
        flash(f"{label} 발행이 이미 진행 중입니다. 완료될 때까지 기다려주세요.", "error")
        return redirect(url_for("index") + "#wordpress")
    threading.Thread(target=_run_single_wp_publish, args=(site_id, site["domain"], label), daemon=True).start()
    flash(f"{label} 발행을 시작했습니다 — 카드 아래에서 실시간으로 확인하세요.", "success")
    return redirect(url_for("index") + "#wordpress")


def _run_single_tistory_publish(site_id: str, label: str) -> None:
    """Background worker for one Tistory site's dedicated publish button.

    Same live-tracking treatment as Blogspot/WP/YouTube. Tistory has no
    unattended cloud publish API, so this still only reaches a private
    review draft that the logged-in local registrar (tistory_local_runner.py)
    finishes - the tracker reports that stage honestly, not a fake public
    publish."""
    group = f"tistory_{site_id}"
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    state: dict[str, object] = {"status": "dispatching", "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None, "items": []}
    _bulk_write(group, state)

    if not token:
        state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat(), items=[{
            "label": label, "platform": "tistory", "site_id": site_id, "workflow": "",
            "run_id": None, "run_url": "", "status": "done", "conclusion": "dispatch_failed",
            "reason": "GitHub 연결(CONTROL_CENTER_GITHUB_TOKEN)이 설정되어 있지 않습니다.",
        }])
        _bulk_write(group, state)
        return

    item = _dispatch_and_track(
        repo, token, "tistory-daily-plan.yml",
        {"site_ids": site_id, "run_key": f"manual-{site_id}-{int(time.time())}"},
        label=label, platform="tistory", site_id=site_id,
    )
    state["items"] = [item]
    state["status"] = "polling"
    _bulk_write(group, state)
    _poll_bulk_items(group, repo, token)
    state = _bulk_read(group)
    state.update(status="done", finished_at=datetime.now(timezone.utc).isoformat())
    _bulk_write(group, state)


@app.post("/trigger/tistory-single")
def trigger_tistory_single():
    """One Tistory site's dedicated live-tracked '바이럴자동발행' button."""
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#tistory")
    site_id = request.form.get("site_id", "").strip()
    sites_by_id = {str(site["site_id"]): site for site in get_tistory_data()}
    if not site_id or site_id not in sites_by_id:
        flash("등록되지 않은 Tistory 사이트입니다.", "error")
        return redirect(url_for("index") + "#tistory")
    group = f"tistory_{site_id}"
    already_running = _bulk_read(group).get("status") in {"dispatching", "polling"}
    label = str(sites_by_id[site_id].get("name") or site_id)
    if already_running:
        flash(f"{label} 발행이 이미 진행 중입니다. 완료될 때까지 기다려주세요.", "error")
        return redirect(url_for("index") + "#tistory")
    threading.Thread(target=_run_single_tistory_publish, args=(site_id, label), daemon=True).start()
    flash(f"{label} 검토본 생성을 시작했습니다 — 카드 아래에서 실시간으로 확인하세요.", "success")
    return redirect(url_for("index") + "#tistory")


@app.post("/trigger/publish-group/<group>")
def trigger_publish_group(group: str):
    """One of the six group-level publish buttons — see _run_group_publish."""
    if group not in _BULK_GROUPS:
        flash("알 수 없는 발행 그룹입니다.", "error")
        return redirect(url_for("index"))
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index"))
    already_running = _bulk_read(group).get("status") in {"dispatching", "polling"}
    if already_running:
        flash(f"{_BULK_GROUP_TITLES.get(group, group)} 발행이 이미 진행 중입니다. 완료될 때까지 기다려주세요.", "error")
        return redirect(url_for("index"))
    threading.Thread(target=_run_group_publish, args=(group,), daemon=True).start()
    flash(f"{_BULK_GROUP_TITLES.get(group, group)} 발행을 시작했습니다 — 아래 패널에서 실시간으로 확인하세요.", "success")
    return redirect(url_for("index"))


@app.get("/api/publish-group-status/<group>")
def publish_group_status(group: str):
    individual_prefixes = ("youtube_", "blogspot_", "wp_", "tistory_")
    if group not in _BULK_GROUPS and not group.startswith(individual_prefixes):
        return jsonify({"error": "unknown group"}), 404
    return jsonify(_bulk_snapshot(group))


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


@lru_cache(maxsize=2)
def _current_index_manifest(bucket):
    # Hosted audits update data independently; the VPS must not require a
    # restart (and interruption of publishing workers) to show new evidence.
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    try:
        response = requests.get(f"https://raw.githubusercontent.com/{repo}/main/index_audit_manifest.json", timeout=12)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        path = Path(__file__).resolve().parents[1] / "index_audit_manifest.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}


@app.template_filter("kst_time")
def kst_time(value):
    if not value:
        return "시각 미확인"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return str(value)
        return parsed.astimezone(timezone(timedelta(hours=9))).strftime("%m-%d %H:%M KST")
    except ValueError:
        return str(value)


@lru_cache(maxsize=2)
def _tile_receipts(bucket):
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    try:
        response = requests.get(f"https://raw.githubusercontent.com/{repo}/main/data/site-publication-history.json", timeout=8)
        response.raise_for_status()
        return response.json().get("events", [])
    except (requests.RequestException, ValueError):
        path = Path(__file__).resolve().parents[1] / "data/site-publication-history.json"
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("events", [])
        except (OSError, ValueError):
            return []


def _tile_histories():
    from .tile_status import local_events, summarize
    by_site = {}
    for event in _tile_receipts(int(time.time() // 60)):
        by_site.setdefault(event["site_id"], []).append(event)
    for path in (Path(__file__).resolve().parents[1] / "data").glob("bulk_publish_state_*.json"):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for site_id in {i.get("site_id") for i in state.get("items", []) if i.get("site_id")}:
            by_site.setdefault(site_id, []).extend(local_events(state, site_id))
    # Durable verified Tistory public receipts; planner success is not publication.
    for path in (Path(__file__).resolve().parents[1] / "data").glob("tistory-publishing-*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload if isinstance(payload, list) else payload.get("results", [])
            for row in rows:
                if row.get("status") == "published" and row.get("site_id"):
                    by_site.setdefault(row["site_id"], []).append({**row, "at": row.get("published_at") or row.get("verified_at") or "", "run_id": row.get("job_id")})
        except (OSError, ValueError, TypeError):
            pass
    return {key: summarize(value) for key, value in by_site.items()}


@app.get("/api/site-publication-history")
def site_publication_history():
    return jsonify(_tile_histories())


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
    from .tile_status import new_content
    targets = [(site, "https://" + site["domain"], "wordpress") for site in sites]
    targets += [(site, site["url"], "blogger") for site in bloggers]
    targets += [(site, site["url"], "tistory") for site in tistory_sites]
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [(site, pool.submit(new_content, url, platform, int(time.time() // 300))) for site, url, platform in targets]
        for site, future in futures:
            site.update(future.result())
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
