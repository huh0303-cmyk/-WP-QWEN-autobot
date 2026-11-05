#!/usr/bin/env python3
"""Append verified, per-destination affiliate offers to WordPress and Blogger."""
from __future__ import annotations
import argparse, hashlib, html, json, os, sys
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import requests

ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT/"affiliate-engine"
ROUTING=ENGINE/"config"/"affiliate-routing.json"
POLICY=ROOT/"config"/"affiliate_distribution_policy.json"
CATALOG_DIR=ENGINE/"data"/"catalogs"
MARKER="<!-- london-affiliate-engine:v7-footer-only -->"
LEGACY_AFFILIATE_MARKERS=("<!-- LONDON-COUPANG-PARTNERS-START -->","<!-- LONDON-AFFILIATE-HEADER-START -->","<!-- KHEALTH365-COUPANG-START -->","london-coupang-wrap","london-affiliate-partner-strip")
DISCLOSURE="<p><small>This post contains Coupang Partners affiliate links. If you visit Coupang through one of these links and make a purchase within 24 hours, including a purchase of another eligible product, we may earn a commission at no additional cost to you. Attribution rules, cancellations and returns may affect commission eligibility.</small><br/><small>이 게시물에는 쿠팡 파트너스 제휴 링크가 포함되어 있습니다. 이 링크를 통해 쿠팡에 방문한 뒤 24시간 이내에 다른 상품을 구매하더라도 운영정책상 실적으로 인정되는 구매라면 수수료를 제공받을 수 있습니다. 구매 경로의 최종 기여, 주문 취소 및 반품 등에 따라 수수료가 인정되지 않을 수 있습니다.</small></p>"

def load_json(path:Path)->Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))

def normalized(value:str)->str:
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in value).split())

def category_key(value:str)->str:
    raw=str(value or "").lower()
    if raw in {"health_functional_foods","health_supplements","k_health_supplements","health","supplement","supplements","vitamin","vitamins"}: return "health_functional_foods"
    if raw in {"k_beauty_skincare","beauty_cosmetics","k_beauty_olive_young","beauty","skincare","kbeauty"}: return "k_beauty_skincare"
    return raw

def recent_since(hours:int)->str:
    return (datetime.now(UTC)-timedelta(hours=hours)).isoformat().replace("+00:00","Z")

def load_destinations(platform:str)->list[dict[str,str]]:
    registry=load_json(ROOT/"config"/"automation_hub_sites.json")["sites"]
    out=[]
    for row in registry:
        if row.get("platform")!=platform:
            continue
        site_id=str(row.get("site_id",""))
        out.append({"site_key":site_id,"url":str(row.get("url","")),"secret_name":str(row.get("secret_name","")),"destination_id":str(row.get("blog_id") or row.get("destination_id") or "")})
    return out

def load_site_catalog(site_key:str)->dict[str,Any]:
    path=CATALOG_DIR/f"{site_key}.json"
    if not path.exists(): raise ValueError(f"missing_site_catalog:{site_key}")
    payload=load_json(path)
    if payload.get("status") not in {"verified","ready"}: raise ValueError(f"catalog_not_verified:{site_key}")
    return payload

def load_site_offers(site_key:str)->list[dict[str,Any]]:
    return load_site_catalog(site_key).get("offers",[])

def select_offers(title:str,content:str,routing:dict[str,Any],site_key:str,offers:list[dict[str,Any]]|None=None)->list[dict[str,Any]]:
    """Use up to ten destination-specific, verified Coupang products; never invent filler."""
    source=offers if offers is not None else load_site_offers(site_key)
    chosen=[]
    seen=set()
    for offer in source:
        if not isinstance(offer,dict) or offer.get("provider")!="coupang_partners":
            continue
        if offer.get("affiliate_link_verified") is not True or offer.get("image_rights_verified") is not True:
            continue
        if any(not (urlparse(str(offer.get(k,""))).scheme=="https" and urlparse(str(offer.get(k,""))).netloc) for k in ("url","image_url")):
            continue
        url=str(offer["url"])
        if url in seen:
            continue
        seen.add(url)
        chosen.append(offer)
        if len(chosen)>=10:
            break
    if not chosen:
        raise ValueError(f"no_verified_coupang_products_for_destination:{site_key}")
    return chosen

