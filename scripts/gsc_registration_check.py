#!/usr/bin/env python3
"""Read-only: which of the 27 WP sites + 33 Blogspot blogs are visible in Search Console to the service account.
Prints no secrets. Visibility != ownership by the user: a property missing here may still exist under another Google account."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import daily_site_traffic as d

token = d.get_gsc_token()
r = d.requests.get("https://www.googleapis.com/webmasters/v3/sites", headers={"Authorization": f"Bearer {token}"}, timeout=30)
r.raise_for_status()
have = {e["siteUrl"]: e.get("permissionLevel", "") for e in r.json().get("siteEntry", [])}
portfolio = json.load(open("config/blogger_portfolio.json", encoding="utf-8"))
cm = portfolio["custom_domain_policy"]["mappings"]
res = {"total_visible": len(have), "wp": {}, "blogspot": {}}
for u in d.WORDPRESS_SITES:
    dom = u.rstrip("/").replace("https://", "")
    p = f"sc-domain:{dom}"
    res["wp"][dom] = have.get(p) or have.get(u.rstrip("/") + "/") or ""
for c in portfolio["channels"]:
    base = cm.get(c["title"]) or c["blogspot"]
    host = base.rstrip("/").replace("https://", "")
    cands = [base.rstrip("/") + "/", f"sc-domain:{host}", "sc-domain:" + ".".join(host.split(".")[-2:])]
    level = next((have[x] for x in cands if x in have), "")
    res["blogspot"][f"{c['order']:02d} {c['title']} {host}"] = level
res["extra_unmatched"] = sorted(k for k in have if k not in {f"sc-domain:{x}" for x in res["wp"]} and not k.startswith("sc-domain:"))[:80]
json.dump(res, open("gsc_registration.json", "w"), ensure_ascii=False, indent=1)
for g in ("wp", "blogspot"):
    miss = [k for k, v in res[g].items() if not v]
    print(f"{g}: registered {len(res[g]) - len(miss)}/{len(res[g])}; missing={miss}")
print("levels:", {lv: sum(1 for g in ('wp','blogspot') for v in res[g].values() if v == lv) for lv in {v for g in ('wp','blogspot') for v in res[g].values()}})
