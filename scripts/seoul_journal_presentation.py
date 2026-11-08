"""Seoul Journal: original portrait cards, changing captions, central TTS and 1.2x audio."""
import json, os, re, subprocess, shutil
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
def card(headline,caption,photo,credit,index=0,landscape=False):
    """Full-frame portrait with transparent text overlays; no opaque news panels."""
    w,h=(1280,720) if landscape else (1080,1920)
    im=Image.new("RGB",(w,h),NAVY)
    if photo:
        source=Image.open(photo).convert("RGB")
        if landscape:
            # Keep the full portrait visible on the right instead of stretching a Short.
            background=ImageOps.fit(source,(w,h),centering=(.5,.4))
            im.paste(Image.blend(background,Image.new("RGB",(w,h),NAVY),.65))
            crop=ImageOps.fit(source,(690,h),centering=(.5,.4))
            im.paste(crop,(590,0))
        else:
            im.paste(ImageOps.fit(source,(w,h),centering=(.5,.4)))
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
        text(35,640,"정치·시사 | 쟁점과 반박",25,YELLOW)
        text(720,668,label,22)
    else:
        # Reserve the bottom and right for YouTube controls; never cover the face.
        text(55,1160,"정치·시사 | 쟁점과 반박",34,YELLOW)
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
def fish(text,path,language):
    key=os.getenv("FISH_AUDIO_API_KEY","").strip()
    if not key: return False
    r=requests.post("https://api.fish.audio/v1/tts",headers={
        "Authorization":"Bearer "+key,"model":"s2.1-pro-free",
        "Content-Type":"application/json","Accept":"audio/mpeg"},
        json={"text":text,"format":"mp3"},timeout=150)
    if not r.ok or len(r.content)<2000 or r.content.lstrip().startswith(b"{"): return False
    Path(path).write_bytes(r.content); return True
def make(meta,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    photo,rights=portrait(meta["youtube_title"]+" "+meta["narration"],out)
    audio=out/"voice-original.mp3"
    tts=generate_tts(meta["narration"],audio,language="ko",fish_generator=fish)
    speed=out/"voice-1.2x.m4a"
    run(["ffmpeg","-y","-i",str(audio),"-af","atempo=1.2","-c:a","aac","-b:a","192k",str(speed)])
    duration=float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(speed)]).strip())
    if not 20<=duration<=120: raise RuntimeError("Narration outside Short duration gate: "+str(duration))
    captions=meta.get("captions") or [s.strip() for s in re.split(r"(?<=[.!?。])\s+",meta["narration"]) if s.strip()]
    weights=[max(len(s),1) for s in captions]; total=sum(weights)
    concat=[]
    for i,(caption,weight) in enumerate(zip(captions,weights)):
        frame=out/f"frame-{i:02d}.jpg"
        card(meta["headline"],caption,photo,rights,i).save(frame,quality=94)
        concat.extend(["file '"+frame.name+"'","duration "+str(duration*weight/total)])
    concat.append("file '"+frame.name+"'")
    (out/"frames.txt").write_text("\n".join(concat),encoding="utf-8")
    card(meta["headline"],"",photo,rights,landscape=True).save(out/"thumbnail.jpg",quality=95)
    shutil.copyfile(out/"frame-00.jpg",out/"cover.jpg")
    video=out/"seoul-journal-short.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(out/"frames.txt"),"-i",str(speed),
         "-r","30","-c:v","libx264","-preset","veryfast","-threads","2","-pix_fmt","yuv420p",
         "-c:a","aac","-shortest","-movflags","+faststart",str(video)])
    audit={"duration_seconds":duration,"tts_speed":1.2,"tts":tts,"caption_cards":len(captions),
           "photo":rights,"video":str(video),"thumbnail":str(out/"thumbnail.jpg")}
    (out/"presentation_receipt.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PRESENTATION_READY "+json.dumps(audit,ensure_ascii=True),flush=True)
    return video,audit
