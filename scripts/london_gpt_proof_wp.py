from __future__ import annotations
import json, os, sys
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

SITE="https://kstudy365.com"
SECRET="KSTUDY365COM"
USER="huh0303@gmail.com"
TITLE="TOPIK Study Plan: A 7-Day Routine Before Applying to a Korean University"
CONTENT="""<p>Preparing for TOPIK does not have to mean studying for hours every day. A short, repeatable routine is often more useful because it makes progress easier to track and keeps vocabulary, listening, reading and review in the same weekly cycle.</p>
<h2>A practical 7-day routine</h2>
<p><strong>Day 1:</strong> choose one TOPIK topic and collect 20 useful words. Write one short sentence for each word instead of memorizing a translation alone.</p>
<p><strong>Day 2:</strong> listen to a short Korean clip twice. The first time, listen for the main idea. The second time, note words or grammar you missed.</p>
<p><strong>Day 3:</strong> read one short passage under a time limit. Mark the sentence that contains the main point before checking unfamiliar vocabulary.</p>
<p><strong>Day 4:</strong> review the 20 words from Day 1 and remove the ones you already know. Spend more time on the words you still confuse.</p>
<p><strong>Day 5:</strong> practice one TOPIK question type you often get wrong. Focus on why the wrong answers are wrong, not only on the correct answer.</p>
<p><strong>Day 6:</strong> combine listening and reading. Summarize one short Korean item in two or three sentences using your own words.</p>
<p><strong>Day 7:</strong> do a weekly review. Record what improved, what remained difficult and what should become next week's priority.</p>
<h2>Keep the routine realistic</h2>
<p>Thirty focused minutes every day can be easier to sustain than one long session once a week. International students preparing to study in Korea should also keep admissions deadlines, required TOPIK levels and document preparation on a separate checklist so language study and application tasks do not compete for attention.</p>
<p>Before relying on any score requirement, check the current admissions notice from the university or program you plan to apply to. Requirements can differ by school, department and admission track.</p>"""

def main():
    creds_path=Path(os.environ.get("VPS_WP_CREDENTIALS","/etc/korea365/wp-sites.json"))
    creds=json.loads(creds_path.read_text(encoding="utf-8"))
    pw=creds.get(SECRET,"")
    if not pw: raise SystemExit("credential missing")
    auth=HTTPBasicAuth(USER,pw)
    api=SITE+"/wp-json/wp/v2/posts"
    r=requests.get(api,params={"search":TITLE,"per_page":20,"_fields":"id,title,link,status"},auth=auth,timeout=30)
    r.raise_for_status()
    for row in r.json():
        if row.get("status")=="publish" and row.get("title",{}).get("rendered","").strip()==TITLE:
            print(json.dumps({"platform":"wordpress","status":"existing","post_id":row["id"],"url":row["link"],"title":TITLE},ensure_ascii=False));return
    r=requests.post(api,json={"title":TITLE,"content":CONTENT,"status":"publish"},auth=auth,timeout=45)
    r.raise_for_status(); row=r.json()
    print(json.dumps({"platform":"wordpress","status":row.get("status"),"post_id":row.get("id"),"url":row.get("link"),"title":TITLE},ensure_ascii=False))
if __name__=="__main__": main()
