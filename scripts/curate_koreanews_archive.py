#!/usr/bin/env python3
"""Curate existing Koreanews articles into five newsroom desks; creates no new articles."""
from __future__ import annotations
import argparse,html,json,os,re
from datetime import datetime,timezone
from pathlib import Path
import requests

USER=os.getenv("WP_USER","").strip() or "huh0303@gmail.com"
PW=os.getenv("KOREANEWS365COM","").strip()
BASE="https://koreanews365.com/wp-json/wp/v2"
CONFIRM="CURATE-KOREANEWS-5X5"
DESKS={"breaking":1438,"politics":788,"economy":787,"society":789,"world":989}
# Existing post id -> clean headline, primary desk. Five marked breaking receive a second category.
CURATED={
  4363:("여권 내부 계파 논쟁 재점화…지도부 대응 놓고 공방","politics",False),
  4375:("정청래·김민석, 충청·영남 표심 경쟁 본격화","politics",True),
  4378:("정부, 주 52시간 유연화 특구 검토…노동정책 쟁점은","politics",True),
  3529:("인천 공기업 인사 재편 가능성…새 시정의 선택 주목","politics",False),
  3675:("안철수·한동훈 관계 둘러싼 야권 내 논쟁","politics",False),
  4372:("미국 2분기 성장률 둔화…물가 압력은 지속","economy",True),
  3391:("SK하이닉스 ADR 추진론, 국내 투자자에게 미칠 영향","economy",False),
  4315:("삼성전자, 로봇 사업 확대…신성장 동력 확보 나서","economy",False),
  4308:("TSMC 일본 공장 본격 가동…동아시아 반도체 경쟁 가열","economy",False),
  4317:("충남 수출, 반도체·AI 수요 힘입어 빠른 증가세","economy",False),
  4379:("여성 근로자 절반인데 관리직은 0명…고용 불균형 여전","society",True),
  4320:("임신 36주 낙태 사건, 항소심 판단이 남긴 쟁점","society",False),
  4344:("한국 갯벌 세계유산 확대…여수·고흥·무안·서산 포함","society",False),
  4324:("무신사, AI 작성 후기 제한…온라인 리뷰 신뢰성 강화","society",False),
  4392:("충주찰옥수수버거 이물질 논란…판매 중단과 후속 조치","society",False),
  4319:("동아시아, AI·고령화·패권 경쟁 속 공동 대응 과제","world",True),
  3410:("베네수엘라 강진 피해 확산…현지 구조·복구 상황","world",False),
  3392:("이란 여성 공연자 처벌 논란…복장 규제와 문화적 자유","world",False),
  3325:("탄소중립 정책, 주요국의 대응과 한국의 과제","world",False),
  3273:("지속가능한 성장의 조건…산업 전환과 국제 협력","world",False)
}

def req(method,path,data=None,params=None):
    r=requests.request(method,f"{BASE}/{path}",auth=(USER,PW),json=data,params=params,
      headers={"User-Agent":"WP-Koreanews-Curation/1.0"},timeout=50)
    if r.status_code>=400:raise RuntimeError(f"{method} {path}: {r.status_code} {r.text[:500]}")
    return r.json() if r.text else {},r.headers

def clean_excerpt(content):
    text=html.unescape(re.sub(r"<[^>]+>"," ",content or ""))
    text=re.sub(r"\s+"," ",text).strip()
    for junk in ("Build Your Website in Minutes with One-Click Import – No Coding Hassle!","Build Your Website"):
        text=text.replace(junk,"").strip()
    return (text[:210].rsplit(" ",1)[0] if len(text)>210 else text) or "한국신문 편집국이 주요 사실과 배경을 정리했습니다."

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--confirm",required=True);ap.add_argument("--receipt",default="koreanews_curation_receipt.json");a=ap.parse_args()
    if a.confirm!=CONFIRM:raise SystemExit(f"Use --confirm {CONFIRM}")
    if not PW:raise SystemExit("Missing KOREANEWS365COM")
    receipt={"schema":1,"applied_at":datetime.now(timezone.utc).isoformat(),"changes":[]}
    selected=set(CURATED)
    # Remove currently exposed dummy/archive posts and stale scheduled posts from public rotation.
    for status in ("publish","future"):
        posts,_=req("GET","posts",params={"context":"edit","status":status,"per_page":100,"_fields":"id,status,title,date"})
        for p in posts:
            if p["id"] not in selected:
                saved,_=req("POST",f'posts/{p["id"]}',{"status":"private"})
                receipt["changes"].append({"id":p["id"],"action":"quarantine","from":status,"to":saved["status"],"title":p["title"]["raw"]})
    # Republish only the curated archive with cleaned display metadata.
    for pid,(title,desk,is_breaking) in CURATED.items():
        post,_=req("GET",f"posts/{pid}",params={"context":"edit"})
        cats=[DESKS[desk]]+([DESKS["breaking"]] if is_breaking else [])
        payload={"title":title,"excerpt":clean_excerpt(post.get("content",{}).get("raw","")),"categories":cats,"status":"publish"}
        saved,_=req("POST",f"posts/{pid}",payload)
        receipt["changes"].append({"id":pid,"action":"curate_publish","from":post["status"],"to":saved["status"],
          "title_before":post["title"]["raw"],"title_after":title,"categories":cats,"date_preserved":post["date"]})
    counts={slug:0 for slug in DESKS}
    cats,_=req("GET","categories",params={"per_page":100,"_fields":"slug,count"})
    for cat in cats:
        if cat["slug"] in counts:counts[cat["slug"]]=cat["count"]
    receipt["category_counts"]=counts
    receipt["new_posts_created"]=0
    Path(a.receipt).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"category_counts":counts,"changes":len(receipt["changes"]),"new_posts_created":0},ensure_ascii=False,indent=2))
    if any(counts[x]<5 for x in DESKS):raise SystemExit(f"Category minimum failed: {counts}")

if __name__=="__main__":main()
