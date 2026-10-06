#!/usr/bin/env python3
"""Read-only: public uploads per channel since a date (YouTube Data API, public key)."""
import json, os, urllib.parse, urllib.request
K = os.environ["YOUTUBE_API_KEY"]
SINCE = os.environ.get("SINCE", "2026-09-29T00:00:00Z")
CH = {"cafe_romantic":"UCbJfEtsffpgI5MsKkB7BYvQ","cafe_healing1":"UC7yEsLM-HoXudngrD-4FIqg","Starbucksvibes":"UC_e-sbLkVgwJNYEeobolNog","cafe_mozart":"UC7jOhyMa-FIrzZuea97z1Pw","kpop_studio7":"UCKZsfAWyCmY0jckf4IWZrqw","NASA_XFILES":"UCtNLZO07Oh3UnXPI2CjOgNg","HISTORY_TV_TODAY":"UCVBvZwodUF4s57KeNicxQ3w","INVENTION_STORY1":"UCgNj-yS93A_fOHXXvG49fww","OLD_HOLLYWOOD1":"UCLvy6kSpC8-7o3hnSrfQ47g","RETRO_USA1":"UCwh49EokdWFJqYFE_zA6XDQ","KoreanSurvival":"UC4n-HHAED1mBKcU6x-Row2Q","Japanese":"UCOWoNH_d6p45ywQ6W0Z1Jng","German":"UCKF98zgzm7YRWlyMaoJJKIQ","French":"UCmt8f9yUT6iTxBys8eH4-Cg","Italian":"UCK8B-BM09Cz-ockaQYLL5LA","Spanish":"UC9mvVEdL9Tllkit5v2Qv8UQ","Chinese":"UCGTd7RhfaUaGGbVRsNPUN6Q","Portuguese":"UCKvKhETLGPaRV3qfWv2bM2g","Vietnamese":"UCRZ0uc_bxKDMwz3noBBi9KQ","English":"UCrjkKWMHzAAvpLIFgHnwcWg","seoul_topik1":"UCdA24IuR-JE7qButWv5jLqA","Health_JP":"UCC_PcHMv-Uxpr00Pjw_J2Wg","Health_USA":"UC91BpNSb4nUwD6jrpthK7FQ","jisoopicks":"UCAizx0tPkRSol8sIhanN_QQ"}
for n, c in CH.items():
    u = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode({"part": "snippet", "channelId": c, "order": "date", "type": "video", "maxResults": 25, "publishedAfter": SINCE, "key": K})
    try:
        items = json.load(urllib.request.urlopen(u, timeout=25)).get("items", [])
        days = sorted(i["snippet"]["publishedAt"][:10] for i in items)
        print(f"{n:17} {len(days):2} {days}")
        for i in items[:2]:
            print("      ", i["snippet"]["publishedAt"][:16], i["snippet"]["title"][:70])
    except Exception as e:
        print(n, "ERR", str(e)[:80])
