"""Scheduled Meta publishing. Fail closed on identity, missing media and uncertain outcomes."""
import hashlib, json, os, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data/meta_publishing_receipts.json"
KST = timezone(timedelta(hours=9))
POLICY = json.loads((ROOT / "config/meta_five_account_daily_policy.json").read_text(encoding="utf-8-sig"))
sys.path.insert(0, str(ROOT / "scripts"))
from meta_daily_schedule import plan

def call(url, method="GET", token=None, payload=None):
    headers = {"User-Agent": "LondonProject-MetaPublisher/1.0"}
    if token: headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        payload = urlencode(payload).encode()
    try:
        with urlopen(Request(url, data=payload, headers=headers, method=method), timeout=35) as r:
            return json.loads(r.read().decode())
    except HTTPError as e:
        raise RuntimeError("API HTTP " + str(e.code)) from None

def generate(account, platform, slot):
    key = os.getenv("GEMINI_API_KEY", "")
    if not key: raise RuntimeError("GEMINI_API_KEY missing")
    # Never generate unsourced breaking news, politics, medical efficacy or prices.
    if account["key"] in ("seoul_jisoo", "seoul_chris"):
        category = "timeless Korean skincare routines or everyday wellbeing; avoid medical and commercial claims"
    else:
        category = ", ".join(account["topics"])
    prompt = (
        "Write ONE original educational social media post in a friendly tone, "
        "in up to 350 characters for Threads or up to 900 characters for Instagram. "
        "Use account topic: " + category + ". "
        "Keep facts evergreen, no politics, current news, real-time sports scores, "
        "prices or health treatment claims. No invented links, personal data, or sales pitch. "
        "Include one helpful example where educational. "
        "Return plain post text only, no markdown. "
        "Make it distinct for account " + account["key"] +
        ", platform " + platform + ", dated slot " + slot["slot_id"]
    )
    model = os.getenv("META_GEMINI_FREE_MODEL", "gemini-2.5-flash-lite")
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
    body = json.dumps({"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.8,"maxOutputTokens":350}})
    import urllib.request
    req = urllib.request.Request(endpoint, data=body.encode(), headers={
        "x-goog-api-key":key, "Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            result = json.loads(r.read().decode())
    except HTTPError as e:
        raise RuntimeError("Gemini API HTTP " + str(e.code)) from None
    text = "".join(p.get("text","") for c in result.get("candidates",[]) for p in c.get("content",{}).get("parts",[])).strip()
    if not text or len(text) > (500 if platform=="threads" else 2200):
        raise RuntimeError("Generated content empty or too long")
    return text

def main():
    now = datetime.now(KST)
    today = now.date().isoformat()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    changed = False
    accounts = {a["key"]:a for a in POLICY["accounts"]}
    for slot in plan(today):
        slot_id = slot["slot_id"]
        if slot_id in state: continue
        hh, mm = map(int,slot["time_kst"].split(":"))
        due = now.replace(hour=hh,minute=mm,second=0,microsecond=0)
        # Allow only 20 minutes of catchup; do not flood posts on outages.
        delay = (now-due).total_seconds()
        if delay < 0 or delay > 1200: continue
        platform, name = slot["platform"], slot["account_key"]
        prefix = "META_" + platform.upper() + "_" + name.upper()
        token = os.getenv(prefix+"_ACCESS_TOKEN", "")
        uid = os.getenv(prefix+"_USER_ID", "")
        # Only Threads text publication is supported without media; IG needs approved media.
        if platform == "instagram": continue
        if not token or not uid or not uid.isdigit(): continue
        expected = slot["expected_handle"].lower()
        try:
            me = call("https://graph.threads.net/v1.0/me?fields=id,username", token=token)
            if str(me.get("id")) != uid or me.get("username","").lower()!=expected:
                raise RuntimeError("Account identity mismatch")
            caption = generate(accounts[name], platform, slot)
            # Write marker BEFORE network publish to prevent duplicate retries on uncertainty.
            state[slot_id]={"status":"ATTEMPT_RESERVED","account":name,"platform":platform,"at":now.isoformat(),
                "content_sha256":hashlib.sha256(caption.encode()).hexdigest()}
            STATE.parent.mkdir(parents=True,exist_ok=True)
            STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("RESERVED_SLOT="+slot_id,flush=True)
            import subprocess
            for cmd in (["git","add","data/meta_publishing_receipts.json"],
                        ["git","commit","-m","meta: reserve post slot"],
                        ["git","push","origin","HEAD:main"]):
                check = subprocess.run(cmd, capture_output=True, text=True)
                if check.returncode:
                    raise RuntimeError("Reserve not safely persisted: "+cmd[1])
            if os.getenv("META_LIVE_PUBLISH","false").lower()!="true":
                state[slot_id]["status"]="PREPARED_ONLY"
                continue
            container=call("https://graph.threads.net/v1.0/"+uid+"/threads",method="POST",token=token,payload={"media_type":"TEXT","text":caption})
            cid=str(container.get("id",""))
            if not cid: raise RuntimeError("No Threads container ID")
            # Threads text containers generally become ready shortly after creation.
            time.sleep(5)
            published=call("https://graph.threads.net/v1.0/"+uid+"/threads_publish",method="POST",token=token,payload={"creation_id":cid})
            pid=str(published.get("id",""))
            if not pid: raise RuntimeError("No published ID")
            verification=call("https://graph.threads.net/v1.0/"+pid+"?fields=id,permalink", token=token)
            url=str(verification.get("permalink",""))
            if str(verification.get("id",""))!=pid or not url.startswith("https://"):
                raise RuntimeError("Published ID exists but public URL not confirmed")
            state[slot_id]["status"]="PUBLISHED"
            state[slot_id]["id"]=pid
            state[slot_id]["public_url"]=url
            print("PUBLISHED_SLOT="+slot_id+" URL="+url,flush=True)
        except Exception as e:
            if slot_id in state:
                state[slot_id]["status"]="NEEDS_RECONCILIATION"
                state[slot_id]["error"]=str(e)[:120]
            else:
                print("SKIPPED_SLOT="+slot_id+" REASON="+str(e)[:120],flush=True)
        finally:
            if slot_id in state:
                STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                changed=True
    print("META_DISPATCH_FINISHED state_changed="+str(changed))
if __name__ == "__main__": main()
