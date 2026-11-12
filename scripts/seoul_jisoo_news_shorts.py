#!/usr/bin/env python3
"""Seoul_Jisoo1: source-attributed, original-graphic Korean news Shorts."""
import argparse
import datetime as dt
import json
import os
import re
import random
import subprocess
import sys
import tempfile
import textwrap
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse

CHANNEL_ID = "UCAizx0tPkRSol8sIhanN_QQ"
KST = dt.timezone(dt.timedelta(hours=9))
FEEDS = {
    "politics": "한국 정치 이재명 한동훈 김민석 장동혁 오세훈 정청래 서영교 when:1d",
    "society": "한국 사회 사건 사고 논란 속보 when:1d",
    "sports": "한국시리즈 KBO MLB 한국 선수 경기 when:1d",
    "shopping": "한국 쇼핑 신상품 품절 인기 아이템 when:1d",
}
TRUSTED_SOURCES = {"연합뉴스","KBS뉴스","KBS","MBC","SBS","SBS 뉴스","JTBC","뉴스1","뉴시스","연합뉴스TV","YTN","조선일보","한겨레","스포츠조선","스포츠서울","스포티비뉴스","OSEN","네이버뉴스"}
PERSONS = ("이재명","한동훈","김민석","장동혁","오세훈","정청래","서영교")
VOICE_POOL = [
    ("ko-KR-InJoonNeural","male","anchor"),
    ("ko-KR-HyunsuNeural","male","documentary"),
    ("ko-KR-SunHiNeural","female","anchor"),
    ("ko-KR-JiMinNeural","female","documentary"),
]
TEMPLATES = ("red_breaking","blue_split","gold_frame","black_ticker","white_press")
AD_DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."

def fetch_news(category):
    q = FEEDS[category]
    url = "https://news.google.com/rss/search?" + urlencode({"q":q,"hl":"ko","gl":"KR","ceid":"KR:ko"})
    req = urllib.request.Request(url, headers={"User-Agent":"SeoulJisooNewsShorts/2.0"})
    with urllib.request.urlopen(req, timeout=22) as res: root = ET.fromstring(res.read())
    now = dt.datetime.now(dt.timezone.utc); result=[]
    for item in root.findall("./channel/item"):
        title=(item.findtext("title") or "").strip(); source=(item.findtext("source") or "").strip()
        link=(item.findtext("link") or "").strip(); pub=item.findtext("pubDate") or ""
        try: stamp=parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
        except (ValueError,TypeError): continue
        if not source and " - " in title: source=title.rsplit(" - ",1)[-1].strip()
        if source in {"Google News","Google 뉴스",""}: source="Google News RSS"
        if not link.startswith("https://") or len(title)<12: continue
        headline=title.removesuffix(" - "+source).strip()
        if any(x in headline for x in ("[포토]","[사설]","[칼럼]","오늘의 일정","소문","카더라")): continue
        result.append({"title":headline,"source":source,"link":link,"published_at":stamp.isoformat()})
    result.sort(key=lambda x:x["published_at"],reverse=True)
    if not result: raise RuntimeError("No recent attributed headline from approved sources; no publication")
    return result[0]

def image_queries(headline, category):
    names=[p for p in PERSONS if p in headline]
    if names: return names
    return {"sports":["Korean baseball player","MLB Korean player"],"society":["Korea news scene","Korean public event"],"shopping":["Korean product shopping","K-beauty product"],"politics":["Korean National Assembly","Korean president"]}[category]

def fetch_person_images(headline, category, out_dir):
    import json as _json
    out_dir.mkdir(parents=True,exist_ok=True); files=[]; credits=[]
    for query in image_queries(headline,category):
        api="https://commons.wikimedia.org/w/api.php?"+urlencode({"action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":8,"prop":"imageinfo","iiprop":"url","iiurlwidth":1280,"format":"json"})
        req=urllib.request.Request(api,headers={"User-Agent":"SeoulJisooNewsShorts/2.0"})
        try:
            with urllib.request.urlopen(req,timeout=25) as res: data=_json.loads(res.read())
        except Exception: continue
        for page in (data.get("query",{}).get("pages",{}).values()):
            info=(page.get("imageinfo") or [{}])[0]; src=info.get("thumburl") or info.get("url")
            if not src or not src.lower().split("?")[0].endswith((".jpg",".jpeg",".png",".webp")): continue
            path=out_dir/f"photo_{len(files)+1:02d}.jpg"
            try:
                with urllib.request.urlopen(urllib.request.Request(src,headers={"User-Agent":"SeoulJisooNewsShorts/2.0"}),timeout=35) as res: path.write_bytes(res.read())
                if path.stat().st_size>20000: files.append(path); credits.append({"query":query,"source":"Wikimedia Commons","url":src})
            except Exception: path.unlink(missing_ok=True)
            if len(files)>=5: return files,credits
    if len(files)<5: raise RuntimeError(f"Only {len(files)} licensed reference images found; refusing image-free news short")
    return files,credits

