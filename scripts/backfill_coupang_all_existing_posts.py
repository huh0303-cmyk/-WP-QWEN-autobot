#!/usr/bin/env python3
"""Backfill exactly ten shared Coupang cards into every existing WP/Blogger post.

Preview is read-only. Apply updates only the post body/content field and verifies
that ten distinct affiliate destinations are visible after the update.
"""
from __future__ import annotations
import argparse, html, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automation_hub.coupang_partners import apply_footer, load_candidates, select_products, HEADER_START, HEADER_END, START, END

REGISTRY = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
MASTER_POLICY = json.loads((ROOT / "config/affiliate/portfolio-master-policy-2026-11-05.json").read_text(encoding="utf-8"))
WP_AFFILIATE_POLICY = {str(x["domain"]).lower(): x for x in MASTER_POLICY.get("wordpress", [])}
WP_ROLLOUT_ORDER = [str(x["domain"]).lower() for x in reversed(MASTER_POLICY.get("wordpress", []))]
PROFILES = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
PROFILE_BY_KEY = {p["site_key"]: p for p in PROFILES.get("profiles", [])}
REPORT = ROOT / "reports/coupang-existing-posts-backfill.json"
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."

def wp_auth(site, credentials):
    item = credentials.get(site["site_id"]) or credentials.get(site.get("secret_name","")) or {}
    user = item.get("username") or item.get("user") or os.getenv("WP_USER","").strip() or "huh0303@gmail.com"
    password = item.get("app_password") or item.get("password") or os.getenv(site.get("secret_name",""),"").strip()
    return (user, password) if user and password else None

def wp_posts(session, base):
    page = 1
    while True:
        response = session.get(base.rstrip("/") + "/wp-json/wp/v2/posts",
            params={"status":"publish","per_page":100,"page":page,"context":"edit",
                    "_fields":"id,link,title,content,status,date,modified"},
            timeout=60)
        if response.status_code == 400 and page > 1:
            break
        response.raise_for_status()
        batch = response.json()
        if not batch: break
        yield from batch
        if len(batch) < 100: break
        page += 1

