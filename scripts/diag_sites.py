import requests, time

SITES = ["https://kworld365.com", "https://jobkoreaglobal.com", "https://k-trip365.com"]

for site in SITES:
    print(f"\n=== {site} ===")
    for i in range(4):
        try:
            t0 = time.time()
            r = requests.get(f"{site}/wp-json/wp/v2/posts", params={"per_page": 1}, timeout=15)
            print(f"  [{i+1}] HTTP {r.status_code} - {time.time()-t0:.2f}s")
        except Exception as e:
            print(f"  [{i+1}] ERROR: {type(e).__name__}: {str(e)[:150]}")
        time.sleep(1)
