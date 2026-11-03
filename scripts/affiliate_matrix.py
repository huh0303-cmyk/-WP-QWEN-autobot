#!/usr/bin/env python3
"""Four-network affiliate card engine for WordPress and Blogger.

Catalog contract: data/affiliate/{site_key}-affiliate-matrix.json
Each site owns exactly 10 verified offers per provider (40 cards total).
Preview is read-only; writes require --confirm APPLY-AFFILIATE-MATRIX and
AFFILIATE_MATRIX_WRITE_ENABLED=true.
"""
from __future__ import annotations
import argparse, html, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
import requests

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "automation_hub_sites.json"
PROFILES = ROOT / "config" / "content_engine_profiles.json"
CATALOG_DIR = ROOT / "data" / "affiliate"
EXCLUDED_WORDPRESS_SITE_IDS = {"wp_khealth365", "wp_krealestate", "wp_kworld365", "wp_oliveyoung", "wp_ksa"}
REPORT = ROOT / "reports" / "affiliate-matrix-latest.json"
PROVIDERS = ("coupang_partners", "agoda", "trip_com", "olive_young_global")
LABELS = {"coupang_partners":"Coupang Partners","agoda":"Agoda","trip_com":"Trip.com","olive_young_global":"Olive Young"}
START = "<!-- london-affiliate-matrix:v1:start -->"
END = "<!-- london-affiliate-matrix:v1:end -->"
DISCLOSURE = "This article contains affiliate links. We may earn a commission if you make a qualifying purchase, at no additional cost to you."

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def site_key(site_id: str) -> str:
    return site_id.split("_", 1)[-1] if "_" in site_id else site_id

def valid_https(value: str) -> bool:
    try:
        u = urlparse(str(value or "").strip())
        return u.scheme == "https" and bool(u.netloc) and not u.username and not u.password
    except Exception:
        return False

def load_catalog(site_id: str):
    path = CATALOG_DIR / f"{site_id}-affiliate-matrix.json"
    if not path.exists():
        raise ValueError(f"missing site-specific catalog: {path.name}")
    data = read_json(path)
    if data.get("site_id") != site_id or data.get("status") not in ("verified", "ready"):
        raise ValueError("catalog site_id mismatch or status is not verified/ready")
    by_provider = {p: [] for p in PROVIDERS}
    seen_ids, seen_urls = set(), set()
    for item in data.get("products", []):
        provider = item.get("provider")
        if provider not in by_provider: continue
        if not item.get("affiliate_link_verified") or not item.get("image_rights_verified"): continue
        if not valid_https(item.get("tracking_url")) or not valid_https(item.get("image_url")): continue
        pid, url = str(item.get("id","")).strip(), item.get("tracking_url","").strip()
        if not pid or not item.get("title") or pid in seen_ids or url in seen_urls: continue
        seen_ids.add(pid); seen_urls.add(url); by_provider[provider].append(item)
    counts = {p:len(items) for p,items in by_provider.items()}
    if any(counts[p] != 10 for p in PROVIDERS):
        raise ValueError("need exactly 10 unique verified offers per provider; counts="+json.dumps(counts))
    return by_provider

def make_cards(catalog):
    out = [START, '<style>.affiliate-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:12px 0 24px}.affiliate-card{min-width:0;border:1px solid #e5e7eb;border-radius:10px;padding:10px}.affiliate-card a{display:flex;flex-direction:column;gap:8px;text-decoration:none}.affiliate-card img{display:block;width:100%;height:170px;object-fit:contain}.affiliate-title{font-weight:600;line-height:1.4}.affiliate-cta{display:inline-block;text-align:center;padding:8px 10px;border-radius:6px;background:#102a43;color:#fff}@media(max-width:640px){.affiliate-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.affiliate-card img{height:130px}}</style>',
           '<section class="london-affiliate-matrix" aria-label="Affiliate recommendations">',
           '<p class="affiliate-disclosure"><small>'+html.escape(DISCLOSURE)+'</small></p>']
    for provider in PROVIDERS:
        out.append(f'<h3>{html.escape(LABELS[provider])}</h3><div class="affiliate-grid">')
        for item in catalog[provider]:
            title = html.escape(str(item["title"]), quote=True)
            href = html.escape(item["tracking_url"].strip(), quote=True)
            src = html.escape(item["image_url"].strip(), quote=True)
            alt = html.escape(str(item.get("image_alt") or item["title"]), quote=True)
            out.append('<article class="affiliate-card"><a href="'+href+'" rel="sponsored nofollow noopener" target="_blank">'
                       '<img src="'+src+'" alt="'+alt+'" loading="lazy" decoding="async">'
                       '<span class="affiliate-title">'+title+'</span><span class="affiliate-cta">View offer</span></a></article>')
        out.append("</div>")
    out.extend(["</section>", END])
    return "\n".join(out)