def build_block(offers:list[dict[str,Any]],header_buttons:list[dict[str,Any]]|None=None,trip_categories:list[dict[str,Any]]|None=None)->str:
    if not 1<=len(offers)<=10 or any(o.get("provider")!="coupang_partners" for o in offers):
        raise ValueError("between_1_and_10_verified_coupang_product_cards_required")
    if len({o.get("url") for o in offers})!=len(offers): raise ValueError("duplicate_product_tracking_url")
    if not header_buttons or len(header_buttons)!=3: raise ValueError("missing_three_header_provider_buttons")
    expected=("coupang_partners","olive_young_global","trip_com")
    button_map={x.get("provider"):x for x in header_buttons}
    if set(button_map)!=set(expected): raise ValueError("header_button_provider_set_mismatch")
    header_buttons=[button_map[p] for p in expected]
    colors={"coupang_partners":"#e87518","olive_young_global":"#168a43","trip_com":"#1769d2"}
    labels={"coupang_partners":"Coupang","olive_young_global":"OLIVE YOUNG","trip_com":"Trip.com"}
    logo_fallback={"coupang_partners":"https://commons.wikimedia.org/wiki/Special:FilePath/Coupang_logo.svg","olive_young_global":"https://dist.oliveyoung.com/fo/fe126e9b35/resources/images/common/logo.svg","trip_com":"https://commons.wikimedia.org/wiki/Special:FilePath/Trip.com_logo.svg"}
    buttons=[]
    for b in header_buttons:
        if not str(b.get("affiliate_url","")).startswith("https://"): raise ValueError(f"missing_header_button_url:{b.get('provider')}")
        if b.get("verified") is not True and not (b.get("provider")=="olive_young_global" and b.get("status")=="redirect_test_failed_gate_url_null"):
            raise ValueError(f"unverified_header_button:{b.get('provider')}")
        provider=b["provider"]; label=labels[provider]
        logo_url=logo_fallback[provider]
        logo=f'<img class="london-affiliate-brand-logo" src="{html.escape(logo_url,quote=True)}" alt="{label} official company logo" loading="lazy" decoding="async"/>'
        buttons.append(f'<a class="london-affiliate-provider-button {provider}" style="--brand-color:{colors[provider]}" href="{html.escape(b["affiliate_url"],quote=True)}" target="_blank" rel="sponsored nofollow noopener" aria-label="{label} affiliate link">{logo}<span>{label}</span></a>')
    cards=[]
    for o in offers:
        title=html.escape(o["title"])
        cards.append(f'<article class="london-affiliate-card"><a class="london-affiliate-image-link" href="{html.escape(o["url"],quote=True)}" rel="sponsored nofollow noopener" target="_blank"><img src="{html.escape(o["image_url"],quote=True)}" alt="{html.escape(o.get("image_alt",o["title"]),quote=True)}" loading="lazy" decoding="async"/></a><small>{html.escape(o.get("category_label",o.get("category","")))}</small><strong>{title}</strong><a class="london-affiliate-cta" href="{html.escape(o["url"],quote=True)}" rel="sponsored nofollow noopener" target="_blank">상품 확인하기</a></article>')
    css="<style>.london-affiliate-provider-buttons{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 24px}.london-affiliate-provider-button{box-sizing:border-box;display:flex;min-width:0;min-height:92px;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:12px 8px;border:1px solid #e5e7eb;border-top:4px solid var(--brand-color);border-radius:10px;background:#fff;color:#202124!important;text-decoration:none!important;font-weight:800;text-align:center}.london-affiliate-brand-logo{display:block;width:150px;max-width:100%;height:auto;max-height:54px;object-fit:contain}.london-affiliate-provider-button span{font-size:8px;line-height:1.2;font-weight:500;color:#777}.london-affiliate-provider-button.coupang_partners span{display:none}.london-affiliate-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.london-affiliate-card{display:flex;min-width:0;flex-direction:column;gap:8px;border:1px solid #e5e7eb;border-radius:12px;padding:12px}.london-affiliate-card img{width:100%;height:160px;object-fit:contain}.london-affiliate-card strong{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;min-height:4.5em}.london-affiliate-cta{margin-top:auto;text-align:center;padding:9px;background:#17365d;color:white!important;border-radius:7px;text-decoration:none!important}.london-affiliate-provider-button.coupang_partners{--brand-color:#e87518}.london-affiliate-provider-button.olive_young_global{--brand-color:#168a43}.london-affiliate-provider-button.trip_com{--brand-color:#1769d2}@media(max-width:640px){.london-affiliate-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.london-affiliate-provider-buttons{gap:6px}.london-affiliate-provider-button{min-height:78px;padding:8px 4px}.london-affiliate-brand-logo{max-height:48px;width:132px}.london-affiliate-provider-button span{font-size:7px}}</style>"
    return "\\n".join([MARKER,'<section class="london-affiliate-engine"><div class="london-affiliate-provider-buttons">',*buttons,'</div>',DISCLOSURE,f'<h2>쿠팡 추천 상품 {len(offers)}선</h2>','<div class="london-affiliate-grid">',*cards,'</div></section>',css])

