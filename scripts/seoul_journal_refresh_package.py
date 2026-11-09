"""Refresh the visual overlays of an existing rendered Seoul Journal review package."""
import json, math, subprocess, sys
from pathlib import Path
from PIL import Image
from seoul_journal_presentation import card

def run(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return result.stdout

def duration(path):
    return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)]).strip())

def refresh(package_dir):
    files=list(Path(package_dir).rglob("package.json"))
    if len(files)!=1:
        raise RuntimeError("Expected exactly one package.json")
    package=files[0].parent
    meta=json.loads(files[0].read_text(encoding="utf-8"))
    receipt_path=package/"presentation_receipt.json"
    receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
    rights=receipt["photos"]
    assets=package/"assets-1"
    style=meta["thumbnail_style"]
    captions=meta["captions"]
    for i,caption in enumerate(captions):
        overlay=card(meta["headline"],caption,None,rights[i%len(rights)],i,overlay_only=True,
                     category=meta.get("display_category","정치·시사"),style=style)
        overlay.save(package/f"overlay-{i:02d}.png")
    first_photo=assets/"photo-00.jpg"
    card(meta["headline"],"",first_photo,rights[0],landscape=True,
         category=meta.get("display_category","정치·시사"),style=style).save(package/"thumbnail.jpg",quality=95)
    card(meta["headline"],"",first_photo,rights[0],
         category=meta.get("display_category","정치·시사"),style=style).save(package/"cover.jpg",quality=95)
    for i in range(len(captions)):
        bg=package/f"background-{i:02d}.jpg"
        overlay=package/f"overlay-{i:02d}.png"
        scene=package/f"scene-{i:02d}.mp4"
        seconds=duration(scene)
        frames=max(1,math.ceil(seconds*30))
        z=f"1+0.10*on/{max(frames-1,1)}" if i%2==0 else f"1.10-0.10*on/{max(frames-1,1)}"
        run(["ffmpeg","-y","-loop","1","-i",str(bg),"-loop","1","-i",str(overlay),
             "-filter_complex",f"[0:v]scale=2160:3840,zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30[photo];[photo][1:v]overlay=0:0:shortest=1,format=yuv420p[v]",
             "-map","[v]","-t",str(seconds),"-an","-c:v","libx264","-preset","veryfast",
             "-threads","2",str(scene)])
    video=package/"seoul-journal-short.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(package/"scenes.txt"),
         "-i",str(package/"voice-1.2x.m4a"),"-c:v","copy","-c:a","aac","-shortest",
         "-movflags","+faststart",str(video)])
    receipt["video"]=str(video)
    receipt["archival_year_labels_refreshed"]=True
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print("REVIEW_PACKAGE_REFRESHED "+str(package),flush=True)

if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("usage: seoul_journal_refresh_package.py <artifact-root>")
    refresh(sys.argv[1])
