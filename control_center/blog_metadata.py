from __future__ import annotations

import json
import socket
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]

DOMAIN_PAYMENT_OVERRIDES = {
    "kworld365.com": {"provider": "Gabia", "payment_date": "2026-08-02"},
    "kskin365.com": {"provider": "Gabia", "payment_date": "2026-08-24"},
    "jobkoreaglobal.com": {"provider": "Gabia", "payment_date": "2026-08-22"},
    "korea365.org": {"provider": "Gabia", "payment_date": "2026-09-09"},
}

HOSTING_OVERRIDES = {
    "ki-korea.com": {
        "provider": "Hostinger",
        "payment_date": "2026-02-21",
        "renewal_date": "2027-02-21",
        "plan": "Business Web Hosting (1 year)",
    },
}

PLATFORM_HOSTING = {
    "blogspot": ("Google Blogger", "플랫폼 포함"),
    "naver": ("Naver Blog", "플랫폼 포함"),
    "tistory": ("Tistory", "플랫폼 포함"),
}


def _domain_from_url(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


@lru_cache(maxsize=128)
def _rdap(domain: str, day_bucket: int) -> dict[str, str]:
    del day_bucket
    try:
        response = requests.get(f"https://rdap.org/domain/{domain}", timeout=12, headers={"User-Agent": "Korea365-Control/1.0"})
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return {}
    registrar = ""
    for entity in payload.get("entities", []):
        if "registrar" not in entity.get("roles", []):
            continue
        try:
            for item in entity.get("vcardArray", [None, []])[1]:
                if item and item[0] == "fn":
                    registrar = str(item[3])
                    break
        except Exception:
            pass
        if registrar:
            break
    expiry = ""
    for event in payload.get("events", []):
        if event.get("eventAction") == "expiration":
            expiry = str(event.get("eventDate") or "")[:10]
            break
    return {"provider": registrar, "renewal_date": expiry}


def domain_info(url: str, platform: str) -> dict[str, str]:
    domain = _domain_from_url(url)
    if platform in PLATFORM_HOSTING:
        provider, note = PLATFORM_HOSTING[platform]
        return {"provider": provider, "payment_date": note, "renewal_date": note}
    data = dict(_rdap(domain, int(time.time() // 86400)))
    data.update({k: v for k, v in DOMAIN_PAYMENT_OVERRIDES.get(domain, {}).items() if v})
    return data


def hosting_info(url: str, platform: str) -> dict[str, str]:
    domain = _domain_from_url(url)
    if platform in PLATFORM_HOSTING:
        provider, note = PLATFORM_HOSTING[platform]
        return {"provider": provider, "payment_date": note, "renewal_date": note}
    if domain in HOSTING_OVERRIDES:
        return dict(HOSTING_OVERRIDES[domain])
    try:
        ip = socket.gethostbyname(domain)
    except OSError:
        return {}
    # Current WordPress addresses resolve inside Hostinger AS47583 ranges.
    hostinger_prefixes = ("151.106.", "147.93.", "213.210.", "187.127.", "195.35.", "82.180.", "31.220.")
    provider = "Hostinger" if ip.startswith(hostinger_prefixes) else ""
    return {"provider": provider, "payment_date": "", "renewal_date": "", "ip": ip}


def revenue_info(domain: str, row: dict) -> dict[str, object]:
    history_path = ROOT / "situation_room_history.json"
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = {}
    if domain == "k-health365.com":
        latest = history.get("latest", {}).get("adsense_khealth365", {})
        previous = history.get("previous", {}).get("adsense_khealth365", {})
        current = latest.get("today")
        old = previous.get("today")
        delta = current - old if isinstance(current, (int, float)) and isinstance(old, (int, float)) else None
        return {
            "monetized": True,
            "amount": current,
            "delta": delta,
            "currency": latest.get("currency") or "KRW",
            "status": latest.get("status") or row.get("adsense_status_label") or "AdSense",
        }
    if row.get("google_approved"):
        return {"monetized": True, "amount": None, "delta": None, "currency": "", "status": row.get("adsense_status_label") or "AdSense 승인"}
    return {"monetized": False, "amount": None, "delta": None, "currency": "", "status": row.get("adsense_status_label") or "미수익화"}


def editorial_metadata(row: dict) -> tuple[str, list[str]]:
    topic = str(row.get("category") or row.get("topic") or "").strip()
    categories: list[str] = []
    for item in row.get("official_categories") or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if name and name not in categories:
            categories.append(name)
    if not categories and topic:
        categories = [topic]
    return topic, categories[:5]
