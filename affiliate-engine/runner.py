#!/usr/bin/env python3
"""Append verified affiliate blocks to newly published WordPress and Blogger posts.

This runner is intentionally deterministic: it does not call an LLM, invent a
tracking URL, alter existing affiliate blocks, or write unless --write and the
AFFILIATE_WRITE_ENABLED=true environment gate are both present.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "affiliate-engine"
ROUTING = ENGINE / "config" / "affiliate-routing.json"
OFFERS = ENGINE / "data" / "offers.json"
PROFILES = ROOT / "config" / "content_engine_profiles.json"
MARKER = "<!-- london-affiliate-engine:v2 -->"
DISCLOSURE = "<p><small>Disclosure: This section may contain affiliate links. We may earn a commission at no extra cost to you.</small></p>"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(value: str) -> str:
    return " ".join("".join(character.lower() if character.isalnum() else " " for character in value).split())


def recent_since(hours: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def load_destinations(platform: str) -> list[dict[str, str]]:
    profiles = load_json(PROFILES)["profiles"]
    seen: set[str] = set()
    destinations: list[dict[str, str]] = []
    for profile in profiles:
        target = profile.get(platform, {})
        key = str(target.get("url") or target.get("destination_id") or "").strip()
        if not key or key in seen or not target.get("ready_for_automation", True):
            continue
        seen.add(key)
        destinations.append({
            "site_key": str(profile["site_key"]),
            "url": str(target.get("url", "")),
            "secret_name": str(target.get("secret_name", "")),
            "destination_id": str(target.get("destination_id", "")),
        })
    return destinations


def select_offers(title: str, content: str, routing: dict[str, Any]) -> list[dict[str, Any]]:
    offers = load_json(OFFERS)["offers"]
    text = normalized(f"{title} {content}")
    selected: list[dict[str, Any]] = []
    for slot in routing["required_slots"]:
        candidates = [offer for offer in offers if offer.get("slot") == slot["slot"] and offer.get("url")]
        if slot["slot"].startswith("topic_"):
            candidates = [offer for offer in candidates if any(normalized(keyword) in text for keyword in offer.get("keywords", []))]
        if not candidates:
            raise ValueError(f"missing verified offer for {slot['slot']}")
        candidates.sort(key=lambda offer: hashlib.sha256(f"{title}:{offer['url']}".encode()).hexdigest())
        selected.append(candidates[0])
    return selected


def build_block(offers: list[dict[str, Any]]) -> str:
    cards = []
    for offer in offers:
        cards.append(
            "<li><a href=\"%s\" rel=\"sponsored nofollow noopener\" target=\"_blank\">%s</a></li>"
            % (html.escape(offer["url"], quote=True), html.escape(offer["title"]))
        )
    return "\n".join([MARKER, "<section class=\"london-affiliate-engine\"><h2>Helpful Korea picks</h2>", DISCLOSURE, "<ul>", *cards, "</ul></section>"])


def can_write(write_requested: bool) -> bool:
    return write_requested and os.getenv("AFFILIATE_WRITE_ENABLED", "").lower() == "true"


def wordpress(destination: dict[str, str], since: str, block_for, write: bool) -> list[dict[str, Any]]:
    password = os.getenv(destination["secret_name"], "")
    base = destination["url"].rstrip("/")
    response = requests.get(f"{base}/wp-json/wp/v2/posts", params={"after": since, "status": "publish", "per_page": 100}, timeout=30)
    response.raise_for_status()
    rows = []
    for post in response.json():
        content = post["content"]["rendered"]
        result = {"platform": "wordpress", "site": destination["site_key"], "post_id": post["id"], "url": post["link"], "action": "skipped"}
        if MARKER in content:
            result["reason"] = "already_processed"
        else:
            try:
                block = block_for(post["title"]["rendered"], content)
            except ValueError as exc:
                result["reason"] = str(exc)
            else:
                result["action"] = "would_append"
                if write:
                    if not password:
                        result.update(action="blocked", reason="missing_wordpress_secret")
                    else:
                        update = requests.post(f"{base}/wp-json/wp/v2/posts/{post['id']}", auth=(os.getenv("WP_USER", ""), password), json={"content": content + "\n" + block}, timeout=30)
                        update.raise_for_status()
                        result["action"] = "appended"
        rows.append(result)
    return rows


def blogger_token() -> str:
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.getenv("BLOGGER_GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("BLOGGER_GOOGLE_CLIENT_SECRET", ""),
        "refresh_token": os.getenv("BLOGGER_GOOGLE_REFRESH_TOKEN", ""),
        "grant_type": "refresh_token",
    }, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def blogger(destination: dict[str, str], since: str, block_for, write: bool) -> list[dict[str, Any]]:
    if not destination["destination_id"]:
        return []
    token = blogger_token() if write else ""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{destination['destination_id']}/posts"
    response = requests.get(endpoint, params={"publishedMin": since, "fetchBodies": "true", "maxResults": 100}, headers=headers, timeout=30)
    response.raise_for_status()
    rows = []
    for post in response.json().get("items", []):
        content = post["content"]
        result = {"platform": "blogger", "site": destination["site_key"], "post_id": post["id"], "url": post["url"], "action": "skipped"}
        if MARKER in content:
            result["reason"] = "already_processed"
        else:
            try:
                block = block_for(post["title"], content)
            except ValueError as exc:
                result["reason"] = str(exc)
            else:
                result["action"] = "would_append"
                if write:
                    update = requests.put(f"{endpoint}/{post['id']}", headers=headers, json={"title": post["title"], "content": content + "\n" + block}, timeout=30)
                    update.raise_for_status()
                    result["action"] = "appended"
        rows.append(result)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["wordpress", "blogger", "all"], default="all")
    parser.add_argument("--since-hours", type=int, default=36)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    routing = load_json(ROUTING)
    write = can_write(args.write)
    if args.write and not write:
        raise SystemExit("write blocked: set AFFILIATE_WRITE_ENABLED=true as a GitHub secret")
    since = recent_since(args.since_hours)
    block_for = lambda title, content: build_block(select_offers(title, content, routing))
    results: list[dict[str, Any]] = []
    if args.platform in {"wordpress", "all"}:
        for destination in load_destinations("wordpress"):
            try:
                results.extend(wordpress(destination, since, block_for, write))
            except requests.RequestException as exc:
                results.append({"platform": "wordpress", "site": destination["site_key"], "action": "blocked", "reason": type(exc).__name__})
    if args.platform in {"blogspot", "blogger", "all"}:
        for destination in load_destinations("blogspot"):
            try:
                results.extend(blogger(destination, since, block_for, write))
            except requests.RequestException as exc:
                results.append({"platform": "blogger", "site": destination["site_key"], "action": "blocked", "reason": type(exc).__name__})
    report = {"generated_at": datetime.now(UTC).isoformat(), "since": since, "write": write, "results": results}
    output = ENGINE / "reports" / "latest-new-content-run.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"write": write, "processed": len(results), "appended": sum(row["action"] == "appended" for row in results)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
