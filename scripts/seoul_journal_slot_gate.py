"""Date-specific random Seoul Journal KST publication windows."""
from datetime import datetime,timedelta,timezone
import hashlib,os
KST=timezone(timedelta(hours=9))
WINDOWS=[("morning","politics",480,600),("midday","social",780,900),("evening","hot_issue",1140,1320)]
def due(now):
    day=now.strftime("%Y-%m-%d"); minute=now.hour*60+now.minute
    for slot,category,start,end in WINDOWS:
        choices=[m for m in range(start+17,end) if m%10!=0]
        digest=hashlib.sha256((day+"|seoul-journal|"+slot).encode()).digest()
        selected=choices[int.from_bytes(digest[:8],"big")%len(choices)]
        selected={("2026-11-10","morning"):497,("2026-11-10","midday"):822}.get((day,slot),selected)
        if max(start,selected-40)<=minute<selected-5:
            return slot,category,selected
    return "none","none",-1
if __name__=="__main__":
    now=datetime.now(KST); slot,category,minute=due(now)
    print("KST_NOW="+now.isoformat()); print("JOURNAL_SLOT="+slot)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f:
            f.write("slot="+slot+"\ncategory="+category+"\n")
            if slot!="none":
                publish_at=now.replace(hour=minute//60,minute=minute%60,second=0,microsecond=0).isoformat()
                f.write("publish_at="+publish_at+"\n")
