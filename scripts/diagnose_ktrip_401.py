import os, json, requests
WP_USER = "huh0303@gmail.com"
SITE = "https://k-trip365.com"
pw = os.getenv("KTRIP365COM", "")
MARKER = 'class="related-links"'
total = with_block = 0
page = 1
while True:
    r = requests.get(f"{SITE}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 50, "page": page, "status": "publish",
                              "_fields": "id,content"}, timeout=25)
    if r.status_code != 200:
        break
    batch = r.json()
    if not batch:
        break
    for p in batch:
        total += 1
        if MARKER in p.get("content", {}).get("rendered", ""):
            with_block += 1
    if len(batch) < 50:
        break
    page += 1
result = {"site": SITE, "total": total, "with_block": with_block}
with open("verify_ktrip_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
