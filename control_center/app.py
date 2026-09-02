from flask import Flask, render_template

from flask import Response, flash, jsonify, redirect, request, send_from_directory, url_for

from .keywords import weekly_suggestions
from .registry import load_wordpress_sites
from .models import IMAGE_MODELS, TEXT_MODELS

import json
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

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("CONTROL_CENTER_SECRET_KEY") or secrets.token_hex(32)
app.config["CONTROL_CENTER_CSRF"] = os.environ.get("CONTROL_CENTER_CSRF") or secrets.token_urlsafe(24)


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


@lru_cache(maxsize=64)
def _wp_category_counts(site_url: str) -> list[dict[str, object]]:
    """Read the categories actually registered in WordPress, including zero-count ones."""
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


@lru_cache(maxsize=64)
def _blogger_label_counts(blog_url: str) -> list[dict[str, object]]:
    """Count labels used by publicly visible Blogger posts."""
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


@lru_cache(maxsize=16)
def _tistory_feed_summary(site_url: str) -> dict[str, object]:
    """Read exact public category counts, falling back to the Tistory RSS feed."""
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
    registry_by_domain = {
        site.url.replace("https://", "").replace("http://", "").rstrip("/"): site
        for site in load_wordpress_sites()
    }
    # Categories and visitor counters are independent public APIs. Fetch them
    # together so one slow site cannot serialize the entire 27-site dashboard.
    bucket = int(time.time() // 300)
    with ThreadPoolExecutor(max_workers=32) as executor:
        category_futures = {
            domain: executor.submit(_wp_category_counts, site.url)
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
        total_posts = detail.get("total_posts", traffic.get("total_posts"))
        indexed = detail.get("indexed", traffic.get("indexed"))
        sites.append({
            "site_id": registered.site_id if registered else item["domain"],
            "domain": item["domain"],
            "today_visitors": today_visitors,
            "today_delta": visitor_delta,
            "total_visitors": total_visitors,
            "total_delta": traffic.get("total_delta"),
            "total_posts": total_posts,
            "posts_delta": None,
            "indexed": indexed,
            "indexed_delta": traffic.get("recent_index_increase"),
            "visitor_connected": bool(live_traffic.get("connected")),
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
        site["domain"] != "k-health365.com",
        -(site["today_visitors"] or 0),
    ))


def _site_rows(_sites=None):
    """Compatibility hook used by tests and the richer control-center shell."""
    return get_site_data(), None


def get_blogger_data():
    path = Path(__file__).resolve().parents[1] / "config" / "blogger_portfolio.json"
    rows = json.loads(path.read_text(encoding="utf-8")).get("channels", [])
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
            lambda row: (row.get("blogspot", ""), _blogger_label_counts(row.get("blogspot", ""))),
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
        "status": row.get("status", "UNKNOWN"),
        "blog_id": row.get("destination_id", ""),
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
            lambda row: (row.get("site_id", ""), _tistory_feed_summary(row.get("url", ""))),
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
    path = Path(__file__).resolve().parents[1] / "config" / "automation_rooms.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = []
    for room in payload.get("rooms", []):
        if room.get("platform") != "youtube":
            continue
        channel_id = str(room.get("destination_id", "")).strip()
        rows.append({
            "room_id": str(room.get("room_id", "")),
            "name": str(room.get("name", "")),
            "group": str(room.get("group", "")),
            "channel_id": channel_id,
            "channel_url": f"https://www.youtube.com/channel/{channel_id}" if channel_id else "",
            "workflow": str(room.get("workflow", "")),
            "publish_policy": str(room.get("publish_policy", "private")),
            "status": str(room.get("status", "UNKNOWN")),
            "enabled": bool(room.get("enabled", False)),
            "sheet_controlled": True,
        })
    return sorted(rows, key=lambda row: (row["group"] != "PLAYLIST", row["name"].casefold()))


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
    """Dispatch the real GitHub draft worker; this command cannot publish publicly."""
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-wp-qwen-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    inputs = {
        "site_id": str(payload["site_id"]),
        "keyword": str(payload["keyword"]),
        "source_wp_url": str(payload.get("source_wp_url") or ""),
        "text_model": str(payload["text_model"]),
        "image_model": str(payload["image_model"]),
    }
    if token:
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/sheet-triggered-auto-write.yml/dispatches",
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
        return f"https://github.com/{repo}/actions/workflows/sheet-triggered-auto-write.yml"
    command = [
        "gh", "workflow", "run", "sheet-triggered-auto-write.yml",
        "--repo", repo,
        *[part for key, value in inputs.items() for part in ("-f", f"{key}={value}")],
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "GitHub workflow dispatch failed").strip())
    return f"https://github.com/{repo}/actions/workflows/sheet-triggered-auto-write.yml"


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
    anchor = "blogspot" if platform == "blogger" else "wordpress"

    if platform not in {"wordpress", "blogger"} or not domain:
        flash("사이트 정보가 올바르지 않습니다.", "error")
    elif len(keyword) < 2:
        flash(f"{domain}: 핵심 키워드를 2자 이상 입력하세요.", "error")
    elif text_model not in TEXT_MODELS or image_model not in IMAGE_MODELS:
        flash(f"{domain}: 지원하지 않는 엔진입니다.", "error")
    elif platform == "blogger" and not source_wp_url.startswith("https://"):
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
        }
        if not payload["site_id"].startswith(("wp_", "blogger_")):
            flash(f"{domain}: 실행용 사이트 ID 연결이 완료되지 않았습니다.", "error")
            return redirect(url_for("index") + f"#{anchor}")
        trigger_id = _queue_draft_trigger(payload)
        try:
            workflow_url = _dispatch_draft_workflow(payload)
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            flash(f"{domain}: 로컬 대기열에는 저장했지만 GitHub 실행 요청 실패 · {exc}", "error")
        else:
            flash(f"{domain}: 실제 비공개 초안 작업 시작 · {trigger_id} · {workflow_url}", "success")
    return redirect(url_for("index") + f"#{anchor}")


