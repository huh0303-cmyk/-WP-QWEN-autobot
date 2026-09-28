"""Read-only public collector for the three Naver Blog cards (N1/N2/N3).

Naver Blog does not expose visitor counts through any public API or feed —
that number is only visible to the logged-in blog owner inside 네이버 블로그
관리 > 통계. This module never invents that number; every card reports it as
None with an explicit connector reason instead of a fake zero. Post counts
and the latest post come from the public RSS feed and, best-effort, the
public homepage's "전체보기 (N)" widget when the blog skin renders it.
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

VISITOR_UNAVAILABLE_REASON = (
    "네이버 블로그 방문자 수는 로그인한 블로그 소유자만 볼 수 있는 비공개 통계이며 "
    "공개 API가 없어 자동 수집할 수 없습니다."
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


def get_naver_data() -> list[dict[str, object]]:
    """Build the three Naver control-room cards without inferring visitor data."""
    rooms = _naver_rooms()
    bucket = int(time.time() // 300)
    summaries = {
        room["destination_id"]: _naver_public_summary(room["destination_id"], bucket)
        for room in rooms
    }
    _attach_naver_post_deltas(summaries)
    result = []
    for order, room in enumerate(rooms, 1):
        blog_id = str(room["destination_id"])
        summary = summaries.get(blog_id, {})
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
            "today_visitors": None,
            "today_delta": None,
            "total_visitors": None,
            "total_delta": None,
            "visitor_error": VISITOR_UNAVAILABLE_REASON,
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
