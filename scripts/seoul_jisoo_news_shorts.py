#!/usr/bin/env python3
"""Seoul_Jisoo1: source-attributed, original-graphic Korean news Shorts."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlparse

CHANNEL_ID = "UCAizx0tPkRSol8sIhanN_QQ"
KST = dt.timezone(dt.timedelta(hours=9))
CATEGORIES = ("politics", "sports")
AD_DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."


def affiliate_urls():
    found = []
    for category, key in (("건강식품","SEOUL_JISOO_COUPANG_HEALTH_URL"),
                          ("K뷰티","SEOUL_JISOO_COUPANG_BEAUTY_URL")):
        url = os.getenv(key, "").strip()
        if not url:
            continue
        p = urlparse(url)
        # No generic Coupang storefront URLs or invented tracking IDs.
        if p.scheme != "https" or p.hostname not in ("link.coupang.com","coupa.ng") or len(p.path.strip("/")) < 3:
            raise RuntimeError("Unapproved or malformed affiliate link: "+key)
        found.append((category, url))
    return found

def prepare_story(category, out, used_descriptions):
    from seoul_journal_public_daily import candidates, draft, extract
    from seoul_journal_presentation import make, photo_sequence

    out.mkdir(parents=True, exist_ok=True)
    for index, url in enumerate(candidates(category)):
        if index >= 20:
            break
        if url in used_descriptions:
            continue
        try:
            title, body, published_at = extract(url)
        except Exception as exc:
            print("SOURCE_REJECTED", type(exc).__name__, flush=True)
            continue
        story = draft(title, body)
        story["source_title"] = title
        story["display_category"] = "스포츠" if category == "sports" else "정치·시사"
        assets_dir = out / f"assets-{index}"
        assets_dir.mkdir(exist_ok=True)
        try:
            story["_prepared_assets"] = photo_sequence(story, assets_dir)
        except Exception as exc:
            print("PHOTO_REJECTED", type(exc).__name__, flush=True)
            continue
        video, presentation = make(story, out)
        credits = "\n".join(
            f'{photo["subject"]} / {photo["credit"]} / {photo["license"]} / {photo["source"]}'
            for photo in presentation["photos"]
        )
        return video, {
            "title": story["youtube_title"],
            "source": urlparse(url).hostname,
            "source_title": title,
            "link": url,
            "published_at": published_at,
            "description": story["description"] + "\n\n자료사진 (현재 사건 현장 아님)\n" + credits,
        }
    raise RuntimeError("No fresh article with licensed subject photos")


def youtube_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    required = ("YOUTUBE_OAUTH_CLIENT_ID","YOUTUBE_OAUTH_CLIENT_SECRET",
                "YOUTUBE_OAUTH_REFRESH_TOKEN_SHOPPING_SEOUL_JISOO1")
    if any(not os.getenv(k) for k in required):
        raise RuntimeError("YouTube OAuth environment variables unavailable; refusing upload")
    creds = Credentials(token=None,refresh_token=os.environ[required[2]],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ[required[0]],client_secret=os.environ[required[1]],scopes=None)
    svc = build("youtube","v3",credentials=creds,cache_discovery=False)
    channels = svc.channels().list(part="id,contentDetails",mine=True).execute().get("items",[])
    if len(channels)!=1 or channels[0].get("id")!=CHANNEL_ID:
        raise RuntimeError("Authenticated YouTube channel does not match locked Seoul_Jisoo1 ID")
    return svc,channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]

def ensure_not_duplicate(svc,uploads,day,category):
    # YouTube API uses uploader video metadata, check all video titles for both categories today.
    rows = svc.playlistItems().list(part="snippet,contentDetails",playlistId=uploads,maxResults=30).execute().get("items",[])
    for row in rows:
        title = row.get("snippet",{}).get("title","")
        if f"[SJ-{category.upper()}-{day}]" in title:
            raise RuntimeError("Already uploaded this category today, refusing duplicate")

def upload(video, news, category, svc):
    from googleapiclient.http import MediaFileUpload
    day = dt.datetime.now(KST).strftime("%Y%m%d")
    tag = f"[SJ-{category.upper()}-{day}]"
    title = (news["title"][:75] + " #Shorts " + tag)[:100]
    desc = (news["description"]+"\n\n출처: "+news["source"]+"\n보도 제목: "+news["source_title"]+
            "\n원문: "+news["link"]+"\n\n출처를 밝힌 뉴스 제목 요약이며 독자적인 사실 확인이나 지지를 의미하지 않습니다.")
    links = affiliate_urls()
    if links:
        desc += "\n\n[뉴스와 별개인 쇼핑 추천 · 광고·제휴 안내]\n"+AD_DISCLOSURE
        desc += "".join("\n"+label+": "+url for label,url in links)
    body = {"snippet":{"title":title,"description":desc,"categoryId":"25" if category=="politics" else "17",
                       "defaultLanguage":"ko","tags":["SeoulJisoo",category,"Shorts"]},
            "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}}
    media = MediaFileUpload(str(video),mimetype="video/mp4",resumable=True,chunksize=8*1024*1024)
    req = svc.videos().insert(part="snippet,status",body=body,media_body=media)
    result = None
    while result is None:
        _,result=req.next_chunk()
    video_id = result.get("id")
    if not video_id:
        raise RuntimeError("YouTube did not return a video ID")
    # Verify on the authenticated channel, without a second upload on uncertainty.
    check=svc.videos().list(part="snippet,status",id=video_id).execute().get("items",[])
    if len(check)!=1 or check[0]["snippet"]["channelId"]!=CHANNEL_ID:
        raise RuntimeError("Uploaded video channel identity not confirmed, do not retry")
    actual_privacy=check[0]["status"]["privacyStatus"]
    if actual_privacy != "public":
        raise RuntimeError("Video uploaded but public status not confirmed; do not retry blindly")
    return {"video_id":video_id,"url":"https://www.youtube.com/shorts/"+video_id,
            "privacy":actual_privacy,"source":news["source"],
            "category":category}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--category",choices=CATEGORIES,required=True)
    ap.add_argument("--upload",action="store_true")
    ap.add_argument("--outdir",default="artifacts/seoul-jisoo-shorts")
    args=ap.parse_args()
    day=dt.datetime.now(KST).strftime("%Y-%m-%d")
    out=Path(args.outdir)/day/args.category
    urls=affiliate_urls()
    print("AFFILIATE_APPROVED_LINKS",len(urls),flush=True)
    svc=None
    used_descriptions = ""
    if args.upload:
        if os.getenv("SEOUL_JISOO_SHORTS_LIVE","false").lower()!="true":
            raise RuntimeError("Live publishing disabled by environment variable")
        svc,uploads=youtube_service()
        ensure_not_duplicate(svc,uploads,day,args.category)
        from seoul_journal_publish_package import recent
        used_descriptions = "\n".join(
            item["snippet"].get("description", "") for item in recent(svc, uploads)
        )
    video, news = prepare_story(args.category, out, used_descriptions)
    manifest={"category":args.category,"day":day,"news":news,"video":str(video),
              "affiliate_link_count":len(urls),"status":"PREPARED"}
    if args.upload:
        try:
            receipt=upload(video,news,args.category,svc)
            manifest.update(status="PUBLISHED",receipt=receipt)
            print("PUBLISH_OK",json.dumps(receipt,ensure_ascii=False),flush=True)
        except Exception as e:
            manifest.update(status="UNKNOWN_UPLOAD_OUTCOME",error=str(e)[:180])
            raise
        finally:
            (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    else:
        (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        print("DRY_RUN_OK",str(video),flush=True)
if __name__=="__main__":
    main()
