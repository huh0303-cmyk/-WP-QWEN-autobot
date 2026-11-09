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
SUBJECT_ALIASES={"오세훈":("오세훈","Oh Se-hoon","Oh Se Hun"),"이용철":("이용철","Lee Yong Cheol","Lee Yong-cheol")}
THUMBNAIL_STYLES=("split_red","giant_quote","bottom_strip","angled_label","face_left")

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
def title_subject(text):
    title=(text or "").splitlines()[0]
    found=[name for name,aliases in SUBJECT_ALIASES.items() if any(alias in title for alias in aliases)]
    if len(found)>1: raise RuntimeError("AMBIGUOUS_TITLE_SUBJECT")
    return found[0] if found else next((name for name in PORTRAITS if name in title),None)

def card(headline,caption,photo,credit,index=0,landscape=False,zoom=1.0,overlay_only=False,category='정치·시사',style='split_red'):
    """Five varied, mobile-first headline compositions."""
    w,h=(1280,720) if landscape else (1080,1920)
    im=Image.new("RGBA" if overlay_only else "RGB",(w,h),(0,0,0,0) if overlay_only else NAVY)
    if photo and not overlay_only:
        source=Image.open(photo).convert("RGB")
        if landscape:
            background=ImageOps.fit(source,(w,h),centering=(.5,.4))
            im.paste(Image.blend(background,Image.new("RGB",(w,h),NAVY),.58))
            im.paste(ImageOps.fit(source,(690,h),centering=(.5,.4)),(590,0))
        else:
            scaled=ImageOps.fit(source,(round(w*zoom),round(h*zoom)),centering=(.5,.4))
            x=(scaled.width-w)//2; y=(scaled.height-h)//2
            im.paste(scaled.crop((x,y,x+w,y+h)))
    d=ImageDraw.Draw(im); stroke=(0,0,0)
    def text(x,y,value,size,color=WHITE):
        d.text((x,y),value,font=font(size),fill=color,stroke_width=max(2,size//12),stroke_fill=stroke)
    style=style if style in THUMBNAIL_STYLES else "split_red"
    label=(credit["subject"]+" · 자료사진("+(re.search(r"(?:19|20)\\d{2}",credit.get("date","")) or ["촬영일 미상"])[0]+")") if credit else "서울저널 자체 제작 그래픽"
    if landscape:
        cfg={
          "split_red":((20,78,770,630),YELLOW,84,48,155),
          "giant_quote":((0,385,880,720),WHITE,90,44,420),
          "bottom_strip":((0,455,1280,720),YELLOW,86,55,480),
          "angled_label":((20,80,850,690),RED,80,62,165),
          "face_left":((0,70,720,650),WHITE,88,38,175),
        }
        panel,color,size,x,y=cfg[style]
        if style=="angled_label": d.polygon([(0,110),(850,55),(850,650),(0,710)],fill=NAVY)
        elif style=="bottom_strip": d.rectangle(panel,fill=NAVY)
        elif style=="giant_quote":
            d.rectangle(panel,fill=NAVY); d.rectangle((0,385,14,720),fill=RED)
        else: d.rounded_rectangle(panel,radius=24,fill=NAVY)
        text(28,18,"서울저널",22,YELLOW if style in ("giant_quote","angled_label") else WHITE)
        maxw=panel[2]-panel[0]-65
        while size>48 and len(wrap(headline,size,maxw))>3: size-=2
        lines=wrap(headline,size,maxw)
        if len(lines)>3: raise ValueError("Thumbnail headline too long")
        for i,line in enumerate(lines): text(x,y+i*(size+10),line,size,color if i==0 else (WHITE if color!=WHITE else YELLOW))
        return im
    cfg={
      "split_red":(55,1110,920,YELLOW,NAVY,82),
      "giant_quote":(48,1280,940,WHITE,(255,255,255),94),
      "bottom_strip":(42,1400,996,(255,222,89),(8,28,62),88),
      "angled_label":(70,1160,850,(255,90,90),NAVY,82),
      "face_left":(95,1040,830,WHITE,(12,26,48),86),
    }
    left,top,width,color,bg,size=cfg[style]
    if style=="giant_quote":
        d.rectangle((0,top-35,w,h),fill=bg); d.text((35,top-110),"“",font=font(155),fill=YELLOW)
    elif style=="bottom_strip": d.rectangle((0,top-45,w,h),fill=bg)
    elif style=="angled_label": d.polygon([(0,top+20),(w,top-40),(w,h),(0,h)],fill=bg)
    elif style=="split_red":
        d.rounded_rectangle((25,top-30,w-25,h-75),radius=28,fill=bg); d.rectangle((25,top-30,42,h-75),fill=RED)
    else: d.rectangle((0,top-50,w,h),fill=bg)
    text(34,20,"서울저널",26,YELLOW if style in ("giant_quote","angled_label") else WHITE)
    text(left,top-18,"승부의 순간" if category=="스포츠" else "쟁점·반박",29,YELLOW)
    while size>48 and len(wrap(headline,size,width))>3: size-=2
    lines=wrap(headline,size,width)
    if len(lines)>3: raise ValueError("Short headline too long")
    for i,line in enumerate(lines): text(left,top+35+i*(size+12),line,size,color)
    cap_size=40 if style in ("split_red","face_left") else 35
    cap=wrap(caption,cap_size,width)
    if len(cap)>3: cap_size=29; cap=wrap(caption,cap_size,width)
    for i,line in enumerate(cap[:3]): text(left,top+330+i*(cap_size+12),line,cap_size,WHITE)
    text(left,1760,label,20)
    return im

ANCHOR_VOICES = (
 {"name":"남성 뉴스앵커 1","gender":"male","edge":"ko-KR-InJoonNeural","pitch":"-4Hz","fish_env":"SJ_FISH_MALE_ANCHOR"},
 {"name":"남성 다큐 2","gender":"male","edge":"ko-KR-BongJinNeural","pitch":"+1Hz","fish_env":"SJ_FISH_MALE_2"},
 {"name":"여성 뉴스앵커 1","gender":"female","edge":"ko-KR-SunHiNeural","pitch":"-2Hz","fish_env":"SJ_FISH_FEMALE_ANCHOR"},
 {"name":"여성 다큐 2","gender":"female","edge":"ko-KR-YuJinNeural","pitch":"+1Hz","fish_env":"SJ_FISH_FEMALE_2"},
)
def photo_sequence(meta,out):
    """Use reviewed Commons file titles, or the exact registered subject's named photos."""
    session=requests.Session()
    session.headers.update({"User-Agent":"SeoulJournalEditorial/2.0 (https://github.com/huh0303-cmyk/-WP-QWEN-autobot; news asset attribution)"})
    files=meta.get("photo_files", [])
    evidence=meta.get("source_title","")+" "+meta["youtube_title"]+" "+meta["narration"]
    subject=title_subject(meta.get("source_title") or meta.get("youtube_title"))
    if not subject: raise RuntimeError("NO_TITLE_MATCHED_SUBJECT: refusing unrelated portrait")
    english={"이재명":"Lee Jae-myung","오세훈":"Oh Se-hoon","이용철":"Lee Yong Cheol"}[subject]
    if subject and not english:
        # Resolve the exact Korean label before searching named Commons images.
        response=session.get("https://www.wikidata.org/w/api.php",params={
            "action":"wbsearchentities","search":subject,"language":"ko","limit":5,"format":"json"},timeout=30)
        response.raise_for_status()
        matches=[x for x in response.json().get("search",[]) if x.get("label")==subject]
        if len(matches)==1:
            response=session.get("https://www.wikidata.org/w/api.php",params={
                "action":"wbgetentities","ids":matches[0]["id"],"props":"labels|claims","languages":"en","format":"json"},timeout=30)
            response.raise_for_status()
            entity=response.json()["entities"][matches[0]["id"]]
            kinds=[x.get("mainsnak",{}).get("datavalue",{}).get("value",{}).get("id") for x in entity.get("claims",{}).get("P31",[])]
            if "Q5" in kinds:
                english=entity.get("labels",{}).get("en",{}).get("value")
    if not files and subject=="이용철":
        raise RuntimeError("LICENSE_REVIEW_REQUIRED: 이용철 official portrait has no verified reuse mark")
    if not files and english:
        response=session.get("https://commons.wikimedia.org/w/api.php",params={
            "action":"query","list":"search","srsearch":'intitle:"'+english+'" filetype:bitmap',
            "srnamespace":6,"srlimit":20,"format":"json"},timeout=30)
        response.raise_for_status()
        files=([PORTRAITS[subject]] if subject in PORTRAITS else [])+[x["title"] for x in response.json()["query"]["search"]
            if english.lower() in x["title"].lower()]
    assets=[]; hashes=set()
    for title in dict.fromkeys(files):
        response=session.get("https://commons.wikimedia.org/w/api.php",params={
            "action":"query","titles":title,"prop":"imageinfo","iiprop":"url|extmetadata|sha1",
            "iiurlwidth":1600,"format":"json"},timeout=30)
        response.raise_for_status()
        page=next(iter(response.json()["query"]["pages"].values()))
        if not page.get("imageinfo"): continue
        info=page["imageinfo"][0]; md=info.get("extmetadata",{})
        license_name=md.get("LicenseShortName",{}).get("value","")
        if license_name not in ("Public domain","CC0","CC BY 4.0","CC BY-SA 4.0","CC BY 3.0","CC BY-SA 3.0"): continue
        if info.get("sha1") in hashes: continue
        image=session.get(info.get("thumburl",info["url"]),timeout=45); image.raise_for_status()
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
    # One of two male or two female profiles; stable for retries, varied between stories.
    seed=meta.get("slot_marker") or (meta["youtube_title"]+str(random.SystemRandom().randint(0,2**32-1)))
    pick=int(hashlib.sha256(seed.encode()).hexdigest(),16)%len(ANCHOR_VOICES)
    return dict(ANCHOR_VOICES[pick])

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
    assets=meta.pop("_prepared_assets",None) or photo_sequence(meta,out)
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
    style=meta.get("thumbnail_style")
    if style not in THUMBNAIL_STYLES: style=random.SystemRandom().choice(THUMBNAIL_STYLES)
    meta["thumbnail_style"]=style
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
        card(meta["headline"],caption,None,rights,i,overlay_only=True,category=category,style=style).save(overlay)
        frames=max(1,math.ceil(seconds*30))
        z=f"1+0.10*on/{max(frames-1,1)}" if i%2==0 else f"1.10-0.10*on/{max(frames-1,1)}"
        clip=out/f"scene-{i:02d}.mp4"
        run(["ffmpeg","-y","-loop","1","-i",str(bg),"-loop","1","-i",str(overlay),
             "-filter_complex",f"[0:v]scale=2160:3840,zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30[photo];[photo][1:v]overlay=0:0:shortest=1,format=yuv420p[v]",
             "-map","[v]","-t",str(seconds),"-an","-c:v","libx264","-preset","veryfast","-threads","2",str(clip)])
        concat.append("file '"+clip.name+"'"); elapsed+=seconds
    (out/"scenes.txt").write_text("\n".join(concat),encoding="utf-8")
    card(meta["headline"],"",assets[0][0],assets[0][1],landscape=True,category=category,style=style).save(out/"thumbnail.jpg",quality=95)
    card(meta["headline"],"",assets[0][0],assets[0][1],category=category,style=style).save(out/"cover.jpg",quality=95)
    video=out/"seoul-journal-short.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(out/"scenes.txt"),"-i",str(speed),
         "-c:v","copy","-c:a","aac","-shortest","-movflags","+faststart",str(video)])
    audit={"duration_seconds":duration,"tts_speed":1.2,"tts":tts,"caption_cards":len(captions),
           "photo":assets[0][1],"photos":[r for _,r in assets],"anchor":voice["name"],"voice_gender":voice["gender"],"thumbnail_style":style,"motion":"alternating zoom in/out; stationary text","video":str(video),"thumbnail":str(out/"thumbnail.jpg")}
    (out/"presentation_receipt.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PRESENTATION_READY "+json.dumps(audit,ensure_ascii=True),flush=True)
    return video,audit
