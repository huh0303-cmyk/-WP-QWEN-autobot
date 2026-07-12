import os, json, time, requests
WP_USER = "huh0303@gmail.com"
SITE = "https://k-trip365.com"
pw = os.getenv("KTRIP365COM", "")
MARKER = 'class="related-links"'
total = with_block = 0
page = 1
error = None
try:
    while True:
        for attempt in range(3):
            try:
                r = requests.get(f"{SITE}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                                  params={"per_page": 20, "page": page, "status": "publish",
                                          "_fields": "id,content"}, timeout=40)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(5)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            total += 1
            if MARKER in p.get("content", {}).get("rendered", ""):
                with_block += 1
        if len(batch) < 20:
            break
        page += 1
        time.sleep(1)
except Exception as e:
    error = str(e)

result = {"site": SITE, "total": total, "with_block": with_block, "error": error}
with open("verify_ktrip_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
