import json, os, random, re, requests
log = [x for x in json.load(open("data/add_images_log_2026-10-06.json", encoding="utf-8")) if x.get("status") == "updated" and str(x.get("photo", "")).startswith("Pexels:")]
random.seed(7); sample = random.sample(log, min(150, len(log)))
key = os.environ["PEXELS_API_KEY"]
STOP = set("a an the of in on and with to for korea korean south your how what guide".split())
W = lambda s: {w.rstrip("s") for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in STOP}
for x in sample:
    pid = x["photo"].split(":")[1]
    r = requests.get(f"https://api.pexels.com/v1/photos/{pid}", headers={"Authorization": key}, timeout=20)
    alt = r.json().get("alt", "") if r.ok else f"HTTP{r.status_code}"
    print(f"{x['site']}|{x['id']}|T: {x['title'][:60]}|Q: {x['query']}|ALT: {alt[:90]}", flush=True)
