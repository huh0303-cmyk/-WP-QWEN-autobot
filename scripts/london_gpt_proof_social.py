from __future__ import annotations
import json, os, time
from pathlib import Path
import requests

IMAGE_URL="https://raw.githubusercontent.com/huh0303-cmyk/-WP-QWEN-autobot/main/demo_assets/topik-proof-20260926.png"
TEXT="TOPIK 공부는 길게 한 번보다 매일 짧게 반복하는 편이 관리하기 쉽습니다. 30분 루틴: 어휘 10분 · 듣기 10분 · 읽기 5분 · 복습 5분. 작은 루틴을 7일간 기록해 보세요. #TOPIK #한국어공부 #StudyInKorea"

def req(method,url,**kwargs):
    r=requests.request(method,url,timeout=45,**kwargs)
    if not r.ok: raise RuntimeError(f"{r.status_code} {r.text[:500]}")
    return r.json()
def facebook():
    token=os.environ.get("FB_PAGE_ACCESS_TOKEN","")
    if not token:return {"platform":"facebook","status":"blocked","reason":"FB_PAGE_ACCESS_TOKEN missing"}
    me=req("GET","https://graph.facebook.com/me",params={"fields":"id,name","access_token":token})
    post=req("POST",f"https://graph.facebook.com/{me['id']}/feed",data={"message":TEXT,"link":"https://kstudy365.com","access_token":token})
    permalink=""
    try: permalink=req("GET",f"https://graph.facebook.com/{post['id']}",params={"fields":"permalink_url","access_token":token}).get("permalink_url","")
    except Exception: pass
    return {"platform":"facebook","status":"published","page_id":me["id"],"post_id":post["id"],"url":permalink}
def instagram():
    token=os.environ.get("IG_ACCESS_TOKEN",""); uid=os.environ.get("IG_USER_ID","")
    if not token or not uid:return {"platform":"instagram","status":"blocked","reason":"IG token/id missing"}
    container=req("POST",f"https://graph.facebook.com/{uid}/media",data={"image_url":IMAGE_URL,"caption":TEXT,"access_token":token})
    cid=container["id"]
    for _ in range(12):
        try:
            st=req("GET",f"https://graph.facebook.com/{cid}",params={"fields":"status_code","access_token":token}).get("status_code","")
            if st=="FINISHED":break
        except Exception: pass
        time.sleep(2)
    post=req("POST",f"https://graph.facebook.com/{uid}/media_publish",data={"creation_id":cid,"access_token":token})
    url=""
    try:url=req("GET",f"https://graph.facebook.com/{post['id']}",params={"fields":"permalink","access_token":token}).get("permalink","")
    except Exception:pass
    return {"platform":"instagram","status":"published","media_id":post["id"],"url":url}
def main():
    out=[] 
    for fn in (instagram,facebook):
        try:out.append(fn())
        except Exception as e:out.append({"platform":fn.__name__(),"status":"failed","error":str(e)})
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/london-gpt-social-proof.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False))
if __name__=="__main__":main()
