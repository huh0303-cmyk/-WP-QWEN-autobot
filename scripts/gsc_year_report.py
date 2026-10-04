#!/usr/bin/env python3
"""One-off: Google Search Console clicks/impressions per site for the last ~12 months (monthly).
Read-only. Used for the keep/drop-domain decision (2026-10-04). Prints a table; never prints secrets."""
import json, os, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import daily_site_traffic as d  # reuses get_gsc_token / gsc_post

KST = timezone(timedelta(hours=9))
end = datetime.now(KST).date() - timedelta(days=3)
start = end - timedelta(days=395)
token = d.get_gsc_token()
out = {}
for site_url in d.WORDPRESS_SITES:
    domain = site_url.rstrip("/").replace("https://", "")
    prop = f"sc-domain:{domain}"
    ep = f"/sites/{d.requests.utils.quote(prop, safe='')}/searchAnalytics/query"
    r = d.gsc_post(token, ep, {"startDate": start.isoformat(), "endDate": end.isoformat(),
                               "dimensions": ["date"], "rowLimit": 25000})
    if r.status_code != 200:
        out[domain] = {"error": f"HTTP {r.status_code} {r.text[:80]}"}
        continue
    months = defaultdict(lambda: [0, 0])
    tc = ti = 0; pos_w = 0.0; last28c = last28i = 0; first = None
    cutoff = (end - timedelta(days=27)).isoformat()
    for row in r.json().get("rows", []):
        day = row["keys"][0]; c = row.get("clicks", 0); i = row.get("impressions", 0)
        months[day[:7]][0] += c; months[day[:7]][1] += i
        tc += c; ti += i; pos_w += row.get("position", 0) * i
        if day >= cutoff: last28c += c; last28i += i
        if (c or i) and (first is None or day < first): first = day
    out[domain] = {"clicks": tc, "impr": ti, "pos": round(pos_w / ti, 1) if ti else None,
                   "first_data": first, "c28": last28c, "i28": last28i,
                   "months": {k: v for k, v in sorted(months.items())}}
json.dump({"range": [start.isoformat(), end.isoformat()], "sites": out},
          open("gsc_year_report.json", "w"), ensure_ascii=False, indent=1)
rows = sorted(out.items(), key=lambda kv: -(kv[1].get("clicks", 0) * 1000 + kv[1].get("impr", 0)))
print(f"range {start}..{end}")
print(f"{'domain':26}{'clicks':>8}{'impr':>9}{'pos':>6}{'c28':>6}{'i28':>7}  first_data")
for dom, v in rows:
    if "error" in v: print(f"{dom:26} {v['error']}"); continue
    print(f"{dom:26}{v['clicks']:>8}{v['impr']:>9}{str(v['pos']):>6}{v['c28']:>6}{v['i28']:>7}  {v['first_data']}")
print("MONTHLY theseouljournal.com:", json.dumps(out.get("theseouljournal.com", {}).get("months", {})))
print("MONTHLY koreanews365.com:", json.dumps(out.get("koreanews365.com", {}).get("months", {})))
