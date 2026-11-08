"""Seoul Journal: original portrait cards, changing captions, central TTS and 1.2x audio."""
import json, os, re, subprocess, shutil, random, hashlib, html, math
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from tts_provider_priority import generate_tts

NAVY=(11,23,48); YELLOW=(255,212,0); RED=(230,59,66); WHITE=(255,255,255)
PORTRAITS={
    "이재명": "File:Lee Jae-myung (2025) (cropped).jpg",
}
def run(args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=300)
    if r.returncode: raise RuntimeError(r.stderr[-1800:])
    return r.stdout
def font(size):
    candidates=["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf","C:/Windows/Fonts/malgunbd.ttf"]
    return ImageFont.truetype(next(p for p in candidates if Path(p).exists()),size)
def wrap(text, size, width):
    f=font(size); lines=[]; line=""
    for c in text:
        if c=="\n" or f.getlength(line+c)>width:
            if line: lines.append(line)
            line="" if c=="\n" else c
        else: line+=c
    if line: lines.append(line)
    return lines
def portrait(text,out):
    # Explicit subject matching; no unrelated faces and no arbitrary publisher photographs.
    name=next((x for x in PORTRAITS if x in text),None)
    if not name: return None,None
    r=requests.get("https://commons.wikimedia.org/w/api.php",params={
        "action":"query","titles":PORTRAITS[name],"prop":"imageinfo",
        "iiprop":"url|extmetadata","format":"json"},headers={"User-Agent":"SeoulJournalEditorial/1.0"},timeout=30)
    r.raise_for_status()
    info=next(iter(r.json()["query"]["pages"].values()))["imageinfo"][0]
    md=info["extmetadata"]; license_name=md.get("LicenseShortName",{}).get("value","")
    if license_name!="Public domain" or md.get("Copyrighted",{}).get("value")!="False":
        raise RuntimeError("Portrait rights changed; stop and review asset")
    image=requests.get(info["url"],headers={"User-Agent":"SeoulJournalEditorial/1.0"},timeout=30)
    image.raise_for_status(); path=out/"licensed-portrait.jpg"; path.write_bytes(image.content)
    record={"subject":name,"url":info["url"],"source":info["descriptionurl"],
            "license":license_name,"credit":"The White House / Emily J. Higgins",
            "date":"2025-08-25","use":"archival portrait; cropped; not current-event footage"}
    (out/"image_rights.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    return path,record
def card(headline,caption,photo,credit,index=0,landscape=False,zoom=1.0,overlay_only=False,category='정치·시사'):
    """Full-frame portrait with transparent text overlays; no opaque news panels."""
    w,h=(1280,720) if landscape else (1080,1920)
    im=Image.new("RGBA" if overlay_only else "RGB",(w,h),(0,0,0,0) if overlay_only else NAVY)
    if photo and not overlay_only:
        source=Image.open(photo).convert("RGB")
        if landscape:
            # Keep the full portrait visible on the right instead of stretching a Short.
            background=ImageOps.fit(source,(w,h),centering=(.5,.4))
            im.paste(Image.blend(background,Image.new("RGB",(w,h),NAVY),.65))
            crop=ImageOps.fit(source,(690,h),centering=(.5,.4))
            im.paste(crop,(590,0))
        else:
            scaled=ImageOps.fit(source,(round(w*zoom),round(h*zoom)),centering=(.5,.4))
            x=(scaled.width-w)//2; y=(scaled.height-h)//2
            im.paste(scaled.crop((x,y,x+w,y+h)))
    d=ImageDraw.Draw(im)
    stroke=(0,0,0)
    def text(x,y,value,size,color=WHITE):
        d.text((x,y),value,font=font(size),fill=color,
               stroke_width=max(2,size//15),stroke_fill=stroke)
    text(35,20,"서울저널",38 if landscape else 48)
    label=(credit["subject"]+" · 자료사진("+credit.get("date","2025")[:4]+")") if credit else "서울저널 자체 제작 그래픽"
    if landscape:
        size=78
        while size>42 and len(wrap(headline,size,570))>4: size-=2
        lines=wrap(headline,size,570)
        if len(lines)>4: raise ValueError("Landscape headline too long")
        for i,line in enumerate(lines):
            text(35,175+i*(size+18),line,size,YELLOW if i==0 else WHITE)
        text(35,640,category+" | "+("승부의 순간" if category=="스포츠" else "쟁점과 반박"),25,YELLOW)
        text(720,668,label,22)
    else:
        # Reserve the bottom and right for YouTube controls; never cover the face.
        text(55,1160,category+" | "+("승부의 순간" if category=="스포츠" else "쟁점과 반박"),34,YELLOW)
        size=82
        while size>48 and len(wrap(headline,size,860))>3: size-=2
        lines=wrap(headline,size,860)
        if len(lines)>3: raise ValueError("Short headline too long")
        for i,line in enumerate(lines):
            text(55,1230+i*(size+18),line,size,YELLOW if i==0 else WHITE)
        caption_size=46
        while caption_size>28 and len(wrap(caption,caption_size,850))>3: caption_size-=2
        caption_lines=wrap(caption,caption_size,850)
        if len(caption_lines)>3: raise ValueError("Split caption into shorter segments")
        for i,line in enumerate(caption_lines):
            text(55,1550+i*(caption_size+15),line,caption_size)
        text(55,1760,label,25)
    return im

ANCHOR_VOICES = (
    {"name":"남성 저음", "edge":"ko-KR-InJoonNeural", "pitch":"-12Hz", "fish_env":"SJ_FISH_MALE_ANCHOR"},
    {"name":"여성 저음", "edge":"ko-KR-SunHiNeural", "pitch":"-8Hz", "fish_env":"SJ_FISH_FEMALE_ANCHOR"},
)
def photo_sequence(meta,out):
    """Use reviewed Commons file titles, or the exact registered subject's named photos."""
    files=meta.get("photo_files", [])
    subject=next((n for n in PORTRAITS if n in meta["youtube_title"]+" "+meta["narration"]),None)
    if not files and subject=="이재명":
        response=requests.get("https://commons.wikimedia.org/w/api.php",params={
            "action":"query","list":"search","srsearch":'intitle:"Lee Jae-myung" filetype:bitmap',
            "srnamespace":6,"srlimit":20,"format":"json"},timeout=30)
        response.raise_for_status()
        files=[PORTRAITS[subject]]+[x["title"] for x in response.json()["query"]["search"]
            if "lee jae-myung" in x["title"].lower()]
    assets=[]; hashes=set()
    for title in dict.fromkeys(files):
        response=requests.get("https://commons.wikimedia.org/w/api.php",params={
            "action":"query","titles":title,"prop":"imageinfo","iiprop":"url|extmetadata|sha1",
            "iiurlwidth":1600,"format":"json"},timeout=30)
        response.raise_for_status()
        page=next(iter(response.json()["query"]["pages"].values()))
        if not page.get("imageinfo"): continue
        info=page["imageinfo"][0]; md=info.get("extmetadata",{})
        license_name=md.get("LicenseShortName",{}).get("value","")
        if license_name not in ("Public domain","CC0","CC BY 4.0","CC BY-SA 4.0","CC BY 3.0","CC BY-SA 3.0"): continue
        if info.get("sha1") in hashes: continue
        image=requests.get(info.get("thumburl",info["url"]),timeout=45); image.raise_for_status()
        digest=hashlib.sha256(image.content).hexdigest()
        if digest in hashes: continue
        path=out/f"photo-{len(assets):02d}.jpg"
        path.write_bytes(image.content)
        with Image.open(path) as check:
            if min(check.size)<400: path.unlink(); continue
        clean=lambda key: html.unescape(re.sub("<[^>]+>","",md.get(key,{}).get("value",""))).strip()
        # Missing dates are explicitly labelled as archival with an unknown date.
        record={"subject":subject or meta.get("visual_subject","자료"),
            "source":info["descriptionurl"],"url":info["url"],"license":license_name,
            "credit":clean("Artist"),"date":clean("DateTimeOriginal") or clean("DateTime") or "촬영일 미상",
            "edits":"cropped, animated zoom, text overlay", "sha256":digest}
        assets.append((path,record)); hashes.update((digest,info.get("sha1")))
        if len(assets)>=5: break
    if len(assets)<3:
        raise RuntimeError("MULTI_PHOTO_REQUIRED: need 3+ distinct cleared subject photos; supply reviewed photo_files")
    (out/"image_rights.json").write_text(json.dumps([r for _,r in assets],ensure_ascii=False,indent=2),encoding="utf-8")
    return assets

def anchor(meta):
    # Stable per-story selection: retries never change voice in the same video.
    seed=int(hashlib.sha256(meta["youtube_title"].encode()).hexdigest(),16)
    voice=dict(ANCHOR_VOICES[seed%len(ANCHOR_VOICES)])
    return voice

def fish(text,path,language,reference_id=None):
    key=os.getenv("FISH_AUDIO_API_KEY","").strip()
    if not key: return False
    r=requests.post("https://api.fish.audio/v1/tts",headers={
        "Authorization":"Bearer "+key,"model":"s2.1-pro-free",
        "Content-Type":"application/json","Accept":"audio/mpeg"},
        json={"text":text,"format":"mp3",**({"reference_id":reference_id} if reference_id else {})},timeout=150)
    if not r.ok or len(r.content)<2000 or r.content.lstrip().startswith(b"{"): return False
    Path(path).write_bytes(r.content); return True
def make(meta,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    assets=photo_sequence(meta,out)
    photo,rights=assets[0]
    voice=anchor(meta)
    def anchor_fish(text,path,language):
        reference=os.getenv(voice["fish_env"],"").strip()
        # Unconfigured Fish default voices do not satisfy the selected anchor profile.
        return fish(text,path,language,reference) if reference else False
    audio=out/"voice-original.mp3"
    tts=generate_tts(meta["narration"],audio,language="ko",fish_generator=anchor_fish, edge_voice=voice["edge"], edge_pitch=voice["pitch"])
    speed=out/"voice-1.2x.m4a"
    run(["ffmpeg","-y","-i",str(audio),"-af","atempo=1.2","-c:a","aac","-b:a","192k",str(speed)])
    duration=float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(speed)]).strip())
    if not 20<=duration<=120: raise RuntimeError("Narration outside Short duration gate: "+str(duration))
    captions=meta.get("captions") or [s.strip() for s in re.split(r"(?<=[.!?。])\s+",meta["narration"]) if s.strip()]
    weights=[max(len(s),1) for s in captions]; total=sum(weights)
    category=meta.get("display_category","정치·시사")
    concat=[]; elapsed=0
    for i,(caption,weight) in enumerate(zip(captions,weights)):
        photo,rights=assets[i%len(assets)]
        seconds=duration*weight/total
        # Animate only the photograph. Typography stays stationary and legible.
        bg=out/f"background-{i:02d}.jpg"
        overlay=out/f"overlay-{i:02d}.png"
        card("","",photo,rights,i,overlay_only=False,category=category).save(bg,quality=94)
        # Background must contain no duplicated typography.
        ImageOps.fit(Image.open(photo).convert("RGB"),(1080,1920),centering=(.5,.4)).save(bg,quality=94)
        card(meta["headline"],caption,None,rights,i,overlay_only=True,category=category).save(overlay)
        frames=max(1,math.ceil(seconds*30))
        z=f"1+0.10*on/{max(frames-1,1)}" if i%2==0 else f"1.10-0.10*on/{max(frames-1,1)}"
        clip=out/f"scene-{i:02d}.mp4"
        run(["ffmpeg","-y","-loop","1","-i",str(bg),"-loop","1","-i",str(overlay),
             "-filter_complex",f"[0:v]scale=2160:3840,zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30[photo];[photo][1:v]overlay=0:0:shortest=1,format=yuv420p[v]",
             "-map","[v]","-t",str(seconds),"-an","-c:v","libx264","-preset","veryfast","-threads","2",str(clip)])
        concat.append("file '"+clip.name+"'"); elapsed+=seconds
    (out/"scenes.txt").write_text("\n".join(concat),encoding="utf-8")
    card(meta["headline"],"",assets[0][0],assets[0][1],landscape=True,category=category).save(out/"thumbnail.jpg",quality=95)
    card(meta["headline"],"",assets[0][0],assets[0][1],category=category).save(out/"cover.jpg",quality=95)
    video=out/"seoul-journal-short.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(out/"scenes.txt"),"-i",str(speed),
         "-c:v","copy","-c:a","aac","-shortest","-movflags","+faststart",str(video)])
    audit={"duration_seconds":duration,"tts_speed":1.2,"tts":tts,"caption_cards":len(captions),
           "photo":assets[0][1],"photos":[r for _,r in assets],"anchor":voice["name"],"motion":"alternating zoom in/out; stationary text","video":str(video),"thumbnail":str(out/"thumbnail.jpg")}
    (out/"presentation_receipt.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PRESENTATION_READY "+json.dumps(audit,ensure_ascii=True),flush=True)
    return video,audit
