#!/usr/bin/env python3
"""Seoul_Jisoo1: source-attributed, original-graphic Korean news Shorts."""
import argparse
import datetime as dt
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse

from seoul_journal_presentation import make, wrap

CHANNEL_ID = "UCAizx0tPkRSol8sIhanN_QQ"
KST = dt.timezone(dt.timedelta(hours=9))
FEEDS = {
    "politics": "https://news.google.com/rss/search?" + urlencode(
        {"q":"한국 정치 국회 정부 when:1d","hl":"ko","gl":"KR","ceid":"KR:ko"}),
    "sports": "https://news.google.com/rss/search?" + urlencode(
        {"q":"한국 스포츠 경기 선수 when:1d","hl":"ko","gl":"KR","ceid":"KR:ko"}),
}
TRUSTED_SOURCES = {
    "연합뉴스","KBS뉴스","KBS","MBC","SBS","SBS 뉴스","JTBC",
    "뉴스1","뉴시스","BBC News 코리아","Reuters","AP News","스포츠조선",
    "스포츠서울","스포티비뉴스","OSEN","연합뉴스TV","YTN",
}
AD_DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."

def fetch_news(category):
    url = FEEDS[category]
    req = urllib.request.Request(url, headers={"User-Agent":"SeoulJisooNewsShorts/1.0"})
    with urllib.request.urlopen(req, timeout=22) as res:
        root = ET.fromstring(res.read())
    now = dt.datetime.now(dt.timezone.utc)
    result = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or ""
        try:
            stamp = parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
        except (ValueError, TypeError):
            continue
        if not source and " - " in title:
            source = title.rsplit(" - ", 1)[-1].strip()
        if source not in TRUSTED_SOURCES:
            continue
        if not (0 <= (now-stamp).total_seconds() <= 36 * 3600):
            continue
        if not link.startswith("https://") or len(title) < 15:
            continue
        headline = title.removesuffix(" - " + source).strip()
        if any(x in headline for x in ("속보?", "소문", "카더라", "충격 예언", "주요일정", "오늘의 일정", "오늘의 포토", "[포토]", "[사설]", "[칼럼]")):
            continue
        result.append({"title":headline, "source":source, "link":link,
                       "published_at":stamp.isoformat()})
    # Choose deterministic recent item to avoid a different item on retry.
    result.sort(key=lambda x:x["published_at"], reverse=True)
    if not result:
        raise RuntimeError("No recent attributed headline from approved sources; no publication")
    return result[0]

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

def render(headline, source, category, out_dir):
    narration = f"{headline}. {source} 보도입니다. 자세한 내용은 영상 설명의 원문에서 확인할 수 있습니다."
    meta = {
        "source_title": headline,
        "youtube_title": headline,
        "headline": "\n".join(wrap(headline, 48, 860)[:3]),
        "narration": narration,
        "captions": [f"{source} 보도", "자세한 내용은 원문에서", "원문 링크는 영상 설명에"],
        "display_category": "스포츠" if category == "sports" else "정치·시사",
    }
    return make(meta, out_dir, minimum_duration=4, brand="서울지수")


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

def upload(video, news, category, svc, photos):
    from googleapiclient.http import MediaFileUpload
    day = dt.datetime.now(KST).strftime("%Y%m%d")
    tag = f"[SJ-{category.upper()}-{day}]"
    title = (news["title"][:75] + " #Shorts " + tag)[:100]
    desc = ("출처: "+news["source"]+"\n보도 제목: "+news["title"]+
            "\n원문: "+news["link"]+"\n\n출처를 밝힌 뉴스 제목 요약이며 독자적인 사실 확인이나 지지를 의미하지 않습니다.")
    desc += "\n\n자료사진 (크롭·줌·텍스트 삽입)\n" + "\n".join(
        f"{photo['credit']} · {photo['license']} · {photo['source']}" for photo in photos
    )
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
    ap.add_argument("--category",choices=tuple(FEEDS),required=True)
    ap.add_argument("--upload",action="store_true")
    ap.add_argument("--outdir",default="artifacts/seoul-jisoo-shorts")
    args=ap.parse_args()
    day=dt.datetime.now(KST).strftime("%Y-%m-%d")
    out=Path(args.outdir)/day/args.category
    news=fetch_news(args.category)
    urls=affiliate_urls()
    print("SOURCE_OK",json.dumps({k:news[k] for k in ("title","source","published_at")},ensure_ascii=False),flush=True)
    print("AFFILIATE_APPROVED_LINKS",len(urls),flush=True)
    svc=None
    if args.upload:
        if os.getenv("SEOUL_JISOO_SHORTS_LIVE","false").lower()!="true":
            raise RuntimeError("Live publishing disabled by environment variable")
        svc,uploads=youtube_service()
        ensure_not_duplicate(svc,uploads,day,args.category)
    video,audit=render(news["title"],news["source"],args.category,out)
    manifest={"category":args.category,"day":day,"news":news,"video":str(video),
              "presentation":audit,"affiliate_link_count":len(urls),"status":"PREPARED"}
    if args.upload:
        try:
            receipt=upload(video,news,args.category,svc,audit['photos'])
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
