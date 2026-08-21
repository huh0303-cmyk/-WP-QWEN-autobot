#!/usr/bin/env python3
"""Deploy a newsroom front-page template to the active Twenty Twenty-Five theme."""
from __future__ import annotations
import argparse,html,json,os
from datetime import datetime,timezone
from pathlib import Path
import requests

USER=os.getenv("WP_USER","").strip() or "huh0303@gmail.com"
ENV={"koreanews365.com":"KOREANEWS365COM","theseouljournal.com":"THESEOULJOURNALCOM"}
CONFIRM="DEPLOY-NEWSROOM-FRONT-PAGE"
THEME="twentytwentyfive"

DATA={
"koreanews365.com":{
"name":"한국신문","tag":"한국뉴스 균형잡힌 정론지","edition":"2026 · SEOUL",
"breaking":"주요 뉴스","latest":"주요 기사","more":"전체 기사 보기","read":"기사 읽기",
"nav":[("속보","/category/breaking/"),("정치","/category/politics/"),("경제","/category/economy/"),("사회","/category/society/"),("국제","/category/world/")],
"sections":[("정치","politics"),("경제","economy"),("사회","society"),("국제","world")],
"footer":[("신문사 소개","/about/"),("편집 원칙","/editorial-standards/"),("정정·반론 보도","/corrections/"),("기사제보","/tips/"),("출처 및 저작권","/source-copyright-policy/")],
"css":"--ink:#0B1F3A;--accent:#B42318;--wash:#EEF2F6;--serif:'Noto Serif KR','Nanum Myeongjo','Batang',serif;--sans:'Noto Sans KR','Malgun Gothic',sans-serif"
},
"theseouljournal.com":{
"name":"THE SEOUL JOURNAL","tag":"Korea in Context. Asia in Focus.","edition":"2026 · SEOUL",
"breaking":"TOP STORIES","latest":"Latest","more":"View all stories","read":"Read story",
"nav":[("TOP STORIES","/category/top-stories/"),("KOREA","/category/korea/"),("ASIA","/category/asia/"),("WORLD","/category/world/"),("BUSINESS","/category/business/"),("TECHNOLOGY","/category/technology/")],
"sections":[("Korea","korea"),("Asia","asia"),("Business","business"),("Technology","technology")],
"footer":[("About","/about/"),("Editorial Standards","/editorial-standards/"),("Corrections","/corrections/"),("Submit a Tip","/tips/"),("Sources & Copyright","/source-copyright-policy/")],
"css":"--ink:#111111;--accent:#173B65;--wash:#F2F0EB;--serif:'Source Serif 4',Georgia,serif;--sans:Inter,Arial,sans-serif"
}}

def req(method,site,path,pw,data=None,params=None):
    r=requests.request(method,f"https://{site}/wp-json/wp/v2/{path}",auth=(USER,pw),json=data,params=params,
      headers={"User-Agent":"WP-Newsroom-Front/1.0"},timeout=60)
    if r.status_code>=400: raise RuntimeError(f"{site} {method} {path}: {r.status_code} {r.text[:500]}")
    return r.json() if r.text else {}

def link(label,url):
    return f'<a href="{url}">{html.escape(label)}</a>'

def query_block(per_page=5,cat_id=None,lead=False):
    inherit="false"
    q={"perPage":per_page,"pages":0,"offset":0,"postType":"post","order":"desc","orderBy":"date","author":"","search":"","exclude":[],"sticky":"","inherit":False}
    if cat_id:q["taxQuery"]={"category":[cat_id]}
    cls="news-lead" if lead else "news-grid"
    return f'''<!-- wp:query {json.dumps({"query":q},separators=(",",":"))} -->
<div class="wp-block-query {cls}"><!-- wp:post-template -->
<!-- wp:post-featured-image {{"isLink":true,"aspectRatio":"16/9"}} /-->
<!-- wp:group {{"className":"story-copy","layout":{{"type":"constrained"}}}} -->
<div class="wp-block-group story-copy"><!-- wp:post-date {{"format":"Y.m.d"}} /-->
<!-- wp:post-title {{"isLink":true}} /-->
<!-- wp:post-excerpt {{"moreText":"","excerptLength":24}} /--></div>
<!-- /wp:group --><!-- /wp:post-template -->
<!-- wp:query-no-results --><!-- wp:paragraph --><p>Newsroom preparation in progress.</p><!-- /wp:paragraph --><!-- /wp:query-no-results --></div>
<!-- /wp:query -->'''

