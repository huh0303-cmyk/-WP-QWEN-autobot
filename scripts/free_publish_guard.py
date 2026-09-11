"""Read-only publication limits; failed checks must never allow a write."""
from datetime import datetime, timedelta, timezone
import requests

KST = timezone(timedelta(hours=9))
DAILY_LIMIT = 1
HELD_BLOGGER_ID = "2234527810530371008"

def blogger_daily_gate(blog_id, token, site_url="", now=None):
    if str(blog_id) == HELD_BLOGGER_ID:
        return "destination_confirmation_required"
    if not str(blog_id).isdigit() or not token:
        return "credentials_missing"
    now = now or datetime.now(KST)
    start = now.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
        headers={"Authorization": "Bearer " + token},
        params={"status": "live", "startDate": start.isoformat(),
                "maxResults": DAILY_LIMIT, "fetchBodies": "false", "fields": "items(id,published)"}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or "error" in data:
        raise ValueError("Invalid Blogger publication inventory")
    return "daily_limit_reached" if len(data.get("items", [])) >= DAILY_LIMIT else ""
