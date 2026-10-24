#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one source-grounded Seoul Journal political Short and upload PRIVATE only."""
import os, re, json, textwrap, subprocess, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests, trafilatura
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT=Path.cwd()
OUT=ROOT/"artifacts"/"seoul-journal-short"
OUT.mkdir(parents=True,exist_ok=True)
NAVER_POLITICS="https://news.naver.com/section/100"
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

def log(s): print(s,flush=True)

def choose_naver_article():
    r=requests.get(NAVER_POLITICS,headers=UA,timeout=25); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    candidates=[]
    for a in soup.select('a[href*="n.news.naver.com/mnews/article/"], a[href*="n.news.naver.com/article/"]'):
        href=a.get("href","")
        title=" ".join(a.get_text(" ",strip=True).split())
        if len(title)<12 or "naver.com" not in href: continue
        if any(x["url"]==href for x in candidates): continue
        candidates.append({"url":href,"title":title})
    if not candidates:
        raise RuntimeError("네이버 정치 섹션에서 기사 URL을 자동 추출하지 못했습니다. workflow_dispatch에 article_url을 입력해 주세요.")
    # Naver section card order is used as a prominence heuristic, not a verified view-count ranking.
    return candidates[0]["url"], candidates[0]["title"], "Naver Politics section first eligible card (not verified by view count)"

def extract(url):
    p=urlparse(url)
    if p.scheme not in ("https","http") or not p.netloc or "naver.com" not in p.netloc.lower():
        raise RuntimeError("기사 URL은 네이버 뉴스 URL이어야 합니다.")
    r=requests.get(url,headers=UA,timeout=25); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    title=(soup.select_one("#title_area") or soup.select_one("h2") or soup.title)
    title=" ".join(title.get_text(" ",strip=True).split()) if title else ""
    text=trafilatura.extract(r.text,include_comments=False,include_tables=False)
    og=soup.find("meta",property="og:image")
    image_url=og.get("content","") if og else ""
    if not text or len(text)<300: raise RuntimeError("기사 본문 추출 실패/본문 부족. 접근 제한 기사일 수 있습니다.")
    return title,text,image_url

def draft(title,body):
    key=os.getenv("OPENAI_API_KEY","").strip()
    if not key: raise RuntimeError("OPENAI_API_KEY GitHub Actions secret이 없습니다.")
    prompt=f"""당신은 서울저널의 한국어 정치 뉴스 기자 겸 팩트체커입니다.
기사 제목: {title}
기사 본문:
{body[:12000]}

약 55~60초 세로 쇼츠 패키지를 작성하세요. 내레이션은 공백 포함 한국어 450~650자 정도로 충분히 작성하고, 최소 4개의 짧은 문단으로 구성하세요. 첫 문장은 핵심 사실을 바로 제시하고, 중간에는 기사에 나온 배경·당사자 발언·확인된 사실을 구체적으로 설명하며, 마지막에는 확인된 사실과 아직 확인되지 않은 점을 구분하고 '서울저널이 알려드립니다. 여러분은 어떻게 생각하십니까?'로 마무리하세요. 기사에 없는 사실을 채우기 위해 분량을 늘리지 마세요. 결과는 JSON 객체 하나:
{{"headline":"썸네일용 10~18자 헤드라인","youtube_title":"사실에 근거한 제목 100자 이내","narration":"공백 포함 450~650자, 약 55~60초 분량의 자연스러운 한국어 기자 내레이션","description":"기사 핵심을 중립적으로 요약하고 원문 출처가 들어갈 자리 [원문 기사]를 포함한 설명","source_note":"기사에서 확인한 핵심 사실과 확인 한계"}}
규칙:
- 기사 본문에 있는 정보만 말한다. 논평·주장은 발언자에게 귀속한다.
- 혐의/의혹/수사/재판/여론조사는 확정 사실로 과장하지 않는다.
- 강한 호기심은 만들되 허위·모욕·선동적 프레이밍을 쓰지 않는다.
- 헤드라인은 모바일에서 크게 읽히도록 짧게 작성한다.
- 발언을 직접 인용할 때 원문과 일치하는 표현만 사용한다.
- JSON 이외 텍스트 금지."""
    client=OpenAI(api_key=key)
    res=client.chat.completions.create(model=os.getenv("SEOUL_JOURNAL_MODEL","gpt-4o-mini"),temperature=0.35,
       messages=[{"role":"system","content":"Return valid JSON only. Be factually conservative."},{"role":"user","content":prompt}])
    raw=res.choices[0].message.content.strip()
    raw=re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$","",raw)
    data=json.loads(raw)
    data["narration"]=data["narration"].strip()
    if len(data["narration"])<420: raise RuntimeError(f"생성된 내레이션이 너무 짧습니다: {len(data['narration'])}자 (최소 420자). 대본을 다시 생성해야 합니다.")
    return data