@app.post("/trigger/tistory-plan")
def trigger_tistory_plan():
    """Start the existing five-site review bundle; it never authorizes publication."""
    if request.form.get("csrf_token") != app.config["CONTROL_CENTER_CSRF"]:
        flash("요청 확인값이 만료되었습니다. 새로고침 후 다시 시도하세요.", "error")
        return redirect(url_for("index") + "#tistory")
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-wp-qwen-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    try:
        if token:
            response = requests.post(
                f"https://api.github.com/repos/{repo}/actions/workflows/tistory-daily-plan.yml/dispatches",
                headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
                json={"ref": "main"}, timeout=30,
            )
            if response.status_code != 204:
                raise RuntimeError(f"GitHub API dispatch failed ({response.status_code})")
            completed = None
        else:
            command = ["gh", "workflow", "run", "tistory-daily-plan.yml", "--repo", repo]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError, requests.RequestException, RuntimeError) as exc:
        flash(f"Tistory 5개 검토본 실행 요청 실패 · {exc}", "error")
    else:
        if completed is None or completed.returncode == 0:
            flash("Tistory 5개 비공개 검토본 생성을 시작했습니다. 공개 발행은 하지 않습니다.", "success")
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
    repo = os.environ.get("CONTROL_CENTER_GITHUB_REPO", "huh0303-cmyk/-WP-QWEN-autobot")
    token = os.environ.get("CONTROL_CENTER_GITHUB_TOKEN", "").strip()
    if not token:
        flash("YouTube 중앙 스케줄러 실행용 GitHub 연결이 필요합니다.", "error")
        return redirect(url_for("index") + "#youtube")
    try:
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/youtube-control-scheduler.yml/dispatches",
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
            json={"ref": "main", "inputs": {"dry_run": "false", "max_dispatch": "10"}},
            timeout=30,
        )
        if response.status_code != 204:
            raise RuntimeError(f"GitHub API dispatch failed ({response.status_code})")
    except (requests.RequestException, RuntimeError) as exc:
        flash(f"YouTube 10채널 실행 요청 실패 · {exc}", "error")
    else:
        flash("YouTube 중앙 스케줄러를 시작했습니다. 현재 승인 슬롯이 있으면 전체에서 1개만 비공개 업로드합니다.", "success")
    return redirect(url_for("index") + "#youtube")

@app.route("/")
def index():
    sites = get_site_data()
    for site in sites:
        site["keyword_suggestions"] = weekly_suggestions(site["domain"])
    return render_template(
        "index.html", sites=sites, bloggers=get_blogger_data(), tistory_sites=get_tistory_data(),
        youtube_channels=get_youtube_data(),
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


def main() -> None:
    port = int(os.environ.get("CONTROL_CENTER_PORT", "8766"))
    print(f"Korea 365 Control Center: http://127.0.0.1:{port}")
    from waitress import serve
    serve(app, host="127.0.0.1", port=port, threads=4)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8766, debug=True)