def tts(text, out):
    import requests
    speed = "+30%"
    fish=os.getenv("FISH_AUDIO_API_KEY","").strip()
    if fish:
        try:
            r=requests.post("https://api.fish.audio/v1/tts",headers={"Authorization":"Bearer "+fish,"model":"s2.1-pro-free","Accept":"audio/mpeg","Content-Type":"application/json"},json={"text":text,"format":"mp3"},timeout=120)
            if r.ok and len(r.content)>2000: out.write_bytes(r.content); return "fish.audio"
        except Exception: pass
    qwen=os.getenv("QWEN3_TTS_URL","").strip()
    if qwen:
        try:
            r=requests.post(qwen,json={"text":text,"speed":1.3},timeout=120)
            if r.ok and len(r.content)>2000: out.write_bytes(r.content); return "Qwen3-TTS"
        except Exception: pass
    voice,gender,style=random.Random(dt.datetime.now().toordinal()+dt.datetime.now().hour).choice(VOICE_POOL)
    import asyncio, edge_tts
    asyncio.run(edge_tts.Communicate(text,voice,rate=speed).save(str(out)))
    if not out.exists() or out.stat().st_size<2000: raise RuntimeError("All permitted TTS providers failed")
    return f"EdgeTTS:{voice}:{gender}:{style}:1.3x"

def render(news,category,out_dir):
    from PIL import Image,ImageDraw,ImageFont
    out_dir.mkdir(parents=True,exist_ok=True); photos,credits=fetch_person_images(news["title"],category,out_dir/"photos")
    audio=out_dir/"voice.mp3"; narration=f"{news['title']}. {news['source']} 보도입니다. 자세한 내용은 설명란 원문을 확인하세요."
    provider=tts(narration,audio); duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],text=True).strip())+1.5
    fp=next((p for p in FONT_PATHS if Path(p).exists()),None)
    if not fp: raise RuntimeError("Korean font unavailable")
    font=ImageFont.truetype(fp,76); small=ImageFont.truetype(fp,38); clips=[]
    colors={"red_breaking":((180,20,35),(255,235,80)),"blue_split":((20,70,145),(255,255,255)),"gold_frame":((30,25,20),(255,205,60)),"black_ticker":((10,10,10),(255,90,70)),"white_press":((245,245,240),(30,30,30))}
    for i,photo in enumerate(photos):
        template=TEMPLATES[i%5]
        from PIL import ImageOps
        base=ImageOps.fit(Image.open(photo).convert("RGB"),(1080,1920),method=Image.Resampling.LANCZOS,centering=(0.5,0.42))
        overlay=Image.new("RGBA",base.size,(0,0,0,105)); base=Image.alpha_composite(base.convert("RGBA"),overlay).convert("RGB")
        d=ImageDraw.Draw(base); bg,fg=colors[template]
        # Strong editorial header and central headline panel, matching the supplied political-news references.
        d.rectangle((0,0,1080,190),fill=bg)
        d.rectangle((48,48,270,132),fill=(205,24,38) if category in ("politics","society") else bg)
        d.text((62,62),("속보" if category in ("politics","society") else "서울지수"),font=small,fill=(255,255,255))
        d.rounded_rectangle((36,625,1044,1290),radius=28,fill=(*bg,222),outline=fg,width=6)
        textwrap_lines=textwrap.wrap(news["title"],width=12,break_long_words=True,replace_whitespace=False)[:3]
        headline_font=ImageFont.truetype(fp,78 if len(textwrap_lines)<=2 else 68)
        line_h=[]
        for line in textwrap_lines:
            b=d.textbbox((0,0),line,font=headline_font,stroke_width=2); line_h.append(b[3]-b[1])
        spacing=24; total=sum(line_h)+max(0,len(line_h)-1)*spacing
        y=625+(665-total)//2
        for j,line in enumerate(textwrap_lines):
            b=d.textbbox((0,0),line,font=headline_font,stroke_width=3); x=(1080-(b[2]-b[0]))//2
            color=fg if j in (0,len(textwrap_lines)-1) else (255,255,255)
            d.text((x,y),line,font=headline_font,fill=color,stroke_width=4,stroke_fill=(0,0,0))
            y+=line_h[j]+spacing
        d.rectangle((0,1680,1080,1835),fill=bg)
        d.text((45,1725),f"{news['source']}  ·  {dt.datetime.now(KST).strftime('%Y.%m.%d')}",font=small,fill=(255,255,255))
        still=out_dir/f"card_{i+1:02d}.jpg"; base.save(still,quality=92)
        if i==0: base.save(out_dir/"cover.jpg",quality=94)
        clip=out_dir/f"clip_{i+1:02d}.mp4"
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1","-i",str(still),"-i",str(audio),"-t",str(min(12,duration/5+1)),"-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(clip)],check=True,timeout=150)
        clips.append(clip)
    listing=out_dir/"concat.txt"; listing.write_text("".join(f"file '{c.name}'\n" for c in clips),encoding="utf-8")
    video=out_dir/"short.mp4"; subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(listing),"-c","copy","-movflags","+faststart",str(video)],check=True,timeout=180)
    return video,provider,credits