def tts(text):
    """Prefer Fish Audio S2.1 Pro Free when configured; fall back to free Edge TTS."""
    import asyncio
    p=OUT/"voice.mp3"
    fish_key=os.getenv("FISH_AUDIO_API_KEY","").strip()
    if fish_key:
        import requests
        model=os.getenv("FISH_AUDIO_MODEL","s2.1-pro-free").strip()
        reference_id=os.getenv("FISH_AUDIO_REFERENCE_ID","933563129e564b19a115bedd57b7406a").strip()
        try:
            r=requests.post(
                "https://api.fish.audio/v1/tts",
                headers={"Authorization":f"Bearer {fish_key}","Content-Type":"application/json","model":model},
                json={"text":text,"reference_id":reference_id,"format":"mp3"},
                timeout=120,
            )
            if r.ok and len(r.content)>2000:
                p.write_bytes(r.content)
                log(f"TTS_ENGINE=fish-audio model={model} bytes={p.stat().st_size}")
                return p
            log(f"Fish Audio failed HTTP {r.status_code}; falling back to Edge TTS.")
        except Exception as e:
            log(f"Fish Audio request failed ({e}); falling back to Edge TTS.")
    else:
        log("FISH_AUDIO_API_KEY not configured; using free Edge TTS fallback.")
    import edge_tts
    voice=os.getenv("SEOUL_JOURNAL_EDGE_VOICE","ko-KR-SunHiNeural").strip()
    rate=os.getenv("SEOUL_JOURNAL_TTS_RATE","+15%").strip()
    async def generate():
        await edge_tts.Communicate(text=text,voice=voice,rate=rate).save(str(p))
    try:
        asyncio.run(generate())
    except Exception as e:
        raise RuntimeError(f"Free Edge TTS failed ({voice}): {e}") from e
    if not p.exists() or p.stat().st_size<2000:
        raise RuntimeError("Generated TTS audio is missing or too small.")
    log(f"TTS_ENGINE=edge-tts voice={voice} rate={rate} bytes={p.stat().st_size}")
    return p

def fetch_photo(image_url):
    if not image_url: return None
    try:
        r=requests.get(image_url,headers=UA,timeout=20); r.raise_for_status()
        p=OUT/"article-photo"
        p.write_bytes(r.content)
        from PIL import Image
        im=Image.open(p).convert("RGB")
        im.save(OUT/"photo.jpg",quality=92)
        return OUT/"photo.jpg"
    except Exception as e:
        log(f"Image unavailable; using branded background: {e}")
        return None