def can_write(requested:bool)->bool:
    return requested and os.getenv("AFFILIATE_WRITE_ENABLED","").lower()=="true"

def wordpress(dest,since,block_for,write,scope,batch_size):
    base=dest["url"].rstrip("/"); password=os.getenv(dest["secret_name"],""); rows=[]; page=1
    while len(rows)<batch_size:
        params={"status":"publish","per_page":100,"page":page,"orderby":"date","order":"desc"}
        if scope=="new": params["after"]=since
        response=requests.get(f"{base}/wp-json/wp/v2/posts",params=params,timeout=30)
        if response.status_code==400 and page>1: break
        response.raise_for_status(); posts=response.json()
        if not posts: break
        for post in posts:
            content=post["content"]["rendered"]
            result={"platform":"wordpress","site":dest["site_key"],"post_id":post["id"],"url":post["link"],"action":"skipped"}
            if any(marker in content for marker in (MARKER,*LEGACY_AFFILIATE_MARKERS)): result["reason"]="existing_managed_affiliate_footer_preserved"
            else:
                try: block=block_for(post["title"]["rendered"],content,dest["site_key"])
                except ValueError as exc: result.update(action="blocked",reason=str(exc))
                else:
                    result["action"]="would_append"
                    if write:
                        if not password: result.update(action="blocked",reason="missing_wordpress_secret")
                        else:
                            update=requests.post(f"{base}/wp-json/wp/v2/posts/{post['id']}",auth=(os.getenv("WP_USER",""),password),json={"content":content+"\n"+block},timeout=30)
                            update.raise_for_status()
                            verify=requests.get(f"{base}/wp-json/wp/v2/posts/{post['id']}",params={"context":"edit"},auth=(os.getenv("WP_USER",""),password),timeout=30)
                            verify.raise_for_status()
                            if MARKER not in verify.json()["content"]["raw"]: raise RuntimeError("wordpress_readback_marker_missing")
                            result["action"]="appended_verified"
            rows.append(result)
            if len(rows)>=batch_size: break
        if scope=="new" or len(posts)<100: break
        page+=1
    return rows

def blogger_token():
    response=requests.post("https://oauth2.googleapis.com/token",data={"client_id":os.getenv("BLOGGER_GOOGLE_CLIENT_ID",""),"client_secret":os.getenv("BLOGGER_GOOGLE_CLIENT_SECRET",""),"refresh_token":os.getenv("BLOGGER_GOOGLE_REFRESH_TOKEN",""),"grant_type":"refresh_token"},timeout=30)
    response.raise_for_status(); return response.json()["access_token"]

