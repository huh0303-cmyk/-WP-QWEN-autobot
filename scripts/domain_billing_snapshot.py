#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/domain_billing_snapshot.json"
UA={"User-Agent":"Korea365-Control/1.0"}

def inspect(domain):
    urls=["https://rdap.org/domain/"+domain]
    if domain.endswith(".com"):
        urls.append("https://rdap.verisign.com/com/v1/domain/"+domain)
    elif domain.endswith(".org"):
        urls.append("https://rdap.publicinterestregistry.org/rdap/domain/"+domain)
    p=None; last_error=""
    for url in urls:
        try:
            r=requests.get(url,headers=UA,timeout=15);r.raise_for_status();p=r.json();break
        except Exception as e:
            last_error=type(e).__name__
    if p is None:
        return domain,{"provider":"","registered_date":"","expiry_date":"","error":last_error or "RDAPError"}
    provider=""
    for entity in p.get("entities",[]):
        if "registrar" not in entity.get("roles",[]):continue
        try:
            for item in entity.get("vcardArray",[None,[]])[1]:
                if item and item[0]=="fn":provider=str(item[3]);break
        except Exception:pass
        if provider:break
    reg=exp=""
    for event in p.get("events",[]):
        action=event.get("eventAction");dt=str(event.get("eventDate") or "")[:10]
        if action=="registration":reg=dt
        elif action=="expiration":exp=dt
    return domain,{"provider":provider,"registered_date":reg,"expiry_date":exp,"error":""}

def main():
    profiles=json.loads((ROOT/"config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    domains=[]
    for p in profiles:
        u=(p.get("wordpress") or {}).get("url")
        if u:
            d=(urlparse(u).hostname or "").lower()
            if d and d not in domains:domains.append(d)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        rows=dict(ex.map(inspect,domains))
    payload={"generated_at":datetime.now(timezone.utc).isoformat(),"domains":rows}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"domains":len(rows),"complete":sum(bool(x.get("expiry_date")) for x in rows.values())},ensure_ascii=False))
if __name__=="__main__":main()