def render(headline,photo,audio):
    W,H=1080,1920
    base=Image.new("RGB",(W,H),(12,20,34))
    if photo:
        try:
            im=Image.open(photo).convert("RGB")
            scale=max(W/im.width,1250/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
            x=(im.width-W)//2; y=max(0,(im.height-1250)//2)
            base.paste(im.crop((x,y,x+W,y+1250)),(0,0))
            # dark overlay on photo for legibility
            overlay=Image.new("RGBA",(W,1250),(5,10,20,78)); base.paste(overlay,(0,0),overlay)
        except Exception: pass
    draw=ImageDraw.Draw(base)
    navy=(15,35,61); yellow=(255,214,10); red=(235,35,55); white=(255,255,255)
    draw.rectangle((0,0,W,115),fill=navy)
    draw.rectangle((0,115,W,130),fill=red)
    font_paths=[
      "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
      "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    fp=next((p for p in font_paths if os.path.exists(p)),None)
    try:
        logo=ImageFont.truetype(fp,43); title_font=ImageFont.truetype(fp,94); foot=ImageFont.truetype(fp,33)
    except Exception: logo=title_font=foot=ImageFont.load_default()
    draw.text((54,28),"SEOUL JOURNAL  |  정치 뉴스",font=logo,fill=white,stroke_width=1,stroke_fill=navy)
    draw.rectangle((0,1240,W,H),fill=navy)
    draw.rectangle((0,1240,22,H),fill=red)
    # big, readable headline blocks; each line is short enough for mobile
    chars=10
    lines=textwrap.wrap(headline,width=chars,break_long_words=True,replace_whitespace=False)
    y=1325
    for idx,line in enumerate(lines[:4]):
        color=yellow if idx==0 else white
        draw.text((58,y),line,font=title_font,fill=color,stroke_width=3,stroke_fill=(0,0,0))
        y+=122
    draw.rectangle((58,1770,1020,1778),fill=red)
    draw.text((58,1810),"원문과 공식 자료를 확인하세요",font=foot,fill=(220,230,242))
    still=OUT/"cover.jpg"; base.save(still,quality=94)
    ffmpeg=os.getenv("FFMPEG_BINARY","ffmpeg")
    video=OUT/"seoul-journal-short.mp4"
    cmd=[ffmpeg,"-y","-loop","1","-i",str(still),"-i",str(audio),"-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p","-c:v","libx264","-preset","medium","-tune","stillimage","-af","atempo=1.2","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(video)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
    if p.returncode: raise RuntimeError("FFmpeg 렌더링 실패: "+p.stderr[-1200:])
    return video

def upload_private(video,meta,source_url):
    client_id=os.getenv("YOUTUBE_OAUTH_CLIENT_ID","").strip()
    client_secret=os.getenv("YOUTUBE_OAUTH_CLIENT_SECRET","").strip()
    refresh=os.getenv("SEOUL_JOURNAL_YOUTUBE_OAUTH_REFRESH_TOKEN","").strip()
    expected=os.getenv("SEOUL_JOURNAL_YOUTUBE_CHANNEL_ID","").strip()
    if not all([client_id,client_secret,refresh,expected]):
        raise RuntimeError("YouTube 안전 업로드 차단: YOUTUBE_OAUTH_CLIENT_ID/SECRET 및 SEOUL_JOURNAL_YOUTUBE_OAUTH_REFRESH_TOKEN, SEOUL_JOURNAL_YOUTUBE_CHANNEL_ID 중 하나 이상 누락. 계정이 다른 채널일 수 있어 업로드하지 않았습니다.")
    creds=Credentials(token=None,refresh_token=refresh,token_uri="https://oauth2.googleapis.com/token",
      client_id=client_id,client_secret=client_secret,scopes=["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube.readonly"])
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    ch=yt.channels().list(part="snippet",mine=True).execute()
    items=ch.get("items",[])
    if len(items)!=1 or items[0]["id"]!=expected:
        got=items[0]["id"] if items else "NO_CHANNEL"
        name=items[0]["snippet"]["title"] if items else "NO_CHANNEL"
        raise RuntimeError(f"채널 ID 검증 실패: 인증 채널={name} ({got}); 예상 채널과 일치하지 않아 업로드 중단.")
    description=(meta["description"].replace("[원문 기사]",source_url)+"\n\n원문 기사: "+source_url+"\n\n#Shorts #서울저널 #정치뉴스")
    body={"snippet":{"title":meta["youtube_title"][:100],"description":description[:4900],"categoryId":"25","tags":["서울저널","정치뉴스","대한민국정치","Shorts"]},
          "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}}
    req=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(video),mimetype="video/mp4",resumable=True,chunksize=5*1024*1024))
    response=None
    while response is None:
        _,response=req.next_chunk()
    return {"video_id":response["id"],"url":"https://studio.youtube.com/video/"+response["id"]+"/edit","privacy":"private","channel_title":items[0]["snippet"]["title"],"channel_id":items[0]["id"]}

def main():
    url=os.getenv("INPUT_ARTICLE_URL","").strip()
    if not url:
        url,title_hint,selection=choose_naver_article()
        log(f"Auto-selected from Naver Politics: {url} ({selection})")
    else:
        title_hint=""; selection="User-supplied Naver article URL"
    title,body,img=extract(url)
    if title_hint and len(title)<8: title=title_hint
    meta=draft(title,body)
    meta["source_title"]=title; meta["source_url"]=url; meta["article_selection_method"]=selection
    (OUT/"package.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"narration.txt").write_text(meta["narration"],encoding="utf-8")
    log("SCRIPT_READY: "+meta["youtube_title"])
    audio=tts(meta["narration"])
    photo=fetch_photo(img)
    video=render(meta["headline"],photo,audio)
    log("VIDEO_RENDERED: "+str(video))
    result=upload_private(video,meta,url)
    (OUT/"upload_receipt.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    log("YOUTUBE_PRIVATE_UPLOADED: "+json.dumps(result,ensure_ascii=False))
    log("Owner review required in YouTube Studio before making public.")
if __name__=="__main__":
    try: main()
    except Exception as e:
        log("FAILED: "+str(e)); sys.exit(1)
