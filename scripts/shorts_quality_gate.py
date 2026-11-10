"""Fail-closed, dependency-free pre-publication checks for Shorts packages.

Usage:
 python scripts/shorts_quality_gate.py --package artifacts/job123 --history artifacts/published_history.jsonl
Requires package/manifest.json with title, narration, subject, photo_paths, audio_path.
Optional photo_hashes and source_urls. Does not upload or mutate published history.
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from difflib import SequenceMatcher

def norm(s):
    return re.sub(r"[^\w가-힣]", "", str(s).lower())

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def probe_audio(path):
    p = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True)
    if p.returncode: raise ValueError("AUDIO_PROBE_FAILED")
    duration=float(p.stdout.strip())
    if not 8 <= duration <= 180: raise ValueError("AUDIO_DURATION_INVALID")
    # Detect extensive silence, including a silent opening.
    s=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-af",
        "silencedetect=noise=-38dB:d=1.5","-f","null","-"],capture_output=True,text=True)
    if s.returncode: raise ValueError("AUDIO_DECODE_FAILED")
    starts=re.findall(r"silence_start:\s*([\d.]+)",s.stderr)
    ends=re.findall(r"silence_end:\s*([\d.]+)",s.stderr)
    if starts and (float(starts[0]) < .25 and (not ends or float(ends[0]) > 2.5)):
        raise ValueError("AUDIO_SILENT_OPENING")
    if len(starts)>5: raise ValueError("AUDIO_EXCESSIVE_SILENCE")
    return duration

def validate(package, history):
    p=Path(package); m=json.loads((p/"manifest.json").read_text(encoding="utf-8"))
    issues=[]
    for key in ("title","narration","subject","audio_path","photo_paths"):
        if not m.get(key): issues.append("MISSING_"+key.upper())
    title=norm(m.get("title",""))
    if len(title)<8: issues.append("TITLE_TOO_SHORT")
    photos=m.get("photo_paths") or []
    if len(photos)<3: issues.append("INSUFFICIENT_SUBJECT_PHOTOS")
    hashes=[]
    for item in photos:
        f=p/item
        if not f.is_file(): issues.append("PHOTO_MISSING:"+str(item)); continue
        hashes.append(digest(f))
    if len(hashes)!=len(set(hashes)): issues.append("DUPLICATE_PHOTO_IN_VIDEO")
    audio=p/(m.get("audio_path") or "missing")
    if not audio.is_file(): issues.append("AUDIO_MISSING")
    else:
        try: probe_audio(audio)
        except Exception as e: issues.append(str(e))
    if not m.get("photo_rights_verified"): issues.append("PHOTO_RIGHTS_UNVERIFIED")
    if not m.get("subject_match_verified"): issues.append("SUBJECT_MATCH_UNVERIFIED")
    if not m.get("fact_check_verified"): issues.append("FACT_CHECK_UNVERIFIED")
    if not m.get("captions_verified"): issues.append("CAPTIONS_UNVERIFIED")
    if not m.get("voice_review_verified"): issues.append("VOICE_REVIEW_UNVERIFIED")
    if history and Path(history).exists():
        for line in Path(history).read_text(encoding="utf-8").splitlines():
            try: h=json.loads(line)
            except ValueError: continue
            prior=norm(h.get("title",""))
            if prior and (prior==title or SequenceMatcher(None,prior,title).ratio()>=.88):
                issues.append("TITLE_DUPLICATE_HISTORY");break
        previous_hashes=set()
        for line in Path(history).read_text(encoding="utf-8").splitlines():
            try: previous_hashes.update(json.loads(line).get("photo_hashes",[]))
            except ValueError: pass
        if set(hashes)&previous_hashes: issues.append("PHOTO_REUSE_HISTORY")
    report={"passed":not issues,"issues":sorted(set(issues)),"photo_hashes":hashes,
            "title":m.get("title"),"subject":m.get("subject")}
    (p/"qa_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--package",required=True)
    parser.add_argument("--history")
    args=parser.parse_args()
    try: report=validate(args.package,args.history)
    except Exception as exc:
        print(json.dumps({"passed":False,"issues":["GATE_ERROR:"+str(exc)]},ensure_ascii=False))
        sys.exit(2)
    print(json.dumps(report,ensure_ascii=False))
    sys.exit(0 if report["passed"] else 1)