def build(site,cats):
    d=DATA[site]
    nav="".join(link(a,b) for a,b in d["nav"])
    foot="".join(link(a,b) for a,b in d["footer"])
    sections=[]
    for label,slug in d["sections"]:
        cid=cats.get(slug)
        sections.append(f'''<!-- wp:group {{"className":"desk-section","layout":{{"type":"constrained"}}}} -->
<div class="wp-block-group desk-section"><div class="desk-head"><h2>{html.escape(label)}</h2><a href="/category/{slug}/">{html.escape(d["more"])}</a></div>
{query_block(3,cid)}</div><!-- /wp:group -->''')
    css=f'''<style>
:root{{{d["css"]}}}body{{font-family:var(--sans);color:var(--ink);background:#fff}}.wp-site-blocks{{padding:0!important}}
.newsroom-wrap{{max-width:1240px;margin:auto;padding:0 24px}}.news-mast{{border-top:6px solid var(--ink);border-bottom:1px solid var(--ink);padding:18px 0 12px}}
.news-topline{{display:flex;justify-content:space-between;font:700 12px var(--sans);letter-spacing:.08em;text-transform:uppercase}}
.news-brand{{font:900 clamp(36px,7vw,76px)/1 var(--serif);text-align:center;margin:18px 0 8px;letter-spacing:-.04em}}
.news-tag{{text-align:center;margin:0 0 16px;color:#4b5563}}.news-nav{{display:flex;gap:24px;justify-content:center;flex-wrap:wrap;border-top:1px solid #ccd3db;padding-top:12px}}
.news-nav a,.news-footer a,.desk-head a{{color:var(--ink);text-decoration:none;font-weight:700}}.breaking{{margin:20px 0;background:var(--ink);color:#fff;padding:10px 14px;font-weight:800;letter-spacing:.05em}}
.news-lead .wp-block-post-template,.news-grid .wp-block-post-template{{list-style:none;padding:0;display:grid;gap:24px}}.news-lead .wp-block-post-template{{grid-template-columns:repeat(2,minmax(0,1fr))}}
.news-grid .wp-block-post-template{{grid-template-columns:repeat(3,minmax(0,1fr))}}.wp-block-post-featured-image img{{width:100%;object-fit:cover;background:var(--wash)}}
.story-copy{{padding-top:10px}}.wp-block-post-date{{font-size:12px;color:#667085}}.wp-block-post-title{{font:700 clamp(21px,2.4vw,34px)/1.15 var(--serif);margin:8px 0}}
.wp-block-post-title a{{color:var(--ink);text-decoration:none}}.wp-block-post-excerpt{{color:#475467;line-height:1.65}}.desk-section{{border-top:3px solid var(--ink);margin-top:44px;padding-top:10px}}
.desk-head{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:16px}}.desk-head h2{{font:800 28px var(--serif);margin:0}}.news-footer{{margin-top:60px;background:var(--ink);color:#fff;padding:34px 24px}}
.news-footer-inner{{max-width:1240px;margin:auto}}.news-footer a{{color:#fff;margin-right:20px;display:inline-block;margin-bottom:10px}}.news-footer p{{color:#cbd5e1;font-size:13px}}
@media(max-width:760px){{.newsroom-wrap{{padding:0 16px}}.news-brand{{font-size:39px}}.news-nav{{gap:13px;font-size:12px}}.news-lead .wp-block-post-template,.news-grid .wp-block-post-template{{grid-template-columns:1fr}}.wp-block-post-title{{font-size:25px}}}}
</style>'''
    return f'''<!-- wp:html -->{css}<!-- /wp:html -->
<!-- wp:group {{"className":"newsroom-wrap","layout":{{"type":"constrained"}}}} --><div class="wp-block-group newsroom-wrap">
<!-- wp:html --><header class="news-mast"><div class="news-topline"><span>{d["edition"]}</span><span>INDEPENDENT NEWSROOM</span></div><h1 class="news-brand">{html.escape(d["name"])}</h1><p class="news-tag">{html.escape(d["tag"])}</p><nav class="news-nav">{nav}</nav></header><div class="breaking">{html.escape(d["breaking"])}</div><!-- /wp:html -->
{query_block(4,None,True)}
<!-- wp:heading {{"level":2,"className":"latest-title"}} --><h2 class="wp-block-heading latest-title">{html.escape(d["latest"])}</h2><!-- /wp:heading -->
{query_block(6)}
{''.join(sections)}
</div><!-- /wp:group -->
<!-- wp:html --><footer class="news-footer"><div class="news-footer-inner"><nav>{foot}</nav><p>© 2026 {html.escape(d["name"])} · Independent editorial operation · Corrections are recorded transparently.</p></div></footer><!-- /wp:html -->'''

def deploy(site):
    pw=os.getenv(ENV[site],"").strip()
    if not pw: raise RuntimeError(f"Missing {ENV[site]}")
    cats=req("GET",site,"categories",pw,params={"per_page":100,"_fields":"id,slug"})
    cmap={x["slug"]:x["id"] for x in cats}
    current=req("GET",site,"templates",pw,params={"context":"edit"})
    existing=next((x for x in current if x.get("slug")=="front-page" and x.get("theme")==THEME),None)
    before={"id":existing.get("id"),"content":existing.get("content",{}).get("raw","")} if existing else None
    payload={"slug":"front-page","theme":THEME,"type":"wp_template","title":f'{DATA[site]["name"]} Front Page',
      "description":"Managed newsroom front page v1","content":build(site,cmap),"status":"publish"}
    if existing: saved=req("POST",site,f'templates/{existing["id"]}',pw,payload)
    else: saved=req("POST",site,"templates",pw,payload)
    return {"site":site,"template_id":saved.get("id"),"previous_template":before,"category_ids":cmap}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--site",choices=["ALL",*ENV],default="ALL");ap.add_argument("--confirm",required=True)
    ap.add_argument("--receipt",default="newsroom_front_page_receipt.json");a=ap.parse_args()
    if a.confirm!=CONFIRM: raise SystemExit(f"Use --confirm {CONFIRM}")
    sites=list(ENV) if a.site=="ALL" else [a.site]
    out={"schema":1,"applied_at":datetime.now(timezone.utc).isoformat(),"results":[deploy(s) for s in sites]}
    Path(a.receipt).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
