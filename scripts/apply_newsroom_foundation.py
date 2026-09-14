#!/usr/bin/env python3
"""Guarded WordPress newsroom foundation setup. No post deletion or theme activation."""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/"config/newsrooms.json").read_text(encoding="utf-8"))
USER=os.getenv("WP_USER","").strip() or "huh0303@gmail.com"
ENV={"koreanews365.com":"KOREANEWS365COM","theseouljournal.com":"THESEOULJOURNALCOM"}
CONFIRM="APPLY-NEWSROOM-FOUNDATION"

PAGE_COPY={
"ko-KR":{
"about":("신문사 소개","<h2>한국신문 소개</h2><p>한국신문은 사실 확인과 맥락 설명을 우선하는 독립 종합 인터넷신문을 지향합니다.</p><p>기사와 의견을 구분하고, 출처·작성일·수정 이력을 투명하게 표시합니다.</p>"),
"editorial-standards":("편집 원칙","<h2>편집 원칙</h2><ol><li>복수의 신뢰할 수 있는 자료로 핵심 사실을 확인합니다.</li><li>기사, 분석, 의견, 광고를 명확히 구분합니다.</li><li>보도자료나 타 매체 기사를 그대로 복제하거나 문장만 바꾸어 게시하지 않습니다.</li><li>인공지능은 자료 정리 보조로만 사용하며 최종 판단과 책임은 편집자가 집니다.</li><li>이해관계와 제휴 관계는 독자에게 공개합니다.</li></ol>"),
"corrections":("정정·반론 보도","<h2>정정 및 반론 보도</h2><p>사실 오류가 확인되면 신속히 바로잡고 기사 하단에 수정 일시와 내용을 남깁니다. 반론·정정 요청은 문의 페이지를 통해 접수합니다.</p>"),
"tips":("기사제보","<h2>기사제보</h2><p>공익적 가치가 있는 제보를 받습니다. 확인되지 않은 주장은 게시하지 않으며, 제보자의 신원과 자료는 관련 법령과 취재윤리에 따라 다룹니다.</p>"),
"source-copyright-policy":("출처 및 저작권 정책","<h2>출처 및 저작권 정책</h2><p>원문을 대체하는 복제·번역·문장 돌려쓰기를 하지 않습니다. 외부 자료는 이용조건을 확인하고 필요한 범위에서 인용하며 원 출처 링크와 자료명을 표시합니다.</p><p>별도 서면 허락이나 상업적 제휴가 필요한 RSS는 자동 수집 대상에서 제외합니다.</p>")
},
"en-US":{
"about":("About","<h2>About The Seoul Journal</h2><p>The Seoul Journal is an independent English-language publication explaining Korea and Asia with verified sources, original context and transparent corrections.</p>"),
"editorial-standards":("Editorial Standards","<h2>Editorial Standards</h2><ol><li>Verify material facts against reliable primary or multiple independent sources.</li><li>Clearly distinguish news, analysis, opinion and advertising.</li><li>Never copy, line-translate or superficially rewrite another outlet's reporting.</li><li>AI may assist research organization, but an editor remains accountable for every published article.</li><li>Disclose relevant conflicts and commercial relationships.</li></ol>"),
"corrections":("Corrections & Right of Reply","<h2>Corrections &amp; Right of Reply</h2><p>We correct confirmed errors promptly and append a dated correction note. Requests for correction or reply may be submitted through our contact page.</p>"),
"tips":("Submit a Tip","<h2>Submit a Tip</h2><p>We welcome information with a clear public-interest value. Unverified claims are not published, and source material is handled under applicable law and editorial ethics.</p>"),
"source-copyright-policy":("Sources & Copyright","<h2>Sources &amp; Copyright</h2><p>We do not reproduce, line-translate or spin reporting from other publishers. External material is used only after checking its terms, with proportionate quotation, clear attribution and a direct source link.</p><p>Feeds requiring separate written permission or a commercial content agreement are excluded from automation.</p>")
}}

def req(method,site,path,password,data=None,params=None):
    r=requests.request(method,f"https://{site}/wp-json/wp/v2/{path}",auth=(USER,password),
        json=data,params=params,headers={"User-Agent":"WP-Newsroom-Setup/1.0"},timeout=30)
    if r.status_code >= 400: raise RuntimeError(f"{site} {method} {path}: {r.status_code} {r.text[:300]}")
    return r.json()

def snapshot(site,pw):
    return {
      "site":site,"captured_at":datetime.now(timezone.utc).isoformat(),
      "settings":req("GET",site,"settings",pw),
      "categories":req("GET",site,"categories",pw,params={"per_page":100,"_fields":"id,name,slug,count"}),
      "pages":req("GET",site,"pages",pw,params={"per_page":100,"status":"any","_fields":"id,slug,status,title"})
    }

def ensure_cat(site,pw,item):
    found=req("GET",site,"categories",pw,params={"slug":item["slug"],"per_page":1})
    if found:
        current=found[0]
        if current.get("name") != item["name"]:
            updated=req("POST",site,f"categories/{current['id']}",pw,{"name":item["name"]})
            return {"id":updated["id"],"action":"renamed","slug":item["slug"]}
        return {"id":current["id"],"action":"kept","slug":item["slug"]}
    x=req("POST",site,"categories",pw,{"name":item["name"],"slug":item["slug"],"description":f'{item["name"]} newsroom desk'})
    return {"id":x["id"],"action":"created","slug":item["slug"]}

def ensure_page(site,pw,lang,item):
    title,content=PAGE_COPY[lang][item["slug"]]
    found=req("GET",site,"pages",pw,params={"slug":item["slug"],"status":"any","per_page":1})
    payload={"title":title,"slug":item["slug"],"content":content,"status":"publish"}
    if found:
        x=req("POST",site,f'pages/{found[0]["id"]}',pw,payload)
        return {"id":x["id"],"action":"updated","slug":item["slug"]}
    x=req("POST",site,"pages",pw,payload)
    return {"id":x["id"],"action":"created","slug":item["slug"]}

def apply(site):
    pw=os.getenv(ENV[site],"").strip()
    if not pw: raise RuntimeError(f"Missing secret {ENV[site]}")
    cfg=CFG["sites"][site]
    before=snapshot(site,pw)
    req("POST",site,"settings",pw,{"title":cfg["name"],"description":cfg["tagline"],"timezone":"Asia/Seoul"})
    cats=[ensure_cat(site,pw,x) for x in cfg["categories"]]
    pages=[ensure_page(site,pw,cfg["language"],x) for x in cfg["editorial_pages"]]
    return {"site":site,"before":before,"changes":{"settings":["title","description","timezone"],"categories":cats,"pages":pages},
      "safety":{"posts_deleted":0,"categories_deleted":0,"theme_changed":False}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--site",choices=["ALL",*CFG["sites"]],default="ALL")
    ap.add_argument("--confirm",required=True)
    ap.add_argument("--receipt",default="newsroom_foundation_receipt.json")
    a=ap.parse_args()
    if a.confirm!=CONFIRM: raise SystemExit(f"Refusing apply. Use --confirm {CONFIRM}")
    sites=list(CFG["sites"]) if a.site=="ALL" else [a.site]
    result={"schema":1,"applied_at":datetime.now(timezone.utc).isoformat(),"results":[apply(s) for s in sites]}
    Path(a.receipt).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
