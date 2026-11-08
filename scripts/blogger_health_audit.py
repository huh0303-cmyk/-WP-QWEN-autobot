#!/usr/bin/env python3
"""Read-only Blogger public feed audit. No API keys, login or publishing permissions."""
import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATOM = "{http://www.w3.org/2005/Atom}"
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Korea365-FeedAudit/1.0"})
    with urllib.request.urlopen(req, timeout=18) as response:
        return response.read()
def parse_date(value):
    return dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
def audit(row):
    now = dt.datetime.now(dt.timezone.utc)
    result = {"checked_at": now.isoformat(), "status": "unavailable", "posts_checked": 0}
    base = row["url"].rstrip("/")
    posts = []
    try:
        for start in (1, 101):
            url = base + "/feeds/posts/default?" + urllib.parse.urlencode({"alt":"atom","max-results":100,"start-index":start})
            root = ET.fromstring(get(url))
            entries = root.findall(ATOM+"entry")
            for entry in entries:
                title = entry.findtext(ATOM+"title", default="")
                published = entry.findtext(ATOM+"published", default="")
                if published:
                    posts.append((title, parse_date(published)))
            if len(entries) < 100:
                break
            time.sleep(0.4)
        if not posts:
            result["status"] = "empty"
            result["posts_7d"] = 0
            result["duplicate_titles"] = 0
            return result
        titles = Counter(re.sub(r"[^\w]+", "", title.casefold()) for title, _ in posts)
        result.update({
            "status": "ok",
            "posts_checked": len(posts),
            "posts_7d": sum(0 <= (now - published).total_seconds() < 7*86400 for _, published in posts),
            "latest_publish_date": max(published for _, published in posts).date().isoformat(),
            "days_since_publish": (now.date() - max(published for _, published in posts).date()).days,
            "duplicate_titles": sum(n-1 for n in titles.values() if n > 1),
            "duplicate_scope": "recent_200_posts",
        })
    except (urllib.error.URLError, TimeoutError, ValueError, ET.ParseError, OSError) as exc:
        result["error"] = str(exc)[:160]
    return result
def main():
    rows = json.loads((ROOT/"docs/dashboard.json").read_text(encoding="utf-8")).get("rows", [])
    data = {}
    for row in rows:
        if str(row.get("platform","")).lower() != "blogspot":
            continue
        data[row["site"]] = audit(row)
        time.sleep(0.5)
    out = {"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source":"public Blogger Atom feed; last 200 posts","sites":data}
    (ROOT/"docs/blogger_health.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Blogger audited:",len(data),"OK:",sum(x["status"]=="ok" for x in data.values()))
if __name__=="__main__":
    main()
