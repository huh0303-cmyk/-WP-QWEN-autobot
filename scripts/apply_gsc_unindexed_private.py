#!/usr/bin/env python3
"""Apply reviewed private candidates from index_audit_manifest.json.

Reversible (status=private, never force-deletes). Requires an exact confirmation
token and refuses unknown/API-error records and fresh posts.
"""
import argparse, json, os
from pathlib import Path
import requests
from site_registry import SITES

WP_USER="huh0303@gmail.com"
REG={u:(secret,state) for u,secret,state in SITES}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",default="index_audit_manifest.json")
    ap.add_argument("--site",required=True)
    ap.add_argument("--execute",action="store_true")
    ap.add_argument("--confirm",default="")
    args=ap.parse_args()
    data=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if args.site not in data.get("sites",{}): raise SystemExit("site absent from manifest")
    rows=list(data["sites"][args.site].get("posts",{}).values())
    targets=[r for r in rows if r.get("state")=="unindexed" and r.get("private_candidate") is True and r.get("age_days",0)>=60]
    print(f"{args.site}: reviewed private candidates={len(targets)}")
    for r in targets[:30]: print(f"  {r['id']} | {r.get('coverageState')} | {r.get('title','')[:60]}")
    if not args.execute:
        print("DRY RUN: no changes"); return
    if args.confirm!="PRIVATE_REVIEWED_UNINDEXED": raise SystemExit("exact --confirm token required")
    secret,lifecycle=REG[args.site]; pw=os.getenv(secret,"")
    if not pw: raise SystemExit(f"{secret} missing")
    changed=[]; failed=[]
    for r in targets:
        x=requests.post(f"{args.site}/wp-json/wp/v2/posts/{r['id']}",auth=(WP_USER,pw),json={"status":"private"},timeout=30)
        (changed if x.status_code in (200,201) else failed).append(r["id"])
    receipt={"site":args.site,"changed":changed,"failed":failed,"reversible":True}
    Path("index_privacy_receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print(json.dumps(receipt,indent=2))

if __name__=="__main__": main()