def insert_block(content: str, block: str) -> str:
    if START in content and END in content:
        return re.sub(re.escape(START)+r".*?"+re.escape(END), lambda _:block, content, count=1, flags=re.S)
    if START in content or END in content:
        raise ValueError("incomplete affiliate marker found; manual review required")
    return content.rstrip()+"\n\n"+block+"\n"

def wp_auth(site, credentials):
    row = credentials.get(site["site_id"]) or credentials.get(site.get("secret_name","")) or {}
    user = row.get("username") or row.get("user")
    password = row.get("app_password") or row.get("password")
    return (user,password) if user and password else None

def wp_posts(session, base, scope, since, limit):
    page, emitted = 1, 0
    while emitted < limit:
        size = min(100, limit-emitted)
        params = {"status":"publish","per_page":size,"page":page,"context":"edit",
                  "_fields":"id,link,title,content,status,date,modified"}
        if scope == "new": params["after"] = since
        r = session.get(base+"/wp-json/wp/v2/posts",params=params,timeout=60)
        if r.status_code == 400 and page > 1: break
        r.raise_for_status(); batch = r.json()
        if not batch: break
        for post in batch:
            emitted += 1; yield post
            if emitted >= limit: break
        if scope == "new" or len(batch) < size: break
        page += 1

def blogger_token():
    keys = ("BLOGGER_GOOGLE_CLIENT_ID","BLOGGER_GOOGLE_CLIENT_SECRET","BLOGGER_GOOGLE_REFRESH_TOKEN")
    vals = [os.getenv(k,"") for k in keys]
    if not all(vals): raise ValueError("missing Blogger OAuth secrets")
    r = requests.post("https://oauth2.googleapis.com/token",data={"client_id":vals[0],"client_secret":vals[1],
        "refresh_token":vals[2],"grant_type":"refresh_token"},timeout=30)
    r.raise_for_status(); return r.json()["access_token"]

