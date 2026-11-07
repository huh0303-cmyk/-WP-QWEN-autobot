#!/usr/bin/env python3
"""Daily deterministic random Seoul Journal publication slots (Asia/Seoul)."""
from datetime import datetime,timedelta,timezone
import hashlib,json,os
KST=timezone(timedelta(hours=9))
WINDOWS=[("morning","politics",8*60,10*60),("midday","sports",13*60,15*60),("evening","hot_issue",19*60,22*60)]
def due(now):
    day=now.strftime("%Y-%m-%d")
    minute=now.hour*60+now.minute
    for slot,category,start,end in WINDOWS:
        choices=list(range(start,end,10))
        digest=hashlib.sha256((day+"|seoul-journal|"+slot).encode()).digest()
        selected=choices[int.from_bytes(digest[:8],"big")%len(choices)]
        # tolerate scheduling delay while minimizing repeat dispatch
        if selected<=minute<selected+20:
            return slot,category,selected
    return "none","none",-1
if __name__=="__main__":
    now=datetime.now(KST)
    slot,category,m=due(now)
    print("KST_NOW="+now.isoformat())
    print("JOURNAL_SLOT="+slot)
    print("JOURNAL_CATEGORY="+category)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f:
            f.write("slot="+slot+"\ncategory="+category+"\n")
