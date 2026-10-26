#!/usr/bin/env python3
"""Find exact normalized-title duplicates in all ten language channels.
Keep highest views; ties keep newest. Missing view counts are report-only.
"""
import argparse, datetime as dt, json, os, re, unicodedata
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"config/survival_language_channels.json"
OUT=ROOT/"artifacts/youtube/language-duplicate-audit"
def env(code,name):
 s=f"LANGUAGE_{code.upper()}"
 v=os.environ.get(f"YOUTUBE_OAUTH_{name}_{s}") or os.environ.get(f"YOUTUBE_OAUTH_{name}")
 if not v: raise RuntimeError(f"Missing YOUTUBE_OAUTH_{name}_{s}")
 return v
def svc(code):
 c=Credentials(token=None,refresh_token=env(code,"REFRESH_TOKEN"),token_uri="https://oauth2.googleapis.com/token",client_id=env(code,"CLIENT_ID"),client_secret=env(code,"CLIENT_SECRET"),scopes=None)
 return build("youtube","v3",credentials=c,cache_discovery=False)
def norm(s):
 s=unicodedata.normalize("NFKC",s).casefold()
 s=re.sub(r"#shorts?\\b","",s)
 return re.sub(r"[^\\w]+","",s,flags=re.UNICODE)
def videos(api,cid,limit):
 rows=api.channels().list(part="contentDetails",id=cid).execute().get("items",[])
 if len(rows)!=1: raise RuntimeError(f"Cannot resolve uploads playlist {cid}")
 pl=rows[0]["contentDetails"]["relatedPlaylists"]["uploads"]; ids=[]; token=None
 while len(ids)<limit:
  page=api.playlistItems().list(part="contentDetails",playlistId=pl,maxResults=min(50,limit-len(ids)),pageToken=token).execute()
  ids += [x["contentDetails"]["videoId"] for x in page.get("items",[])]
  token=page.get("nextPageToken")
  if not token: break
 out=[]
 for i in range(0,len(ids),50): out += api.videos().list(part="snippet,statistics,status",id=",".join(ids[i:i+50])).execute().get("items",[])
 return out
def main():
 p=argparse.ArgumentParser(); p.add_argument("--apply",action="store_true"); p.add_argument("--limit",type=int,default=500); a=p.parse_args()
 registry=json.loads(REG.read_text(encoding="utf-8")); OUT.mkdir(parents=True,exist_ok=True)
 report={"mode":"apply" if a.apply else "report_only","created_at":dt.datetime.now(dt.timezone.utc).isoformat(),"channels":[],"actions":[]}
 for row in registry["languages"]:
  code,cid=row["language_code"],row["channel_id"]; api=svc(code)
  mine=api.channels().list(part="id",mine=True).execute().get("items",[])
  if len(mine)!=1 or mine[0]["id"]!=cid:
   report["channels"].append({"language":code,"status":"BLOCKED_CHANNEL_IDENTITY_MISMATCH"}); continue
  allv=videos(api,cid,a.limit); groups={}
  for v in allv:
   if v.get("status",{}).get("privacyStatus")=="private": continue
   key=norm(v.get("snippet",{}).get("title",""))
   if key: groups.setdefault(key,[]).append(v)
  losers=0
  for group in groups.values():
   if len(group)<2: continue
   if any("viewCount" not in v.get("statistics",{}) for v in group):
    report["actions"].append({"language":code,"status":"REVIEW_VIEW_COUNT_UNAVAILABLE","video_ids":[v["id"] for v in group]}); continue
   group.sort(key=lambda v:(int(v["statistics"]["viewCount"]),v.get("snippet",{}).get("publishedAt","")),reverse=True)
   keep=group[0]
   for v in group[1:]:
    action={"language":code,"title":v["snippet"].get("title"),"keep_video_id":keep["id"],"keep_views":int(keep["statistics"]["viewCount"]),"duplicate_video_id":v["id"],"duplicate_views":int(v["statistics"]["viewCount"]),"status":"WOULD_SET_PRIVATE"}
    if a.apply:
     old=v.get("status",{}); st={k:old[k] for k in ("license","embeddable","publicStatsViewable","selfDeclaredMadeForKids") if k in old}; st["privacyStatus"]="private"
     api.videos().update(part="status",body={"id":v["id"],"status":st}).execute()
     chk=api.videos().list(part="snippet,status",id=v["id"]).execute().get("items",[])
     if len(chk)!=1 or chk[0].get("snippet",{}).get("channelId")!=cid or chk[0].get("status",{}).get("privacyStatus")!="private": raise RuntimeError(f"Privacy verification failed: {v['id']}")
     action["status"]="VERIFIED_PRIVATE"
    report["actions"].append(action); losers+=1
  report["channels"].append({"language":code,"videos_scanned":len(allv),"duplicate_losers":losers,"status":"SCANNED"})
 path=OUT/f"duplicate_audit_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
 path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
 print(json.dumps({"mode":report["mode"],"channels":report["channels"],"actions":report["actions"],"report_path":str(path)},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