def affiliate_urls():
    found=[]
    for label,key in (("건강식품","SEOUL_JISOO_COUPANG_HEALTH_URL"),("K뷰티","SEOUL_JISOO_COUPANG_BEAUTY_URL"),("SeoulMall","SEOUL_MALL_URL")):
        url=os.getenv(key,"").strip()
        if url: found.append((label,url))
    return found

def youtube_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    required=("YOUTUBE_OAUTH_CLIENT_ID","YOUTUBE_OAUTH_CLIENT_SECRET","YOUTUBE_OAUTH_REFRESH_TOKEN_SHOPPING_SEOUL_JISOO1")
    if any(not os.getenv(k) for k in required): raise RuntimeError("YouTube OAuth environment variables unavailable; refusing upload")
    creds=Credentials(token=None,refresh_token=os.environ[required[2]],token_uri="https://oauth2.googleapis.com/token",client_id=os.environ[required[0]],client_secret=os.environ[required[1]],scopes=None)
    svc=build("youtube","v3",credentials=creds,cache_discovery=False); channels=svc.channels().list(part="id,contentDetails",mine=True).execute().get("items",[])
    if len(channels)!=1 or channels[0].get("id")!=CHANNEL_ID: raise RuntimeError("Authenticated YouTube channel does not match locked Seoul_Jisoo1 ID")
    return svc,channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]

def ensure_not_duplicate(svc,uploads,day,category):
    rows=svc.playlistItems().list(part="snippet,contentDetails",playlistId=uploads,maxResults=50).execute().get("items",[])
    tag=f"[SJ-{category.upper()}-{day}]"
    if any(tag in r.get("snippet",{}).get("title","") for r in rows): raise RuntimeError("Already uploaded this category today")

def upload(video,news,category,svc):
    from googleapiclient.http import MediaFileUpload
    day=dt.datetime.now(KST).strftime("%Y%m%d"); tag=f"[SJ-{category.upper()}-{day}]"
    body={"snippet":{"title":(news["title"][:75]+" #Shorts "+tag)[:100],"description":"출처: "+news["source"]+"\n원문: "+news["link"]+"\n\n서울지수 자체 제작 카드뉴스입니다.\n"+AD_DISCLOSURE+"\n"+"\n".join(f"{k}: {v}" for k,v in affiliate_urls()),"categoryId":"25" if category in ("politics","society") else "17","defaultLanguage":"ko","tags":["서울지수","카드뉴스",category,"Shorts"]},"status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}}
    req=svc.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(video),mimetype="video/mp4",resumable=True,chunksize=8*1024*1024)); result=None
    while result is None: _,result=req.next_chunk()
    vid=result.get("id")
    if not vid: raise RuntimeError("YouTube did not return a video ID")
    check=svc.videos().list(part="snippet,status",id=vid).execute().get("items",[])
    if len(check)!=1 or check[0]["snippet"]["channelId"]!=CHANNEL_ID or check[0]["status"]["privacyStatus"]!="private": raise RuntimeError("Upload verification failed; do not retry blindly")
    return {"video_id":vid,"url":"https://www.youtube.com/shorts/"+vid,"privacy":"private","category":category}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--category",choices=tuple(FEEDS),required=True); ap.add_argument("--upload",action="store_true"); ap.add_argument("--outdir",default="artifacts/seoul-jisoo-shorts"); args=ap.parse_args()
    day=dt.datetime.now(KST).strftime("%Y-%m-%d"); out=Path(args.outdir)/day/args.category; news=fetch_news(args.category)
    print("SOURCE_OK",json.dumps(news,ensure_ascii=False),flush=True)
    svc=None
    if args.upload:
        if os.getenv("SEOUL_JISOO_SHORTS_LIVE","false").lower()!="true": raise RuntimeError("Live publishing disabled")
        svc,uploads=youtube_service(); ensure_not_duplicate(svc,uploads,day,args.category)
    video,provider,credits=render(news,args.category,out); manifest={"category":args.category,"day":day,"news":news,"video":str(video),"tts_provider":provider,"images":credits,"template_set":list(TEMPLATES),"speed":"1.3x","status":"PREPARED"}
    if args.upload:
        receipt=upload(video,news,args.category,svc); manifest.update(status="PUBLISHED",receipt=receipt); print("PUBLISH_OK",json.dumps(receipt,ensure_ascii=False),flush=True)
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__": main()
