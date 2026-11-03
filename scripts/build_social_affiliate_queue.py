#!/usr/bin/env python3
"""Build a receipt-oriented 10-link affiliate distribution queue for social/video content.

This module never publishes. It validates destination-specific catalogs and emits
one independently retryable job per destination. Platform adapters consume this
manifest only after OAuth scopes and live-write approval are configured.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "config/affiliate_distribution_policy.json").read_text(encoding="utf-8-sig"))
YT = json.loads((ROOT / "config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json").read_text(encoding="utf-8-sig"))
SNS = json.loads((ROOT / "config/sns_six_channel_policy.json").read_text(encoding="utf-8-sig"))
CATALOGS = ROOT / "affiliate-engine" / "data" / "catalogs"
EXPECTED = POLICY["provider_allocation"]
MARKER = "london-omnichannel-social-v1"

PLACEMENTS = {
    "youtube": ["video_description", "pinned_comment"],
    "tiktok": ["supported_product_links", "profile_bio_link", "caption_if_clickable_and_allowed"],
    "instagram": ["profile_link", "story_link_sticker", "caption_if_clickable_and_allowed"],
    "threads": ["post_body_links", "profile_link"],
    "facebook": ["page_post_links", "page_link"],
}

def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

def valid_https(value: object) -> bool:
    try:
        u = urlparse(str(value or ""))
        return u.scheme == "https" and bool(u.netloc)
    except Exception:
        return False

def validate_catalog(catalog_key: str) -> tuple[list[dict], list[str]]:
    path = CATALOGS / f"{catalog_key}.json"
    if not path.exists():
        return [], [f"catalog_missing:{catalog_key}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return [], [f"catalog_invalid_json:{catalog_key}"]
    offers = data.get("offers", [])
    errors = []
    if data.get("status") not in {"ready", "verified"}:
        errors.append("catalog_not_ready")
    if len(offers) != 10:
        errors.append(f"expected_10_offers_got_{len(offers)}")
    counts = Counter()
    seen = set()
    for offer in offers:
        provider = offer.get("provider")
        if provider not in EXPECTED:
            errors.append("unknown_provider")
            continue
        if offer.get("affiliate_link_verified") is not True:
            errors.append(f"unverified_tracking_link:{offer.get('slot','unknown')}")
        if not valid_https(offer.get("url")):
            errors.append(f"invalid_tracking_url:{offer.get('slot','unknown')}")
        if offer.get("image_rights_verified") is not True or not valid_https(offer.get("image_url")):
            errors.append(f"unverified_image:{offer.get('slot','unknown')}")
        if not offer.get("title") or not offer.get("slot"):
            errors.append("missing_offer_title_or_slot")
        if offer.get("url") in seen:
            errors.append("duplicate_tracking_url")
        seen.add(offer.get("url"))
        counts[provider] += 1
    if dict(counts) != EXPECTED:
        errors.append(f"provider_mix_mismatch:{dict(counts)}")
    return offers, sorted(set(errors))

def youtube_destinations():
    rows = []
    for group, channels in YT.get("groups", {}).items():
        for channel in channels:
            rows.append({
                "platform": "youtube", "destination_key": channel.get("key", ""),
                "display_name": channel.get("title", ""), "channel_id": channel.get("channel_id"),
                "identity_verified": bool(channel.get("verified")),
                "publish_connected": False,
                "catalog_key": f"youtube_{channel.get('key','')}",
                "group": group,
            })
    for channel in YT.get("planned_shopping_slots", []):
        rows.append({
            "platform": "youtube", "destination_key": channel.get("key", ""),
            "display_name": channel.get("display_name", ""), "channel_id": channel.get("channel_id"),
            "identity_verified": False, "publish_connected": False,
            "catalog_key": f"youtube_{channel.get('key','')}", "group": "planned",
        })
    return rows

def social_destinations():
    rows = []
    for account in SNS.get("accounts", []):
        platform = slug(account.get("platform", ""))
        role = account.get("role", "")
        rows.append({
            "platform": platform, "destination_key": f"{platform}_{role}",
            "display_name": account.get("display_name", ""),
            "account_url": account.get("url", ""),
            "account_exists": account.get("account_exists") is True,
            "identity_verified": account.get("identity_verified") is True,
            "publish_connected": account.get("publish_connected") is True,
            "catalog_key": f"sns_{platform}_{role}",
        })
    return rows

def build_job(destination: dict, content: dict) -> dict:
    offers, errors = validate_catalog(destination["catalog_key"])
    if destination["platform"] == "youtube" and not destination.get("channel_id"):
        errors.append("youtube_channel_id_missing")
    if destination["platform"] != "youtube" and not destination.get("account_exists"):
        errors.append("social_account_not_created_or_verified")
    if not destination.get("identity_verified"):
        errors.append("destination_identity_not_verified")
    if not destination.get("publish_connected"):
        errors.append("publish_oauth_not_connected")
    links = [{"slot": o.get("slot"), "provider": o.get("provider"),
              "title": o.get("title"), "url": o.get("url")} for o in offers]
    job_id = f"{destination['platform']}:{destination['destination_key']}:{content.get('content_id','manual')}"
    return {
        "job_id": job_id, "marker": MARKER,
        "platform": destination["platform"], "destination": destination,
        "content": content, "affiliate_links": links,
        "affiliate_link_count": len(links),
        "provider_counts": dict(Counter(x.get("provider") for x in links)),
        "supported_placements": PLACEMENTS[destination["platform"]],
        "status": "blocked" if errors else "ready_for_platform_adapter",
        "blockers": sorted(set(errors)),
        "publish_attempted": False, "receipt": None,
        "retry_scope": "this_destination_only",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", default="manual-preview")
    parser.add_argument("--title", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--mode", choices=["new", "backfill"], default="new")
    args = parser.parse_args()
    content = {"content_id": args.content_id, "title": args.title, "url": args.url,
               "summary": args.summary, "mode": args.mode}
    destinations = youtube_destinations() + social_destinations()
    jobs = [build_job(d, content) for d in destinations]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {"per_content_total": 10, "provider_allocation": EXPECTED},
        "source_content": content,
        "scope": {"youtube_registry": len([x for x in destinations if x["platform"] == "youtube"]),
                  "social_accounts_listed": len([x for x in destinations if x["platform"] != "youtube"])},
        "jobs_total": len(jobs),
        "ready_for_adapter": sum(j["status"] == "ready_for_platform_adapter" for j in jobs),
        "blocked": sum(j["status"] == "blocked" for j in jobs),
        "publish_attempted": False,
        "jobs": jobs,
    }
    out = ROOT / "reports" / "social-affiliate-distribution-queue.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("jobs_total", "ready_for_adapter", "blocked", "publish_attempted", "scope")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
