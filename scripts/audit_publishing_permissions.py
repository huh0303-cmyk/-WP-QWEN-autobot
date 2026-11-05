#!/usr/bin/env python3
"""Read-only publishing permission audit for all registered WordPress and Blogger sites.

Never creates, edits, publishes, or deletes posts. Credential values are never printed.
"""
from __future__ import annotations
import json, os, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
PROFILES = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
PROFILE_BY_KEY = {p["site_key"]: p for p in PROFILES.get("profiles", [])}
OUT = ROOT / "reports/publishing-permission-audit.json"
WP_USER = os.getenv("WP_USER", "huh0303@gmail.com")


def wp_check(site):
    secret = str(site.get("secret_name") or "").strip()
    password = os.getenv("WP_SECRET_" + secret, "").strip() if secret else ""
    username = WP_USER
    try:
        aggregate = json.loads(os.getenv("WP_SITE_CREDENTIALS_JSON", "{}"))
    except json.JSONDecodeError:
        aggregate = {}
    aggregate_item = aggregate.get(site.get("site_id")) or aggregate.get(secret) or aggregate.get(site.get("url")) or {}
    if isinstance(aggregate_item, dict):
        password = password or str(aggregate_item.get("app_password") or aggregate_item.get("password") or "").strip()
        username = str(aggregate_item.get("username") or aggregate_item.get("user") or username).strip()
    if not secret:
        return {"status":"MISSING_SECRET_MAPPING","write_access":False,"needed":f"GitHub Secret name mapping missing for {site['site_id']}"}
    if not password:
        return {"status":"MISSING_SECRET","write_access":False,"needed":f"Add GitHub Actions secret: {secret}"}
    url = site["url"].rstrip("/")
    try:
        r = requests.get(url + "/wp-json/wp/v2/users/me",
            params={"context":"edit","_fields":"id,name,slug,roles,capabilities"},
            auth=(username,password),timeout=25)
        if r.status_code in (401,403):
            return {"status":f"AUTH_OR_PERMISSION_{r.status_code}","write_access":False,
                    "needed":"Check Application Password, REST authentication and user role."}
        r.raise_for_status()
        data = r.json()
        caps = data.get("capabilities") or {}
        roles = data.get("roles") or []
        edit = bool(caps.get("edit_posts"))
        publish = bool(caps.get("publish_posts"))
        if not caps:
            # Some security configurations omit capability details; authenticated
            # edit-context access is recorded as partial, not falsely as write-ready.
            return {"status":"AUTH_OK_CAPABILITIES_NOT_EXPOSED","write_access":False,
                    "user_id":data.get("id"),"roles":roles,
                    "needed":"Capability details hidden. Confirm this user has Author or Editor role and edit_posts."}
        return {"status":"READY" if edit else "NO_EDIT_POSTS_CAPABILITY",
                "write_access":edit,"publish_access":publish,
                "user_id":data.get("id"),"roles":roles,
                "needed":None if edit else "Grant at least Author role or edit_posts capability."}
    except requests.RequestException as exc:
        return {"status":"NETWORK_OR_REST_ERROR","write_access":False,"needed":type(exc).__name__}


