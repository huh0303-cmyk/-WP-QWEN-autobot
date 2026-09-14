import os, re, requests

SITE_URL = "https://k-trip365.com"
WP_USER = "huh0303@gmail.com"
pw = os.environ.get("KTRIP365COM")
auth = requests.auth.HTTPBasicAuth(WP_USER, pw)

_LOG = []
def log(m):
    print(m)
    _LOG.append(str(m))

GENERIC_SLUG_PATTERN = re.compile(r"^post-\d+$")
MIN_CONTENT_CHARS = 2500

posts = []
page = 1
while True:
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts", auth=auth,
                      params={"per_page": 50, "page": page, "status": "publish",
                              "_fields": "id,slug,title,content"}, timeout=25)
    if r.status_code != 200:
        break
    batch = r.json()
    if not batch:
        break
    posts.extend(batch)
    if len(batch) < 50:
        break
    page += 1

title_seen = {}
for p in posts:
    title = p.get("title", {}).get("rendered", "")
    html = p.get("content", {}).get("rendered", "")
    chars = len(re.sub(r"<[^>]+>", "", html).strip())
    reasons = []
    if GENERIC_SLUG_PATTERN.match(p.get("slug","")):
        reasons.append("dummy")
    key = title.strip().lower()
    if key in title_seen:
        reasons.append(f"dup_of_{title_seen[key]}")
    else:
        title_seen[key] = p["id"]
    if chars < MIN_CONTENT_CHARS:
        reasons.append(f"short_{chars}")
    if reasons:
        log(f"CANDIDATE #{p['id']} slug={p.get('slug')} reasons={reasons} title={title[:40]}")
        dr = requests.delete(f"{SITE_URL}/wp-json/wp/v2/posts/{p['id']}", auth=auth, timeout=20)
        log(f"  DELETE attempt -> status={dr.status_code} body={dr.text[:300]}")

with open("ktrip_debug_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