def blogger_posts(session, blog_id, token):
    endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
    page_token = None
    while True:
        params = {"fetchBodies":"true","maxResults":500,"status":["live"]}
        if page_token: params["pageToken"] = page_token
        r = session.get(endpoint, params=params, headers={"Authorization":f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        data = r.json()
        yield from data.get("items", [])
        page_token = data.get("nextPageToken")
        if not page_token: break

def clean_title(value):
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()

def lang_for(site, content):
    lang = str(site.get("language","en")).lower()
    return "ko" if lang.startswith("ko") else "en"

def distinct_links(content):
    return set(re.findall(r"""href=["'](https://link\.coupang\.com/[^"']+)""", content or ""))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("preview","apply"), default=os.getenv("MODE","preview"))
    ap.add_argument("--platform", choices=("all","wordpress","blogger"), default=os.getenv("PLATFORM","all"))
    ap.add_argument("--site-id", default=os.getenv("SITE_ID",""))
    ap.add_argument("--limit-per-site", type=int, default=0)
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()
    if args.mode == "apply" and args.confirm != "APPLY-ALL":
        raise SystemExit("Apply mode requires --confirm APPLY-ALL")
    try:
        wp_credentials = json.loads(os.getenv("WP_SITE_CREDENTIALS_JSON","").strip() or "{}")
    except json.JSONDecodeError as exc:
        raise SystemExit("WP_SITE_CREDENTIALS_JSON is not valid JSON") from exc

    blogger_token = ""
    if args.platform in ("all","blogger"):
        cid, secret, refresh = (os.getenv(k,"") for k in (
            "BLOGGER_GOOGLE_CLIENT_ID","BLOGGER_GOOGLE_CLIENT_SECRET","BLOGGER_GOOGLE_REFRESH_TOKEN"))
        if cid and secret and refresh:
            tr = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id":cid,"client_secret":secret,"refresh_token":refresh,"grant_type":"refresh_token"}, timeout=30)
            tr.raise_for_status()
            blogger_token = tr.json()["access_token"]

    report = {"mode":args.mode,"platform":args.platform,"started_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
              "sites":[],"totals":{"posts_seen":0,"updated":0,"already_ten":0,"needs_catalog":0,"skipped_legacy":0,"errors":0}}
    session = requests.Session()
    site_rows = [x for x in REGISTRY.get("sites",[]) if x.get("platform") == "wordpress"]
    order_index = {domain: i for i, domain in enumerate(WP_ROLLOUT_ORDER)}
    site_rows.sort(key=lambda x: order_index.get(urlparse(x.get("url", "")).netloc.lower().removeprefix("www."), 10**6))
    for site in site_rows if args.platform == "wordpress" else REGISTRY.get("sites",[]):
        sid, platform = site.get("site_id",""), site.get("platform","")
        if not site.get("enabled", True): continue
        if args.site_id and sid != args.site_id: continue
        if args.platform != "all" and platform != args.platform: continue
        site_key = sid.split("_",1)[-1]
        site_domain = urlparse(site.get("url", "")).netloc.lower().removeprefix("www.")
        policy = WP_AFFILIATE_POLICY.get(site_domain) if platform == "wordpress" else None
        profile = PROFILE_BY_KEY.get(site_key,{})
        # Resolve K-Health365's four missing official product images once before
        # counting candidates. The helper persists the URLs in this run's workspace.
        khealth_image_error = None
        if sid == "wp_khealth365":
            from scripts.khealth365_sitewide_coupang_10 import load_products as load_khealth_products
            try:
                load_khealth_products()
            except Exception as exc:
                # A Coupang product page may deny automated image resolution (403).
                # Never fail the whole fleet or substitute an unverified image.
                khealth_image_error = type(exc).__name__ + ": " + str(exc)[:180]
        if platform == "wordpress" and (not policy or policy.get("provider") != "coupang"):
            report["sites"].append({"site_id":sid,"url":site.get("url"),"platform":platform,"status":"held_by_master_policy","provider":(policy or {}).get("provider","unlisted"),"reason":"This Coupang-only workflow does not process no-affiliate, excluded, Trip.com, or Olive Young destinations."})
            continue
        catalog_count = len(load_candidates(sid))
        entry = {"site_id":sid,"url":site.get("url"),"platform":platform,
                 "verified_products":catalog_count,"posts_seen":0,"updated":0,
                 "already_ten":0,"needs_catalog":0,"skipped_legacy":0,"errors":[]}
        if catalog_count < 10:
            entry["needs_catalog"] = 1
            entry["catalog_note"] = f"{catalog_count}/10 verified site-specific products; apply available cards and all three banners"
            if khealth_image_error:
                entry["image_note"] = "official image resolution blocked; no substitute used: " + khealth_image_error
            report["totals"]["needs_catalog"] += 1
        try:
            if platform == "wordpress":
                auth = wp_auth(site, wp_credentials)
                if not auth:
                    entry["errors"].append("missing site credential: add the site's Application Password as GitHub Secret " + str(site.get("secret_name") or "(secret mapping missing)"))
                    report["totals"]["errors"] += 1
                    report["sites"].append(entry); continue
                base = site["url"].rstrip("/")
                s = requests.Session(); s.auth = auth
                posts = wp_posts(s, base)
                for idx, post in enumerate(posts):
                    try:
                        if args.limit_per_site and idx >= args.limit_per_site: break
                        raw = post.get("content",{}).get("raw")
                        if raw is None:
                            entry["errors"].append({"post_id":post.get("id"),"reason":"raw content unavailable"}); continue
                        title = clean_title(post.get("title",{}).get("rendered",""))
                        lang = lang_for(site, raw)
                        new = apply_footer(raw,title,sid,lang)
                        entry["posts_seen"] += 1
                        report["totals"]["posts_seen"] += 1
                        if new == raw:
                            if HEADER_START in raw and HEADER_END in raw and START in raw and END in raw:
                                entry["already_ten"] += 1
                            elif "link.coupang.com/" in raw or DISCLOSURE in raw:
                                entry["skipped_legacy"] += 1
                            else:
                                entry["errors"].append({"post_id":post["id"],"reason":"footer unchanged; inspect catalog or legacy markup"})
                            continue
                        if args.mode == "apply":
                            endpoint = base + "/wp-json/wp/v2/posts/" + str(post["id"])
                            put = s.post(endpoint,json={"content":new},timeout=60); put.raise_for_status()
                            check = s.get(endpoint,params={"context":"edit","_fields":"id,content,status,date"},timeout=60); check.raise_for_status()
                            verified = check.json().get("content",{}).get("raw","")
                            links = distinct_links(verified)
                            expected = set(p["url"] for p in select_products(title,raw,sid))
                            if HEADER_START not in verified or HEADER_END not in verified or START not in verified or END not in verified or not expected.issubset(links):
                                entry["errors"].append({"post_id":post["id"],"reason":"read-back verification failed"}); continue
                            entry["updated"] += 1; report["totals"]["updated"] += 1
                        else:
                            entry["updated"] += 1
                    except Exception as exc:
                        entry["errors"].append({"post_id": post.get("id"), "reason": "post failed; continuing to next post: " + str(exc)[:350]})
                        report["totals"]["errors"] += 1
            elif platform == "blogger":
                if not blogger_token:
                    entry["errors"].append("missing Blogger OAuth refresh-token secrets")
                    report["totals"]["errors"] += 1
                    report["sites"].append(entry); continue
                blog_id = profile.get("blogspot",{}).get("destination_id")
                if not blog_id:
                    entry["errors"].append("Blogger blog ID missing from content_engine_profiles.json")
                    report["totals"]["errors"] += 1
                    report["sites"].append(entry); continue
                endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
                for idx, post in enumerate(blogger_posts(session,blog_id,blogger_token)):
                    try:
                        if args.limit_per_site and idx >= args.limit_per_site: break
                        raw = post.get("content","")
                        title = clean_title(post.get("title",""))
                        new = apply_footer(raw,title,sid,lang_for(site,raw))
                        entry["posts_seen"] += 1; report["totals"]["posts_seen"] += 1
                        if new == raw:
                            if HEADER_START in raw and HEADER_END in raw and START in raw and END in raw: entry["already_ten"] += 1
                            elif "link.coupang.com/" in raw or DISCLOSURE in raw: entry["skipped_legacy"] += 1
                            else: entry["errors"].append({"post_id":post.get("id"),"reason":"footer unchanged; inspect catalog or legacy markup"})
                            continue
                        if args.mode == "apply":
                            payload = dict(post); payload["content"] = new
                            put = session.put(endpoint + "/" + str(post["id"]),params={"fetchBody": "true"},
                                headers={"Authorization":f"Bearer {blogger_token}"},json=payload,timeout=60)
                            put.raise_for_status()
                            verify = session.get(endpoint + "/" + str(post["id"]),params={"view":"ADMIN"},
                                headers={"Authorization":f"Bearer {blogger_token}"},timeout=60)
                            verify.raise_for_status()
                            content = verify.json().get("content","")
                            expected = set(p["url"] for p in select_products(title,raw,sid))
                            if HEADER_START not in content or HEADER_END not in content or START not in content or END not in content or not expected.issubset(distinct_links(content)):
                                entry["errors"].append({"post_id":post["id"],"reason":"Blogger read-back verification failed"}); continue
                            entry["updated"] += 1; report["totals"]["updated"] += 1
                        else: entry["updated"] += 1
                    except Exception as exc:
                        entry["errors"].append({"post_id": post.get("id"), "reason": "Blogger post failed; continuing to next post: " + str(exc)[:350]})
                        report["totals"]["errors"] += 1
            else:
                entry["errors"].append("unsupported platform")
        except Exception as exc:
            entry["errors"].append(str(exc)[:500])
            report["totals"]["errors"] += 1
        report["sites"].append(entry)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report["totals"],ensure_ascii=False))
    print(f"REPORT={REPORT}")
    if report["totals"]["errors"]:
        print(f"COMPLETED WITH HOLDS — {report['totals']['errors']} item/site errors recorded; remaining sites were still processed.")
    else:
        print("COMPLETED — no item/site errors recorded.")
    if args.mode == "preview": print("PREVIEW ONLY — no published posts were modified.")

if __name__ == "__main__":
    main()