def blogger_posts(session, blog_id, token, scope, since, limit):
    endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
    page_token, emitted = "", 0
    while emitted < limit:
        size = min(100,limit-emitted); params = {"fetchBodies":"true","maxResults":size,"status":["live"]}
        if scope == "new": params["startDate"] = since
        if page_token: params["pageToken"] = page_token
        r = session.get(endpoint,params=params,headers={"Authorization":f"Bearer {token}"},timeout=60)
        r.raise_for_status(); payload = r.json(); batch = payload.get("items",[])
        for post in batch:
            emitted += 1; yield post
            if emitted >= limit: break
        page_token = payload.get("nextPageToken","")
        if scope == "new" or not page_token: break

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode",choices=("preview","apply"),default="preview")
    ap.add_argument("--platform",choices=("all","wordpress","blogger"),default="all")
    ap.add_argument("--site-id",default="")
    ap.add_argument("--scope",choices=("new","backfill"),default="backfill")
    ap.add_argument("--limit-per-site",type=int,default=0)
    ap.add_argument("--confirm",default="")
    args = ap.parse_args()
    if args.mode == "apply" and (args.confirm != "APPLY-AFFILIATE-MATRIX" or os.getenv("AFFILIATE_MATRIX_WRITE_ENABLED","").lower() != "true"):
        raise SystemExit("apply blocked: require --confirm APPLY-AFFILIATE-MATRIX and AFFILIATE_MATRIX_WRITE_ENABLED=true")
    limit = args.limit_per_site if args.limit_per_site > 0 else 10**9
    registry = read_json(REGISTRY).get("sites",[])
    profiles = {p["site_key"]:p for p in read_json(PROFILES).get("profiles",[])}
    try: credentials = json.loads(os.getenv("WP_SITE_CREDENTIALS_JSON","{}"))
    except json.JSONDecodeError: raise SystemExit("WP_SITE_CREDENTIALS_JSON is invalid JSON")
    session = requests.Session()
    token = None
    since = (datetime.now(timezone.utc)-timedelta(hours=36)).isoformat().replace("+00:00","Z")
    report = {"mode":args.mode,"scope":args.scope,"platform":args.platform,"started_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
              "totals":{"sites":0,"catalog_ready":0,"posts_seen":0,"would_update":0,"updated":0,"already_current":0,"blocked":0},"sites":[]}
    for site in registry:
        sid, platform = site.get("site_id",""),site.get("platform","")
        if not site.get("enabled",True) or (platform == "wordpress" and sid in EXCLUDED_WORDPRESS_SITE_IDS) or (args.site_id and sid != args.site_id): continue
        if args.platform != "all" and platform != args.platform: continue
        if platform not in ("wordpress","blogger"): continue
        row = {"site_id":sid,"platform":platform,"posts_seen":0,"would_update":0,"updated":0,"already_current":0,"errors":[]}
        report["totals"]["sites"] += 1
        try:
            catalog = load_catalog(sid); block = make_cards(catalog); report["totals"]["catalog_ready"] += 1
            if platform == "wordpress":
                auth = wp_auth(site,credentials)
                if not auth: raise ValueError("missing WordPress credentials in WP_SITE_CREDENTIALS_JSON")
                base = site["url"].rstrip("/"); s = requests.Session(); s.auth = auth
                for post in wp_posts(s,base,args.scope,since,limit):
                    raw = post.get("content",{}).get("raw")
                    if raw is None: raise ValueError(f"post {post.get('id')}: edit-context raw content unavailable")
                    new = insert_block(raw,block); row["posts_seen"] += 1
                    if new == raw: row["already_current"] += 1; continue
                    row["would_update"] += 1
                    if args.mode == "apply":
                        endpoint = f"{base}/wp-json/wp/v2/posts/{post['id']}"
                        put = s.post(endpoint,json={"content":new},timeout=60); put.raise_for_status()
                        check = s.get(endpoint,params={"context":"edit","_fields":"id,content,status,date"},timeout=60); check.raise_for_status()
                        verified = check.json().get("content",{}).get("raw","")
                        if START not in verified or END not in verified or verified.count('class="affiliate-card"') != 40:
                            raise ValueError(f"post {post['id']}: read-back validation failed")
                        row["updated"] += 1
            else:
                profile = profiles.get(site_key(sid),{})
                blog_id = str(site.get("destination_id") or profile.get("blogspot",{}).get("destination_id") or "")
                if not blog_id: raise ValueError("Blogger blog ID missing")
                if token is None: token = blogger_token()
                endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
                for post in blogger_posts(session,blog_id,token,args.scope,since,limit):
                    raw = post.get("content",""); new = insert_block(raw,block); row["posts_seen"] += 1
                    if new == raw: row["already_current"] += 1; continue
                    row["would_update"] += 1
                    if args.mode == "apply":
                        put = session.put(endpoint+"/"+str(post["id"]),params={"fetchBody":"true"},
                            headers={"Authorization":f"Bearer {token}"},json={"title":post["title"],"content":new},timeout=60)
                        put.raise_for_status()
                        check = session.get(endpoint+"/"+str(post["id"]),params={"view":"ADMIN"},
                            headers={"Authorization":f"Bearer {token}"},timeout=60); check.raise_for_status()
                        verified = check.json().get("content","")
                        if START not in verified or END not in verified or verified.count('class="affiliate-card"') != 40:
                            raise ValueError(f"Blogger post {post['id']}: read-back validation failed")
                        row["updated"] += 1
        except Exception as exc:
            row["errors"].append(str(exc)[:500]); report["totals"]["blocked"] += 1
        for k in ("posts_seen","would_update","updated","already_current"): report["totals"][k] += row[k]
        report["sites"].append(row)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report["totals"],ensure_ascii=False)); print("REPORT="+str(REPORT))
    if report["totals"]["blocked"]: sys.exit(2)
    if args.mode == "preview": print("PREVIEW ONLY — no posts changed.")

if __name__ == "__main__": main()
