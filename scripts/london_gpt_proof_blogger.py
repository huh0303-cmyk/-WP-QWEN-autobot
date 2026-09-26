from __future__ import annotations
import json, os
from pathlib import Path
import requests

BLOG_ID="1529526209955625690"
TITLE="How to Build a 30-Minute Daily TOPIK Routine Before Studying in Korea"
CONTENT="""<p>A daily TOPIK routine works best when every session has a clear purpose. Instead of trying to study every skill at once, divide thirty minutes into small blocks that you can repeat even on busy days.</p>
<h2>The 30-minute structure</h2>
<p><strong>10 minutes — vocabulary:</strong> review a small set of useful words and write one example sentence for each difficult item.</p>
<p><strong>10 minutes — listening:</strong> use one short Korean clip. Listen once for the main idea and once again for details.</p>
<p><strong>5 minutes — reading:</strong> read a short paragraph and identify the main point before checking unknown words.</p>
<p><strong>5 minutes — review:</strong> write down one mistake or weak point that should become tomorrow's first task.</p>
<h2>Use weekly checkpoints</h2>
<p>At the end of each week, look at your notes and choose one skill that needs more attention. This keeps your routine flexible without making it complicated.</p>
<p>If you are preparing for university study in Korea, keep language preparation separate from your admissions checklist. TOPIK score requirements, application dates and document rules can differ by university and admission track, so always confirm the current official notice before making a final plan.</p>
<p>A simple routine is useful because it is measurable: you can see which words were retained, which listening mistakes repeat and which reading question types take too long. Consistency matters more than making every study session perfect.</p>"""
LABELS=["TOPIK","Korean Language","Study in Korea","International Students","Korean Study","Admissions"]

def token():
    data={"client_id":os.environ.get("BLOGGER_GOOGLE_CLIENT_ID"),"client_secret":os.environ.get("BLOGGER_GOOGLE_CLIENT_SECRET"),"refresh_token":os.environ.get("BLOGGER_GOOGLE_REFRESH_TOKEN"),"grant_type":"refresh_token"}
    if not all(data.values()): raise SystemExit("blogger oauth missing")
    r=requests.post("https://oauth2.googleapis.com/token",data=data,timeout=30);r.raise_for_status();return r.json()["access_token"]
def main():
    out=Path("artifacts");out.mkdir(exist_ok=True)
    h={"Authorization":"Bearer "+token(),"Content-Type":"application/json"}
    search=requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/search",headers=h,params={"q":TITLE,"fetchBodies":"false"},timeout=30)
    if search.ok:
        for row in search.json().get("items",[]):
            if row.get("title","").strip()==TITLE:
                result={"platform":"blogger","status":"existing","post_id":row["id"],"url":row.get("url"),"title":TITLE}
                (out/"london-gpt-blogger-proof.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(result));return
    r=requests.post(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/",headers=h,params={"isDraft":"false"},json={"kind":"blogger#post","title":TITLE,"content":CONTENT,"labels":LABELS},timeout=45)
    r.raise_for_status(); row=r.json()
    result={"platform":"blogger","status":"published","post_id":row.get("id"),"url":row.get("url"),"title":TITLE}
    (out/"london-gpt-blogger-proof.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(result))
if __name__=="__main__":main()
