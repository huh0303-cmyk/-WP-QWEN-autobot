"""Read-only public collector for the three Naver Blog cards (N1/N2/N3).

Naver Blog's own logged-in 네이버 블로그 관리 > 통계 dashboard is still not
scrapable, but the daily visitor count is not actually private: every blog
skin renders its "오늘 방문자" widget by calling NVisitorgp4Ajax.naver, a
public, unauthenticated XML gadget feed keyed only by blogId. This module
reads that feed directly instead of assuming visitor counts are categorically
unavailable; when the gadget itself is unreachable or returns nothing
parseable, the card still reports None with an explicit connector reason
instead of a fake zero. Post counts and the latest post come from the public
RSS feed and, best-effort, the public homepage's "전체보기 (N)" widget when
the blog skin renders it.
"""
from __future__ import annotations

import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path

import requests

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]

NAVER_VISITOR_ENDPOINT = "https://blog.naver.com/NVisitorgp4Ajax.naver"

VISITOR_UNAVAILABLE_REASON = (
    "네이버 방문자 위젯(NVisitorgp4Ajax.naver) 응답을 확인하지 못했습니다 — "
    "로그인 전용 통계가 아니라 일시적 연결 실패일 수 있습니다."
)
TOTAL_POSTS_PATTERN = re.compile(r"전체보기\s*\(\s*([\d,]+)\s*\)")

PERSONA_BY_BLOG_ID = {
    "huh0303": ("생활행정 정보 큐레이터", "신청기한·대상·공식 조회 경로를 빠르고 명료하게 안내"),
}
DEFAULT_PERSONA = ("전문 편집자", "공식 출처 중심의 실용적 설명")


def _naver_rooms() -> list[dict]:
    path = ROOT / "config" / "automation_rooms.json"
    try:
        rooms = json.loads(path.read_text(encoding="utf-8")).get("rooms", [])
    except (OSError, ValueError):
        return []
    return [
        room for room in rooms
        if room.get("platform") == "naver" and str(room.get("destination_id") or "").strip()
    ]


def _parse_rfc822(value: str) -> datetime:
    stamp = parsedate_to_datetime(value)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp


