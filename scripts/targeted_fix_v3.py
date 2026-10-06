#!/usr/bin/env python3
"""Targeted fixes (explicit lists): WP title edits; strip a duplicated Pexels photo (figure+img) from named Blogger posts."""
import json, os, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_titles_images_v2 import ROOT  # noqa: E402

TITLES = {("wp_studyinkorea", 3017): "First-Month Checklist for International Students in Korea: Housing and Admin Priorities",
          ("wp_korea365", 1967): "The Soulful Slurp: Korean vs Japanese Ramen Compared"}
STRIP = [("blogger_jobkorea365", "3842163091688651214", "7673904"), ("blogger_kinsurance365", "2186394693265006931", "7673904"),
         ("blogger_kworld365", "2466803557709945664", "144429"), ("blogger_kworld365", "7772210719924873097", "18495176")]
sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
sites = sites if isinstance(sites, list) else sites["sites"]
wp = {s["site_id"]: s for s in sites if s["platform"] == "wordpress"}
for (site, pid), t in TITLES.items():
    s = wp[site]; auth = ("huh0303@gmail.com", os.environ[s["secret_name"]])
    old = requests.get(f"{s['url']}/wp-json/wp/v2/posts/{pid}", auth=auth, params={"context": "edit"}, timeout=30).json()["title"]["raw"]
    r = requests.post(f"{s['url']}/wp-json/wp/v2/posts/{pid}", auth=auth, json={"title": t}, timeout=40)
    print("title", site, pid, "|", old, "=>", t, "|", "ok" if r.ok else r.status_code, flush=True)
tok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
      "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}
prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
bid = {f"blogger_{r['site_key']}": r["blogspot"]["destination_id"] for r in prof["profiles"] if r.get("blogspot", {}).get("destination_id")}
for site, pid, photo in STRIP:
    u = f"https://www.googleapis.com/blogger/v3/blogs/{bid[site]}/posts/{pid}"
    body = requests.get(u, headers=h, timeout=30).json()["content"]
    soup = BeautifulSoup(body, "html.parser"); n = 0
    for img in list(soup.find_all("img")):
        if photo in img.get("src", ""):
            (img.find_parent("figure") or img).decompose(); n += 1
    if n:
        r = requests.patch(u, headers=h, json={"content": str(soup)}, timeout=40)
        print("strip", site, pid, photo, n, "ok" if r.ok else r.status_code, flush=True)
    else:
        print("strip", site, pid, "photo not found", flush=True)
    time.sleep(0.6)