def blogger(dest,since,block_for,write,scope,batch_size):
    if not dest["destination_id"]: return []
    token=blogger_token() if write else ""; headers={"Authorization":f"Bearer {token}"} if token else {}
    endpoint=f"https://www.googleapis.com/blogger/v3/blogs/{dest['destination_id']}/posts"; rows=[]; page_token=""
    while len(rows)<batch_size:
        params={"fetchBodies":"true","maxResults":100}
        if scope=="new": params["publishedMin"]=since
        if page_token: params["pageToken"]=page_token
        response=requests.get(endpoint,params=params,headers=headers,timeout=30); response.raise_for_status(); payload=response.json()
        for post in payload.get("items",[]):
            content=post["content"]; result={"platform":"blogger","site":dest["site_key"],"post_id":post["id"],"url":post["url"],"action":"skipped"}
            if MARKER in content: result["reason"]="already_has_v5_marker"
            else:
                try: block=block_for(post["title"],content,dest["site_key"])
                except ValueError as exc: result.update(action="blocked",reason=str(exc))
                else:
                    result["action"]="would_append"
                    if write:
                        update=requests.put(f"{endpoint}/{post['id']}",headers=headers,json={"title":post["title"],"content":content+"\n"+block},timeout=30)
                        update.raise_for_status()
                        verify=requests.get(f"{endpoint}/{post['id']}",params={"fetchBody":"true"},headers=headers,timeout=30); verify.raise_for_status()
                        if MARKER not in verify.json().get("content",""): raise RuntimeError("blogger_readback_marker_missing")
                        result["action"]="appended_verified"
            rows.append(result)
            if len(rows)>=batch_size: break
        page_token=payload.get("nextPageToken","")
        if scope=="new" or not page_token: break
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--platform",choices=["wordpress","blogger","all"],default="all")
    parser.add_argument("--scope",choices=["new","backfill"],default="new")
    parser.add_argument("--since-hours",type=int,default=36)
    parser.add_argument("--batch-size",type=int,default=5)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    end_raw=os.getenv("AFFILIATE_AUTOMATION_END","").strip()
    if end_raw:
        end_at=datetime.fromisoformat(end_raw)
        if datetime.now(ZoneInfo("Asia/Seoul")) > end_at.astimezone(ZoneInfo("Asia/Seoul")):
            print(json.dumps({"automation":"expired","end_at":end_raw,"write":False},ensure_ascii=False))
            return 0
    routing=load_json(ROUTING); write=can_write(args.write)
    if args.write and not write: raise SystemExit("write blocked: set AFFILIATE_WRITE_ENABLED=true as a GitHub secret")
    since=recent_since(args.since_hours)
    def block_for(title,content,site_key):
        catalog=load_site_catalog(site_key)
        offers=select_offers(title,content,routing,site_key,catalog.get("offers",[]))
        return build_block(offers,catalog.get("header_buttons",[]),catalog.get("trip_com_categories",[]))
    results=[]
    if args.platform in {"wordpress","all"}:
        for dest in load_destinations("wordpress"):
            try: results.extend(wordpress(dest,since,block_for,write,args.scope,args.batch_size))
            except (requests.RequestException,ValueError,RuntimeError) as exc: results.append({"platform":"wordpress","site":dest["site_key"],"action":"blocked","reason":str(exc)[:240]})
    if args.platform in {"blogger","all"}:
        for dest in load_destinations("blogger"):
            try: results.extend(blogger(dest,since,block_for,write,args.scope,args.batch_size))
            except (requests.RequestException,ValueError,RuntimeError) as exc: results.append({"platform":"blogger","site":dest["site_key"],"action":"blocked","reason":str(exc)[:240]})
    report={"generated_at":datetime.now(UTC).isoformat(),"scope":args.scope,"since":since,"batch_size":args.batch_size,"write":write,"policy":"v7_footer_only_three_official_logo_banners_then_up_to_10_verified_coupang_cards","results":results}
    out=ENGINE/"reports"/f"latest-{args.scope}-run.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"write":write,"processed":len(results),"appended_verified":sum(r["action"]=="appended_verified" for r in results),"blocked":sum(r["action"]=="blocked" for r in results)},ensure_ascii=False))
    return 0
if __name__=="__main__": sys.exit(main())