@lru_cache(maxsize=16)
def _naver_public_summary(blog_id: str, five_minute_bucket: int) -> dict[str, object]:
    """Best-effort public read: RSS latest post + homepage 'view all' post count."""
    del five_minute_bucket
    summary: dict[str, object] = {
        "connected": False, "total_posts": None, "today": 0,
        "latest_url": "", "latest_title": "", "latest_at": None, "error": "",
    }
    try:
        response = requests.get(
            f"https://rss.blog.naver.com/{blog_id}.xml", timeout=15,
            headers={"User-Agent": "Korea365-Control-Room/1.0"},
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall("./channel/item")
        summary["connected"] = True
        today = datetime.now(KST).date()
        counted_today = 0
        for item in items:
            pub_date = item.findtext("pubDate")
            try:
                stamp = _parse_rfc822(pub_date) if pub_date else None
            except (TypeError, ValueError):
                stamp = None
            if stamp is not None and stamp.astimezone(KST).date() == today:
                counted_today += 1
        summary["today"] = counted_today
        if items:
            first = items[0]
            summary["latest_url"] = first.findtext("link") or ""
            summary["latest_title"] = html.unescape((first.findtext("title") or "").strip())
            summary["latest_at"] = first.findtext("pubDate")
    except (requests.RequestException, ET.ParseError):
        summary["error"] = "rss_unavailable"

    try:
        homepage = requests.get(
            f"https://blog.naver.com/{blog_id}", timeout=15,
            headers={"User-Agent": "Korea365-Control-Room/1.0"},
        )
        homepage.raise_for_status()
        match = TOTAL_POSTS_PATTERN.search(homepage.text)
        if match:
            summary["total_posts"] = int(match.group(1).replace(",", ""))
            summary["connected"] = True
    except requests.RequestException:
        pass
    return summary


def _attach_naver_post_deltas(summaries: dict[str, dict[str, object]]) -> None:
    """Persist today's total-post snapshot and attach a day-over-day delta."""
    snapshot_path = ROOT / "data" / "naver_post_counts_latest.json"
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
    current: dict[str, int] = {}
    for blog_id, summary in summaries.items():
        total = summary.get("total_posts")
        prior_total = previous.get(blog_id)
        summary["total_delta"] = (
            int(total) - int(prior_total) if total is not None and prior_total is not None else None
        )
        if total is not None:
            current[blog_id] = int(total)
    payload = {"date": today, "previous": previous, "sites": current}
    try:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


@lru_cache(maxsize=16)
def _naver_visitor_stats(blog_id: str, five_minute_bucket: int) -> dict[str, object]:
    """Read Naver Blog's own public daily-visitor XML gadget feed.

    NVisitorgp4Ajax.naver is the same endpoint blog skins call directly to
    render the "오늘 방문자" counter — it needs no login or API key. Naver
    does not publish a stable schema for this legacy gadget, so field names
    are matched loosely (any tag or attribute whose name contains
    "today"/"yesterday"/"total") rather than pinned to one exact tag.
    """
    del five_minute_bucket
    try:
        response = requests.get(
            NAVER_VISITOR_ENDPOINT, params={"blogId": blog_id}, timeout=15,
            headers={"User-Agent": "Korea365-Control-Room/1.0", "Referer": f"https://blog.naver.com/{blog_id}"},
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError):
        return {"connected": False, "reason": "visitor gadget request failed"}

    # The public gadget returns rows like:
    # <visitorcnt id="20260928" cnt="5" />.  Use the KST date ids directly.
    by_day: dict[str, int] = {}
    for node in root.iter():
        day_id = str(node.attrib.get("id") or "").strip()
        count = str(node.attrib.get("cnt") or "").replace(",", "").strip()
        if len(day_id) == 8 and day_id.isdigit() and count.isdigit():
            by_day[day_id] = int(count)

    today_date = datetime.now(KST).date()
    today_key = today_date.strftime("%Y%m%d")
    yesterday_key = (today_date - timedelta(days=1)).strftime("%Y%m%d")
    day_before_key = (today_date - timedelta(days=2)).strftime("%Y%m%d")
    if yesterday_key not in by_day:
        return {"connected": False, "reason": "visitor gadget response missing yesterday row"}
    today_count = by_day.get(today_key, 0)
    yesterday_count = by_day[yesterday_key]
    day_before_count = by_day.get(day_before_key)
    return {
        "connected": True,
        "today": today_count,
        "yesterday": yesterday_count,
        "day_before_yesterday": day_before_count,
        "today_delta": today_count - yesterday_count,
        "yesterday_delta": (
            yesterday_count - day_before_count if day_before_count is not None else None
        ),
        # Naver's public gadget is daily-only; cumulative total is not exposed.
        "total": None,
        "total_delta": None,
        "checked_at": datetime.now(KST).isoformat(),
    }


def _attach_naver_visitor_deltas(stats: dict[str, dict[str, object]]) -> None:
    """Attach yesterday-over-day-before delta using the prior daily snapshot.

    Mirrors _attach_tistory_visitor_deltas in control_center/app.py: the
    gadget itself only ever reports today/yesterday, so a comparison against
    the day before yesterday needs yesterday's own stored reading.
    """
    snapshot_path = ROOT / "data" / "naver_visitor_latest.json"
    today = date.today().isoformat()
    try:
        stored = json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else {}
    except (OSError, ValueError):
        stored = {}
    previous = stored.get("previous", {}) if stored.get("date") == today else stored.get("sites", {})
    if not isinstance(previous, dict):
        previous = {}
    current: dict[str, dict[str, object]] = {}
    for blog_id, row in stats.items():
        if not row.get("connected"):
            continue
        prior = previous.get(blog_id, {}) if isinstance(previous.get(blog_id, {}), dict) else {}
        if row.get("yesterday_delta") is None:
            prior_yesterday = prior.get("yesterday")
            row["yesterday_delta"] = (
                int(row["yesterday"]) - int(prior_yesterday) if prior_yesterday is not None else None
            )
        if row.get("today_delta") is None:
            row["today_delta"] = int(row["today"]) - int(row["yesterday"])
        if row.get("total") is not None and row.get("total_delta") is None:
            row["total_delta"] = int(row["today"])
        current[blog_id] = {"today": row["today"], "yesterday": row["yesterday"], "total": row.get("total")}
    try:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps({"date": today, "previous": previous, "sites": current}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def get_naver_data() -> list[dict[str, object]]:
    """Build the three Naver control-room cards from the public visitor gadget
    plus the RSS/homepage post summary, never inferring numbers that fail."""
    rooms = _naver_rooms()
    bucket = int(time.time() // 300)
    summaries = {
        room["destination_id"]: _naver_public_summary(room["destination_id"], bucket)
        for room in rooms
    }
    _attach_naver_post_deltas(summaries)
    visitor_stats = {
        room["destination_id"]: _naver_visitor_stats(room["destination_id"], bucket)
        for room in rooms
    }
    _attach_naver_visitor_deltas(visitor_stats)
    result = []
    for order, room in enumerate(rooms, 1):
        blog_id = str(room["destination_id"])
        summary = summaries.get(blog_id, {})
        traffic = visitor_stats.get(blog_id, {})
        persona, tone = PERSONA_BY_BLOG_ID.get(blog_id, DEFAULT_PERSONA)
        result.append({
            "site_id": room.get("room_id") or f"naver_{blog_id}",
            "order": order,
            "name": room.get("name") or f"Naver · {blog_id}",
            "url": f"https://blog.naver.com/{blog_id}",
            "admin_review_url": room.get("editor_url") or f"https://blog.naver.com/GoBlogWrite.naver?blogId={blog_id}",
            "status": room.get("status", "UNKNOWN"),
            "category": "",
            "official_categories": [],
            "persona": persona,
            "tone": tone,
            "default_text_model": "gpt-5-mini",
            "default_image_model": "bytedance/sdxl-lightning-4step",
            "today_visitors": traffic.get("today"),
            "today_delta": traffic.get("today_delta"),
            "yesterday_visitors": traffic.get("yesterday"),
            "yesterday_delta": traffic.get("yesterday_delta"),
            "total_visitors": traffic.get("total"),
            "total_delta": traffic.get("total_delta"),
            "visitor_connected": bool(traffic.get("connected")),
            "visitor_checked_at": traffic.get("checked_at", "") if traffic.get("connected") else "",
            "visitor_error": "" if traffic.get("connected") else (traffic.get("reason") or VISITOR_UNAVAILABLE_REASON),
            "total_posts": summary.get("total_posts"),
            "posts_delta": summary.get("total_delta"),
            "today_posts": summary.get("today"),
            "indexed": None,
            "indexed_delta": None,
            "index_status": "Search Console 속성 미등록 · 색인 확인 불가",
            "feed_connected": bool(summary.get("connected")),
            "feed_error": summary.get("error", ""),
            "latest_url": summary.get("latest_url", ""),
            "latest_title": summary.get("latest_title", ""),
            "latest_at": summary.get("latest_at"),
            "checked_at": datetime.now(KST).isoformat(),
        })
    return result
