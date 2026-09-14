#!/usr/bin/env python3
import os, requests, json, base64

WP_USER = "huh0303@gmail.com"
pw = os.getenv("KHEALTH365COM","")
SITE = "https://k-health365.com"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO = os.getenv("GITHUB_REPOSITORY","")

r = requests.get(f"{SITE}/wp-json/rankmath/v1/settings",
                auth=(WP_USER,pw), timeout=10)
print(f"HTTP: {r.status_code}")
if r.status_code == 200:
    rm = r.json()
    general = rm.get("general",{})
    head_code = general.get("head_code","")
    print(f"head_code 존재: {bool(head_code)}")
    print(f"head_code 내용: {head_code[:200]}")
    has_adsense = "ca-pub-3456727916386941" in head_code
    print(f"애드센스 포함: {has_adsense}")
    
    result = {"head_code": head_code, "has_adsense": has_adsense}
    if GH_TOKEN:
        content = __import__("base64").b64encode(__import__("json").dumps(result).encode()).decode()
        gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
        path = "khealth_rm_head.json"
        rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
        sha = rg.json().get("sha","") if rg.status_code==200 else ""
        payload = {"message":"check: rm head_code","content":content}
        if sha: payload["sha"] = sha
        requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,json=payload,timeout=15)
    print("완료")
