"""Publish an authorized, reviewed Seoul Journal package and read back the result."""
import argparse,datetime,json,os
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
CHANNEL="UChRUdHZlXSjftAqBtdDNEWA"
def youtube(credentials_file=None):
    if credentials_file:
        data=json.loads(Path(credentials_file).read_text(encoding="utf-8-sig"))
    else:
        data={"client_id":os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
              "client_secret":os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"],
              "refresh_token":os.environ["SEOUL_JOURNAL_YOUTUBE_OAUTH_REFRESH_TOKEN"]}
    creds=Credentials(token=None,refresh_token=data["refresh_token"],token_uri="https://oauth2.googleapis.com/token",
                      client_id=data["client_id"],client_secret=data["client_secret"])
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    mine=yt.channels().list(part="id,contentDetails",mine=True).execute()["items"]
    if len(mine)!=1 or mine[0]["id"]!=CHANNEL: raise RuntimeError("Channel identity mismatch")
    return yt,mine[0]["contentDetails"]["relatedPlaylists"]["uploads"]
def recent(yt,playlist):
    ids=[]; page=None
    for _ in range(2):
        data=yt.playlistItems().list(part="contentDetails",playlistId=playlist,maxResults=50,pageToken=page).execute()
        ids.extend(x["contentDetails"]["videoId"] for x in data.get("items",[]))
        page=data.get("nextPageToken")
        if not page: break
    videos=[]
    for i in range(0,len(ids),50):
        videos+=yt.videos().list(part="snippet,status",id=",".join(ids[i:i+50])).execute().get("items",[])
    return videos
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--package",required=True); ap.add_argument("--credentials-file")
    ap.add_argument("--publish",action="store_true"); args=ap.parse_args()
    folder=Path(args.package); meta=json.loads((folder/"package.json").read_text(encoding="utf-8"))
    presentation=json.loads((folder/"presentation_receipt.json").read_text(encoding="utf-8"))
    if presentation["tts_speed"]!=1.2: raise RuntimeError("Expected 1.2x TTS")
    if not args.publish: raise RuntimeError("Public publishing requires --publish")
    yt,playlist=youtube(args.credentials_file)
    marker=os.getenv("SEOUL_JOURNAL_SLOT_MARKER","")
    schedule=meta.get("publish_at")
    revision=meta.get("revision_of")
    if revision and (revision!="oEZaFVnqKR0" or marker!="SJ_REVISION:oEZaFVnqKR0:motion-v2"):
        raise RuntimeError("Unapproved revision target")
    if schedule and datetime.datetime.fromisoformat(schedule)<=datetime.datetime.now(datetime.timezone.utc):
        raise RuntimeError("Scheduled time must be future")
    def duplicate(old,desc):
        if marker and marker in desc: return True
        return meta["source_url"] in desc and old["id"]!=revision
    for old in recent(yt,playlist):
        desc=old["snippet"].get("description","")
        if duplicate(old,desc):
            print("PUBLIC_DUPLICATE_SKIPPED "+old["id"]); return
    description=meta["description"]+("\n"+marker if marker else "")
    body={"snippet":{"title":meta["youtube_title"][:100],"description":description[:4900],
                     "categoryId":"17" if meta.get("display_category")=="스포츠" else "25","defaultLanguage":"ko","tags":["서울저널","정치시사","Shorts"]},
          "status":{"privacyStatus":"private" if schedule else "public","selfDeclaredMadeForKids":False,**({"publishAt":schedule} if schedule else {})}}
    request=yt.videos().insert(part="snippet,status",body=body,
        media_body=MediaFileUpload(str(folder/"seoul-journal-short.mp4"),mimetype="video/mp4",resumable=True))
    response=None
    while response is None: _,response=request.next_chunk()
    video_id=response["id"]; thumbnail_status="not_set"
    receipt={"video_id":video_id,"url":"https://www.youtube.com/shorts/"+video_id,
             "channel_id":CHANNEL,"source_url":meta["source_url"],"slot_marker":marker,
             "publish_at":schedule,"revision_of":revision,"uploaded_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    # Save insert receipt immediately so retries can investigate a partial result.
    (folder/"public_upload_receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    try:
        yt.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(str(folder/"thumbnail.jpg"),mimetype="image/jpeg")).execute()
        thumbnail_status="api_set"
    except Exception as exc:
        thumbnail_status="not_set_"+type(exc).__name__
    saved=yt.videos().list(part="snippet,status,contentDetails",id=video_id).execute()["items"][0]
    receipt.update({"privacy":saved["status"]["privacyStatus"],"title":saved["snippet"]["title"],
                    "duration":saved["contentDetails"].get("duration"),"thumbnail_status":thumbnail_status})
    if saved["snippet"]["channelId"]!=CHANNEL: raise RuntimeError("Readback channel mismatch")
    (folder/"public_upload_receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PUBLIC_UPLOAD_READBACK "+json.dumps(receipt,ensure_ascii=True),flush=True)
    if schedule:
        actual=saved["status"].get("publishAt")
        if not actual or datetime.datetime.fromisoformat(actual.replace("Z","+00:00"))!=datetime.datetime.fromisoformat(schedule):
            raise RuntimeError("YouTube scheduled time readback mismatch")
        receipt["confirmed_publish_at"]=saved["status"]["publishAt"]
        (folder/"public_upload_receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    elif receipt["privacy"]!="public": raise RuntimeError("YouTube did not permit public visibility; receipt saved")
if __name__=="__main__": main()
