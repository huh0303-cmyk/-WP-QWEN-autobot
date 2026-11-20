#!/usr/bin/env python3
"""Seoul Journal: source-preserving captioned YouTube clips."""
import argparse, json, os, re, subprocess
from pathlib import Path
from faster_whisper import WhisperModel
import google.generativeai as genai

OUT=Path("shorts_output")
def call(cmd, capture=False):
    return subprocess.run(cmd,check=True,text=True,capture_output=capture)
def seconds(path):
    return float(call(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],True).stdout.strip())
def download(url):
    OUT.mkdir(exist_ok=True)
    cookies=os.environ.get("YT_COOKIES","").strip()
    cookiefile=OUT/"cookies.txt"
    args=["yt-dlp","--no-playlist","-f","bv*+ba/b","--merge-output-format","mp4","--write-info-json","-o",str(OUT/"source.%(ext)s")]
    if cookies:
        if not cookies.startswith("# Netscape HTTP Cookie File") and not cookies.startswith("# HTTP Cookie File"):
            raise ValueError("YT_COOKIES must be Netscape cookies.txt format")
        cookiefile.write_text(cookies+"\n",encoding="utf-8")
        cookiefile.chmod(0o600)
        args+=["--cookies",str(cookiefile)]
    try: call(args+[url])
    finally: cookiefile.unlink(missing_ok=True)
    videos=[p for p in OUT.glob("source.*") if p.suffix.lower() in (".mp4",".mkv",".webm")]
    if not videos: raise RuntimeError("Download did not produce a video")
    infos=list(OUT.glob("source*.info.json"))
    return videos[0],json.loads(infos[0].read_text()) if infos else {}
def transcribe(video):
    model=WhisperModel(os.getenv("WHISPER_MODEL","small"),device="cpu",compute_type="int8")
    segments,_=model.transcribe(str(video),language="ko",word_timestamps=True,vad_filter=True)
    rows=[]
    for seg in segments:
        words=[{"start":round(w.start,2),"end":round(w.end,2),"text":w.word.strip()} for w in (seg.words or []) if w.word.strip()]
        if words: rows.append({"start":words[0]["start"],"end":words[-1]["end"],"text":seg.text.strip(),"words":words})
    if not rows: raise RuntimeError("No Korean speech detected")
    (OUT/"transcript.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    return rows
def select(rows,duration):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model=genai.GenerativeModel(os.getenv("GEMINI_MODEL","gemini-2.5-flash"))
    brief=[{k:r[k] for k in ("start","end","text")} for r in rows]
    prompt=("정치인 발언의 맥락을 왜곡하지 말 것, 특정 인물을 비방하는 편집 금지, 발언 취지를 유지할 것. "
            "원본에 없는 말을 만들지 말고 문장 시작과 끝에서만 자르세요. 30~60초 구간 5~8개, "
            "부족하면 적게 선정. JSON 객체만: "
            '{"clips":[{"start":0,"end":45,"title":"제목","summary":"요약"}]}'+"\n"+json.dumps(brief,ensure_ascii=False))
    data=json.loads(model.generate_content(prompt,generation_config={"response_mime_type":"application/json"}).text)
    clips=[]
    for c in data.get("clips",[]):
        try:
            s=min((r["start"] for r in rows),key=lambda x:abs(x-float(c["start"])))
            e=min((r["end"] for r in rows),key=lambda x:abs(x-float(c["end"])))
            if not 30<=e-s<=60 or e>duration+.2: continue
            if any(max(0,min(e,x["end"])-max(s,x["start"]))>5 for x in clips):continue
            clips.append({"start":s,"end":e,"title":str(c["title"])[:100],"summary":str(c["summary"])[:300]})
        except (KeyError,ValueError,TypeError): continue
        if len(clips)>=8:break
    if not clips:raise RuntimeError("No suitable clips; inspect transcript")
    return clips
def stamp(t):
    n=round(max(0,t)*100);h,n=divmod(n,360000);m,n=divmod(n,6000);s,cs=divmod(n,100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"
def clean(t):
    return re.sub(r"\s+"," ",t).strip().replace("\\","＼").replace("{","｛").replace("}","｝")
def captions(rows,start,end,path):
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK KR,65,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,4,1,2,60,60,260,1
Style: Brand,Noto Sans CJK KR,34,&H0000D7FF,&H0000D7FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1,2,30,30,45,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events=[header]
    for r in rows:
        words=[w for w in r["words"] if w["end"]>start and w["start"]<end]
        for i in range(0,len(words),5):
            group=words[i:i+5]
            a=max(start,group[0]["start"]);b=min(end,group[-1]["end"])
            if b>a+.08:
                events.append(f"Dialogue: 0,{stamp(a-start)},{stamp(b-start)},Default,,0,0,0,,{clean(' '.join(w['text'] for w in group))}\n")
    brand="서울저널  |  자율 후원 · 농협 352-2371-04-7373"
    events.append(f"Dialogue: 1,{stamp(0)},{stamp(end-start)},Brand,,0,0,0,,{brand}\n")
    path.write_text("".join(events),encoding="utf-8")
def render(video,rows,clips,info,layout):
    source={"channel":info.get("channel") or info.get("uploader") or "Unknown","url":info.get("webpage_url") or "","title":info.get("title") or ""}
    metadata={"source":source,"channel_target":"https://www.youtube.com/@seouljournal1","clips":[]}
    for i,c in enumerate(clips,1):
        stem=f"short_{i:02d}";ass=OUT/(stem+".ass");captions(rows,c["start"],c["end"],ass)
        if layout=="crop":
            vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
        else:
            vf=("split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:10[b];"
                "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[f];[b][f]overlay=(W-w)/2:(H-h)/2,setsar=1")
        vf+=",ass="+ass.as_posix()+":fontsdir=/usr/share/fonts/opentype/noto"
        out=OUT/(stem+".mp4")
        call(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",str(c["start"]),"-i",str(video),"-t",str(c["end"]-c["start"]),"-vf",vf,"-map","0:v:0","-map","0:a:0?","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",str(out)])
        metadata["clips"].append({**c,"file":out.name,"description":c["summary"]+"\n원본 채널: "+source["channel"]+"\n원본 링크: "+source["url"]})
        (OUT/"metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print("Created",len(metadata["clips"]),"clips")
def main():
    p=argparse.ArgumentParser();p.add_argument("url");p.add_argument("--layout",choices=["blur","crop"],default="blur");a=p.parse_args()
    if not re.match(r"^https://(www\.)?(youtube\.com|youtu\.be)/",a.url):p.error("YouTube HTTPS URL required")
    if not os.getenv("GEMINI_API_KEY"):p.error("GEMINI_API_KEY is required")
    video,info=download(a.url);rows=transcribe(video);clips=select(rows,seconds(video));render(video,rows,clips,info,a.layout)
if __name__=="__main__":main()
