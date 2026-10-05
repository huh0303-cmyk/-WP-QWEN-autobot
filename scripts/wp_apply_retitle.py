#!/usr/bin/env python3
"""Apply config/wp_retitle_*.json: replace titles only (slug/body/status untouched).
Skips a post if its current raw title no longer equals "old" (someone changed it). Writes rollback log."""
import html, json, os, re, sys, requests


def norm(t):
    t = html.unescape(t or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", t).strip().lower()


MAP = sys.argv[1] if len(sys.argv) > 1 else "config/wp_retitle_2026-10-05.json"
USER = os.environ.get("WP_USER", "huh0303@gmail.com")
rows = json.load(open(MAP, encoding="utf-8"))
log, ok, skip, fail = [], 0, 0, 0
for r in rows:
    pw = os.environ.get(r["secret"], "").strip()
    ep = f"{r['url'].rstrip('/')}/wp-json/wp/v2/posts/{r['id']}"
    try:
        cur = requests.get(ep, params={"context": "edit"}, auth=(USER, pw), timeout=30)
        cur.raise_for_status()
        j = cur.json()
        raw = j.get("title", {}).get("raw", "")
        if raw == r["new"] or r["old"] == r["new"]:
            skip += 1; continue
        if norm(raw) != norm(r["old"]):
            print("SKIP changed", r["site"], r["id"], raw[:60]); skip += 1; continue
        if "unlock" in r["new"].lower():
            raise ValueError("banned word")
        res = requests.post(ep, json={"title": r["new"]}, auth=(USER, pw), timeout=30)
        res.raise_for_status()
        k = res.json()
        assert k["slug"] == j["slug"] and k["status"] == j["status"]
        log.append({"site": r["site"], "id": r["id"], "old": raw, "new": r["new"]}); ok += 1
    except Exception as e:
        fail += 1; print("FAIL", r["site"], r["id"], e)
os.makedirs("logs", exist_ok=True)
json.dump(log, open("logs/wp_retitle_rollback_2026-10-05.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print({"ok": ok, "skipped": skip, "failed": fail})
sys.exit(1 if fail else 0)
