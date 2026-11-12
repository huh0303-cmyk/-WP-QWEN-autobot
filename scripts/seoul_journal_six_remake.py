"""Rebuild six existing Seoul Journal Shorts from original Actions artifacts; private upload only."""
import json, os, re, subprocess, hashlib, sys
from pathlib import Path
from io import BytesIO
from urllib.parse import urljoin
import requests
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"artifacts"/"seoul-six-remake"
IDS={"0iUWNHp7_Ak":"이진숙","-NCACH1CuIw":"이재명","ei0WXO2NgmQ":"오세훈","nmfgsVpYXx8":"한동훈","50aiJ17gbfk":"이재명","nH0xc-tiHQI":"안철수"}
ENGLISH={"이진숙":"Lee Jin-sook","이재명":"Lee Jae-myung","오세훈":"Oh Se-hoon","한동훈":"Han Dong-hoon","안철수":"Ahn Cheol-soo"}
HEADERS={"User-Agent":"SeoulJournalShorts/1.0 (https://github.com/huh0303-cmyk/-WP-QWEN-autobot)"}
def cmd(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=300)
    if p.returncode:raise RuntimeError(p.stderr[-700:])
def find_original(vid):
    for receipt in BASE.rglob("upload_receipt.json"):
        if json.loads(receipt.read_text(encoding="utf-8"))["video_id"]==vid:return receipt.parent
    raise RuntimeError("Missing source artifact "+vid)
def photos(src,name):
    """Use Wikimedia Commons files with explicit subject names and a reusable license."""
    output=[];seen=set()
    api="https://commons.wikimedia.org/w/api.php"
    for query in [f'{ENGLISH[name]}',f'{ENGLISH[name]} politician']:
        try:
            data=requests.get(api,params={"action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":30,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1400,"format":"json"},headers=HEADERS,timeout=20).json()
            pages=data.get("query",{}).get("pages",{})
            for page in pages.values():
                title=page.get("title","")
                if not any(part.lower() in title.lower() for part in ENGLISH[name].split() if len(part)>3):continue
                info=(page.get("imageinfo") or [{}])[0]
                meta=info.get("extmetadata",{})
                license_name=meta.get("LicenseShortName",{}).get("value","")
                if not any(k in license_name.lower() for k in ("cc","public domain","pd")):continue
                url=info.get("thumburl") or info.get("url")
                if not url:continue
                try:
                    raw=requests.get(url,headers=HEADERS,timeout=20).content
                    im=Image.open(BytesIO(raw)).convert("RGB")
                    if min(im.size)<300:continue
                    key=hashlib.sha256(im.resize((64,64)).tobytes()).hexdigest()
                    if key in seen:continue
                    seen.add(key)
                    output.append((im,{"title":title,"url":info.get("descriptionurl"),"license":license_name}))
                    if len(output)>=5:return output
                except Exception:continue
        except Exception as e:print("PHOTO_SEARCH_ERROR",name,type(e).__name__,flush=True)
    return output
def make(vid):
    source=find_original(vid);meta=json.loads((source/"package.json").read_text(encoding="utf-8"))
    voice=source/"voice.mp3"
    if not voice.is_file():raise RuntimeError("Original narration missing")
    name=IDS[vid];images=photos(source,name)
    if len(images)<5:raise RuntimeError(f"FAIL CLOSED {vid}: only {len(images)} verified Commons photographs for {name}")
    dest=BASE/"remade"/vid;dest.mkdir(parents=True,exist_ok=True)
    (dest/"photo-sources.json").write_text(json.dumps([x[1] for x in images],ensure_ascii=False,indent=2),encoding="utf-8")
    audio_length=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(voice)],text=True).strip())/1.2
    length=max(1,audio_length-4)
    words=re.findall(r"[^\\s,.!?]+",meta.get("narration",""))
    font_path="C:/Windows/Fonts/malgunbd.ttf"
    font=ImageFont.truetype(font_path,62)
    pieces=[]
    n=max(5,round(length/2))
    for i in range(n):
        im=images[i%5][0]
        W,H=1080,1920
        scale=max(W/im.width,H/im.height)
        im=im.resize((round(im.width*scale),round(im.height*scale)))
        x=(im.width-W)//2;y=(im.height-H)//2
        im=im.crop((x,y,x+W,y+H))
        d=ImageDraw.Draw(im)
        start=int(i*len(words)/n)
        caption=" ".join(words[start:start+3])[:20]
        box=d.textbbox((0,0),caption,font=font,stroke_width=4)
        d.text(((W-box[2]+box[0])//2,940),caption,font=font,fill="white",stroke_width=5,stroke_fill="black")
        still=dest/f"frame{i:02d}.jpg";im.save(still,quality=92)
        seg=dest/f"seg{i:02d}.mp4";frames=round(length/n*25)
        z="min(zoom+0.0006,1.12)" if i%2==0 else "max(1.0,1.12-on*0.0006)"
        cmd(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(still),"-vf",f"scale=1200:2134,zoompan=z='{z}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={frames}:s=1080x1920:fps=25,format=yuv420p","-frames:v",str(frames),"-c:v","libx264","-preset","ultrafast",str(seg)])
        pieces.append(seg)
    poll=images[0][0].resize((1080,1920))
    d=ImageDraw.Draw(poll)
    question=meta.get("headline","이 사안")+"에 대한 의견은?"
    for i,line in enumerate([question[:16],question[16:32],"찬성  /  반대  /  판단 유보","투표는 채널 게시물에서"]):
        d.text((50,650+i*120),line,font=font,fill="white",stroke_width=6,stroke_fill="black")
    still=dest/"poll.jpg";poll.save(still)
    seg=dest/"poll.mp4"
    cmd(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(still),"-t","4","-vf","format=yuv420p","-r","25","-c:v","libx264","-preset","ultrafast",str(seg)])
    pieces.append(seg)
    concat=dest/"concat.txt";concat.write_text("".join("file '"+p.as_posix()+"'\\n" for p in pieces),encoding="utf-8")
    output=dest/"remade-private-ready.mp4"
    cmd(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-i",str(voice),"-af","atempo=1.2","-c:v","libx264","-preset","ultrafast","-c:a","aac","-shortest",str(output)])
    print("RENDERED",vid,output,flush=True)
    return output
if __name__=="__main__":
    for vid in IDS:
        try:make(vid)
        except Exception as e:print("FAILED",vid,str(e),flush=True)