def blogger_token():
    names=("BLOGGER_GOOGLE_CLIENT_ID","BLOGGER_GOOGLE_CLIENT_SECRET","BLOGGER_GOOGLE_REFRESH_TOKEN")
    missing=[n for n in names if not os.getenv(n,"").strip()]
    if missing:
        return None, {"status":"MISSING_OAUTH_SECRETS","write_access":False,
                      "needed":"Add GitHub Actions secrets: "+", ".join(missing)}
    try:
        r=requests.post("https://oauth2.googleapis.com/token",data={
            "client_id":os.environ[names[0]],"client_secret":os.environ[names[1]],
            "refresh_token":os.environ[names[2]],"grant_type":"refresh_token"},timeout=30)
        if r.status_code>=400:
            return None, {"status":f"OAUTH_REFRESH_{r.status_code}","write_access":False,
                          "needed":"Refresh token/client credentials invalid, revoked, or expired."}
        access_token=r.json().get("access_token")
        info=requests.get("https://oauth2.googleapis.com/tokeninfo",
            params={"access_token":access_token},timeout=20)
        info.raise_for_status()
        scopes=set(str(info.json().get("scope","")).split())
        write_scope="https://www.googleapis.com/auth/blogger" in scopes
        return access_token, {"status":"TOKEN_OK" if write_scope else "TOKEN_READ_ONLY_OR_SCOPE_MISSING",
                              "blogger_write_scope":write_scope,
                              "needed":None if write_scope else "Re-authorize OAuth and grant https://www.googleapis.com/auth/blogger (not blogger.readonly)."}
    except requests.RequestException as exc:
        return None, {"status":"OAUTH_NETWORK_ERROR","write_access":False,"needed":type(exc).__name__}


def blogger_check(site, token):
    sid=site["site_id"]
    key=sid.split("_",1)[-1]
    profile=PROFILE_BY_KEY.get(key,{})
    blog=profile.get("blogspot") or {}
    blog_id=str(blog.get("destination_id") or "")
    if not blog_id:
        return {"status":"MISSING_BLOG_ID","write_access":False,"needed":"Add destination_id to content_engine_profiles.json."}
    if not token:
        return {"status":"OAUTH_UNAVAILABLE","write_access":False,"needed":"Fix Blogger OAuth secrets."}
    try:
        r=requests.get(f"https://www.googleapis.com/blogger/v3/users/self/blogs/{blog_id}",
            headers={"Authorization":f"Bearer {token}"},timeout=25)
        if r.status_code in (401,403):
            return {"status":f"OAUTH_OR_BLOG_ACCESS_{r.status_code}","write_access":False,
                    "blog_id":blog_id,"needed":"Re-authorize the Google account or add it as a Blogger Author/Administrator."}
        r.raise_for_status()
        data=r.json()
        info=data.get("blog_user_info") or {}
        role=str(info.get("role") or "").upper()
        admin=bool(info.get("hasAdminAccess"))
        writable=role in {"ADMIN","AUTHOR"} or admin
        return {"status":"READY" if writable else "READ_ONLY_OR_ROLE_UNKNOWN",
                "write_access":writable,"role":role or ("ADMIN" if admin else "UNKNOWN"),
                "blog_id":blog_id,"needed":None if writable else "Grant the Google account Author or Administrator access."}
    except requests.RequestException as exc:
        return {"status":"BLOGGER_API_ERROR","write_access":False,"blog_id":blog_id,
                "needed":type(exc).__name__}


def main():
    rows=[]
    wp_sites=[s for s in REGISTRY.get("sites",[]) if s.get("platform")=="wordpress" and s.get("enabled",True)]
    blogger_sites=[s for s in REGISTRY.get("sites",[]) if s.get("platform")=="blogger" and s.get("enabled",True)]
    token, oauth=blogger_token()
    if token and not oauth.get("blogger_write_scope"):
        token=None
    for site in wp_sites:
        result=wp_check(site)
        rows.append({"platform":"WordPress","site_id":site["site_id"],"url":site["url"],**result})
        print("WordPress",site["site_id"],result["status"],flush=True)
    for site in blogger_sites:
        result=blogger_check(site,token)
        rows.append({"platform":"Blogger","site_id":site["site_id"],"url":site["url"],**result})
        print("Blogger",site["site_id"],result["status"],result.get("role",""),flush=True)
    ready=sum(1 for x in rows if x.get("write_access"))
    summary={"checked":len(rows),"wordpress_checked":len(wp_sites),"blogger_checked":len(blogger_sites),
             "write_ready":ready,"needs_attention":len(rows)-ready,
             "oauth":oauth,"checked_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"summary":summary,"sites":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
    print("REPORT",OUT,flush=True)
    # Missing/limited access is reported as audit findings; don't hide artifact by failing job.
    return 0

if __name__=="__main__":
    raise SystemExit(main())
