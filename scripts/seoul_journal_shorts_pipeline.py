#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one source-grounded Seoul Journal political Short and upload PRIVATE only."""
import os, re, json, textwrap, subprocess, sys, random, hashlib, time
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse
import requests, trafilatura
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT=Path.cwd()
OUT=ROOT/"artifacts"/"seoul-journal-short"
OUT.mkdir(parents=True,exist_ok=True)
NAVER_POLITICS="https://news.naver.com/section/100"
CONTENT_SCOPE="politics"
THUMBNAIL_BENCHMARKS=ROOT/"config"/"seoul_journal_thumbnail_benchmarks.json"
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
PRIORITY_FIGURES={
    "이재명":"Lee Jae-myung", "한동훈":"Han Dong-hoon", "김민석":"Kim Min-seok politician",
    "정청래":"Chung Chung-rae", "오세훈":"Oh Se-hoon", "추미애":"Choo Mi-ae",
    "조국":"Cho Kuk", "장동혁":"Jang Dong-hyeok politician", "안철수":"Ahn Cheol-soo",
}

def log(s): print(s,flush=True)

def load_thumbnail_benchmark_contract():
    """Fail closed unless three recently inspected 500k+ political Shorts back the cover design."""
    if not THUMBNAIL_BENCHMARKS.is_file():
        raise RuntimeError("썸네일 벤치마크 파일이 없어 비공개 업로드를 중단합니다.")
    data=json.loads(THUMBNAIL_BENCHMARKS.read_text(encoding="utf-8"))
    minimum=int(data.get("minimum_views",500000))
    examples=data.get("examples",[])
    if len(examples)<max(3,int(data.get("minimum_examples",3))):
        raise RuntimeError("50만 조회 이상 정치 쇼츠 썸네일 3개 검수가 필요합니다.")
    invalid=[row.get("video_id","unknown") for row in examples if int(row.get("observed_views",0))<minimum or not row.get("visual_observation")]
    if invalid:
        raise RuntimeError("썸네일 벤치마크 검수 미달: "+", ".join(invalid))
    observed=datetime.fromisoformat(data["observed_at_kst"])
    age=(datetime.now(timezone.utc)-observed.astimezone(timezone.utc)).days
    if age>30:
        raise RuntimeError(f"썸네일 벤치마크가 {age}일 경과했습니다. 실제 화면과 조회수를 다시 확인하세요.")
    receipt={
        "verified_at_run_utc":datetime.now(timezone.utc).isoformat(),
        "observed_at_kst":data["observed_at_kst"],
        "minimum_views":minimum,
        "examples":examples[:3],
        "common_traits":data.get("common_traits",[]),
        "adaptation_rule":data.get("adaptation_rule",""),
    }
    (OUT/"thumbnail-benchmark-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    return receipt

def get_with_retries(url, *, params=None, timeout=25, attempts=3):
    last=None
    for attempt in range(attempts):
        try:
            response=requests.get(url,params=params,headers=UA,timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last=exc
            if attempt+1<attempts:
                time.sleep(1.5*(attempt+1))
    raise last

def choose_naver_article():
    r=get_with_retries(NAVER_POLITICS)
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
    # Prefer a current item whose title names a major political figure. This is a
    # packaging requirement, not a popularity or truth signal.
    selected=next((row for row in candidates if any(name in row["title"] for name in PRIORITY_FIGURES)),candidates[0])
    method="Naver Politics first card naming a priority political figure" if selected is not candidates[0] or any(name in selected["title"] for name in PRIORITY_FIGURES) else "Naver Politics section first eligible card"
    return selected["url"], selected["title"], method+" (not verified by view count)"

def extract(url):
    p=urlparse(url)
    if p.scheme not in ("https","http") or not p.netloc or "naver.com" not in p.netloc.lower():
        raise RuntimeError("기사 URL은 네이버 뉴스 URL이어야 합니다.")
    r=get_with_retries(url)
    soup=BeautifulSoup(r.text,"html.parser")
    title=(soup.select_one("#title_area") or soup.select_one("h2") or soup.title)
    title=" ".join(title.get_text(" ",strip=True).split()) if title else ""
    text=trafilatura.extract(r.text,include_comments=False,include_tables=False)
    og=soup.find("meta",property="og:image")
    image_url=og.get("content","") if og else ""
    if not text or len(text)<300: raise RuntimeError("기사 본문 추출 실패/본문 부족. 접근 제한 기사일 수 있습니다.")
    return title,text,image_url,r.text

def draft(title, body):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY GitHub Actions secret이 없습니다.")
    genai.configure(api_key=key)
    models = [os.getenv("SEOUL_JOURNAL_GEMINI_MODEL", "").strip(), "gemini-3.0-flash-lite", "gemini-3.1-flash-lite", "gemini-3.0-flash", "gemini-2.0-flash", "gemini-3.6-flash", "gemini-3.8-flash"]
    models = list(dict.fromkeys(x for x in models if x))
    prompt = f"""당신은 서울저널의 한국어 정치 뉴스 기자 겸 팩트체커입니다.
기사 제목: {title}
기사 본문:
{body[:12000]}
세로 정치 쇼츠 패키지를 작성하세요. 60초 상한을 두지 말고 핵심 발언, 상대 반박, 확인된 사실과 맥락, 마지막 중립적 투표 질문이 완결될 만큼 작성하세요. 보통 공백 포함 650~1100자, 최소 5개 문단을 목표로 하되 근거가 부족하면 억지로 늘리지 마세요.
기사에 있는 배경·당사자 발언·확인된 사실을 구체적으로 설명하고 마지막은 '서울저널이 알려드립니다. 여러분은 어떻게 생각하십니까?'로 마무리하세요.
기사에 없는 사실·추측·숫자·인용은 만들지 마세요. JSON 객체 하나만 반환:
{{"headline":"썸네일용 10~18자 헤드라인","youtube_title":"사실에 근거한 제목 100자 이내","narration":"650~1100자 기자 내레이션(근거가 부족하면 더 짧게)","description":"중립적 요약과 [원문 기사] 자리","source_note":"확인된 사실과 한계"}}"""
    errors = []
    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)
            result = model.generate_content(prompt, generation_config={"temperature": 0.35, "response_mime_type": "application/json"})
            raw = (result.text or "").strip().strip("`")
            data = json.loads(raw)
            narration = str(data.get("narration", "")).strip()
            if len(narration) >= 420:
                data["narration"] = narration
                log(f"WRITER_ENGINE=gemini model={model_name} narration_chars={len(narration)}")
                return data
            errors.append(f"{model_name}:{len(narration)}")
        except Exception as exc:
            errors.append(f"{model_name}:{type(exc).__name__}")
    raise RuntimeError("Gemini writing chain failed or narration too short: " + ", ".join(errors))

EDGE_VOICES = [("ko-KR-HyunsuNeural","male_deep"),("ko-KR-InJoonNeural","male_documentary"),("ko-KR-BongJinNeural","male_anchor"),("ko-KR-SunHiNeural","female_anchor"),("ko-KR-JiMinNeural","female_documentary"),("ko-KR-SeoHyeonNeural","female_news")]

def tts(text):
    """Free-only narration: Fish Audio S2.1 Pro Free first, then Edge TTS.
    Never calls a paid endpoint. Secrets are never printed to logs.
    """
    p = OUT / "voice.mp3"
    errors = []
    voice_name, voice_role = random.choice(EDGE_VOICES)
    fish_ids = [x.strip() for x in os.getenv("FISH_AUDIO_VOICE_IDS","").split(",") if x.strip()]
    fish_voice = random.choice(fish_ids) if fish_ids else ""
    api_key = os.getenv("FISH_AUDIO_API_KEY", "").strip()
    if api_key:
        try:
            r = requests.post(
                "https://api.fish.audio/v1/tts",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "model": "s2.1-pro-free",
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={"text": text, "format": "mp3", **({"reference_id": fish_voice} if fish_voice else {})},
                timeout=150,
            )
            if r.ok and len(r.content) >= 2000 and not r.content.lstrip().startswith(b"{"):
                p.write_bytes(r.content)
                log(f"TTS_ENGINE=fish_audio model=s2.1-pro-free voice_role={voice_role} bytes={p.stat().st_size}")
                return p
            errors.append(f"Fish Audio returned HTTP {r.status_code} or invalid audio")
        except Exception as exc:
            errors.append(f"Fish Audio failed ({type(exc).__name__})")
    else:
        errors.append("Fish Audio API key not configured; trying free Edge TTS")

    # Edge TTS is a free fallback. No paid provider is called if it fails.
    try:
        import asyncio
        import edge_tts
        async def save_edge():
            await edge_tts.Communicate(text, voice_name).save(str(p))
        asyncio.run(save_edge())
        if p.exists() and p.stat().st_size >= 2000:
            log(f"TTS_ENGINE=edge_tts voice={voice_name} voice_role={voice_role} bytes={p.stat().st_size}")
            return p
        errors.append("Edge TTS returned invalid audio")
    except Exception as exc:
        errors.append(f"Edge TTS failed ({type(exc).__name__})")

    raise RuntimeError("All free TTS providers failed: " + "; ".join(errors))

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

# Five reference-led editorial thumbnail systems: red breaking, quote/debate,
# numeric briefing, field report, and viewer poll. The same selected system is used
# for the opening frame and the generated cover image.
SHORT_STYLES = [
    {"name":"01_breaking_red","bg":(13,25,47),"highlight":(255,220,45),"accent":(222,24,35),"badge":"속보"},
    {"name":"02_quote_debate","bg":(5,27,55),"highlight":(0,226,255),"accent":(236,35,45),"badge":"발언 대 반박"},
    {"name":"03_issue_briefing","bg":(8,38,71),"highlight":(255,226,32),"accent":(0,154,217),"badge":"핵심 쟁점"},
    {"name":"04_field_report","bg":(28,27,35),"highlight":(255,214,74),"accent":(210,35,45),"badge":"현장 리포트"},
    {"name":"05_viewer_poll","bg":(12,24,48),"highlight":(0,229,255),"accent":(221,27,39),"badge":"여러분의 선택은?"},
]

def _font(size):
    paths=[
      "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
      "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
      "C:/Windows/Fonts/malgunbd.ttf",
      "C:/Windows/Fonts/malgun.ttf",
      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    fp=next((p for p in paths if os.path.exists(p)),None)
    try: return ImageFont.truetype(fp,size) if fp else ImageFont.load_default()
    except Exception: return ImageFont.load_default()

def _fit_headline(draw, headline, max_width, max_lines=3):
    words=headline.split()
    for size in (90,84,78,72,66):
        font=_font(size); lines=[]; current=""
        for word in words:
            trial=(current+" "+word).strip()
            if draw.textbbox((0,0),trial,font=font,stroke_width=3)[2] <= max_width:
                current=trial
            else:
                if current: lines.append(current)
                current=word
        if current: lines.append(current)
        if len(lines)<=max_lines:
            return lines,font
    return textwrap.wrap(headline,width=12)[:max_lines],_font(60)

def _cover_frame(headline,photo,style,index,caption="",poll=False,thumbnail=False):
    W,H=1080,1920
    base=Image.new("RGB",(W,H),style["bg"])
    if photo:
        try:
            im=Image.open(photo).convert("RGB")
            scale=max(W/im.width,H/im.height)
            im=im.resize((int(im.width*scale),int(im.height*scale)))
            x=(im.width-W)//2; y=(im.height-H)//2
            base.paste(im.crop((x,y,x+W,y+H)),(0,0))
        except Exception as exc:
            log(f"Photo crop fallback ({type(exc).__name__})")
    # Editorial darkening preserves the real photograph while keeping type readable.
    shade=Image.new("RGBA",(W,H),(0,0,0,88))
    base=Image.alpha_composite(base.convert("RGBA"),shade)
    draw=ImageDraw.Draw(base)
    # top identity and breaking badge
    draw.rectangle((0,0,W,130),fill=(*style["bg"],238))
    draw.rectangle((42,34,250,105),fill=style["accent"])
    draw.text((58,43),style["badge"],font=_font(42),fill=(255,255,255),stroke_width=1,stroke_fill=(0,0,0))
    draw.text((W-425,48),"SEOUL JOURNAL",font=_font(30),fill=(255,255,255))
    if thumbnail:
        # 500k+ reference commonality adapted to the owner's explicit preference:
        # one real face dominates and 1-3 huge lines float directly on the photo.
        # No black panel or bar may cover the face.
        lines,title_font=_fit_headline(draw,headline,900,max_lines=3)
        line_height=title_font.size+18
        y=210
        for i,line in enumerate(lines):
            box=draw.textbbox((0,0),line,font=title_font,stroke_width=3)
            x=(W-(box[2]-box[0]))//2
            color=style["highlight"] if i==len(lines)-1 else (255,255,255)
            draw.text((x,y),line,font=title_font,fill=color,stroke_width=9,stroke_fill=(0,0,0))
            y+=line_height
    # Narration subtitles float directly on the image with a thick outline. Never
    # place a black box/bar over the politician's face.
    if (caption or poll) and not thumbnail:
        if poll:
            lines=["어떻게 생각하시나요?","A 찬성  B 반대","C 더 지켜보기"]
            font=_font(64); y=690
        else:
            lines=textwrap.wrap(caption,width=18,break_long_words=True,break_on_hyphens=False)[:4]
            font=_font(54); y=1250-len(lines)*34
        for line in lines:
            box=draw.textbbox((0,0),line,font=font,stroke_width=7)
            draw.text(((W-(box[2]-box[0]))//2,y),line,font=font,fill=style["highlight"] if poll else (255,255,255),stroke_width=8,stroke_fill=(0,0,0))
            y+=82 if poll else 72
        if poll:
            footer="댓글로 A·B·C를 눌러 참여하세요"
            box=draw.textbbox((0,0),footer,font=_font(38),stroke_width=6)
            draw.text(((W-(box[2]-box[0]))//2,1580),footer,font=_font(38),fill=(255,255,255),stroke_width=7,stroke_fill=(0,0,0))
    return base.convert("RGB")

def _subtitle_chunks(narration, target_chars=32):
    """Expose the full narration as sequential, readable on-screen subtitles."""
    sentences=[x.strip() for x in re.split(r"\n+|(?<=[.!?。！？])\s+",narration) if x.strip()]
    chunks=[]
    for sentence in sentences:
        pieces=textwrap.wrap(sentence,width=target_chars,break_long_words=True,break_on_hyphens=False) or [sentence]
        chunks.extend(piece.strip() for piece in pieces if piece.strip())
    return chunks

def render(headline, photo, audio, photos=None):
    """Render rotating real source images; never loop a single still for a full Short."""
    candidates = list(photos or ([] if photo is None else [photo]))
    unique = []
    hashes = set()
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        with Image.open(candidate) as im:
            digest = hashlib.sha256(im.convert("RGB").resize((64, 64)).tobytes()).hexdigest()
        if digest not in hashes:
            unique.append(Path(candidate)); hashes.add(digest)
    if len(unique) < 5:
        raise RuntimeError(f"Visual quality gate: {len(unique)}/5 distinct photos; private upload blocked to prevent single-image video")
    benchmark=load_thumbnail_benchmark_contract()
    style = random.choice(SHORT_STYLES)
    for idx, template in enumerate(SHORT_STYLES, 1):
        _cover_frame(headline, unique[0], template, idx, thumbnail=True).save(OUT/f"thumbnail-template-{idx:02d}.jpg", quality=93)
    _cover_frame(headline, unique[0], style, 1, thumbnail=True).save(OUT/"cover.jpg", quality=94)
    (OUT/"template.txt").write_text(style["name"], encoding="utf-8")
    ffmpeg = os.getenv("FFMPEG_BINARY", "ffmpeg")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio)], capture_output=True, text=True, check=True)
    duration = float(probe.stdout.strip()) / 1.2
    poll_seconds = min(4.0, max(3.0, duration * 0.10))
    available=duration-poll_seconds
    if available/len(unique) < 1.5:
        raise RuntimeError("Narration is too short to show five source images and the final poll screen")
    frames = []
    narration_path = OUT/"narration.txt"
    narration = narration_path.read_text(encoding="utf-8") if narration_path.exists() else headline
    caption_chunks=_subtitle_chunks(narration)
    if not caption_chunks:
        caption_chunks=[headline]
    weights=[max(1,len(re.sub(r"\s+","",chunk))) for chunk in caption_chunks]
    total_weight=sum(weights)
    for idx, caption in enumerate(caption_chunks):
        source=unique[idx % len(unique)]
        frame = OUT/f"scene-{idx:02d}.jpg"
        _cover_frame(headline,source,style,idx+1,caption=caption).save(frame,quality=92)
        frames.append((frame,available*weights[idx]/total_weight))
    # Final hold frame gives viewers time to answer a poll in the comments.
    poll_frame = OUT/"scene-poll.jpg"
    _cover_frame(headline, unique[0], style, len(unique)+1, poll=True).save(poll_frame, quality=92)
    frames.append((poll_frame,poll_seconds))
    cmd = [ffmpeg, "-y"]
    for frame,hold_seconds in frames:
        cmd += ["-loop", "1", "-t", str(hold_seconds), "-i", str(frame)]
    cmd += ["-i", str(audio)]
    filters=[]
    for i in range(len(frames)):
        prefix=f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
        if i < len(frames)-1:
            # Slow Ken Burns motion keeps archival politician photos alive without
            # distorting the face or interfering with the narration subtitles.
            motion="zoompan=z='min(zoom+0.00012,1.04)':x='iw/2-(iw/zoom/2)+6*sin(on/18)':y='ih/2-(ih/zoom/2)+6*cos(on/21)':d=1:s=1080x1920:fps=30"
            filters.append(prefix+","+motion+f",format=yuv420p[v{i}];")
        else:
            # Keep the final poll steady for legibility.
            filters.append(prefix+f",fps=30,format=yuv420p[v{i}];")
    inputs="".join(filters)
    inputs += "".join(f"[v{i}]" for i in range(len(frames))) + f"concat=n={len(frames)}:v=1:a=0[outv]"
    video = OUT/"seoul-journal-short.mp4"
    cmd += ["-filter_complex", inputs, "-map", "[outv]", "-map", f"{len(frames)}:a", "-c:v", "libx264", "-preset", "medium", "-af", "atempo=1.2", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(video)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise RuntimeError("FFmpeg multi-scene render failed: " + result.stderr[-1200:])
    # Prove the poll survived the final mux instead of trusting an intermediate frame.
    final_probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(video)],capture_output=True,text=True,check=True)
    final_duration=float(final_probe.stdout.strip())
    proof_at=max(0.0,final_duration-1.5)
    proof=OUT/"poll-proof.jpg"
    proof_cmd=[ffmpeg,"-y","-ss",f"{proof_at:.3f}","-i",str(video),"-frames:v","1","-q:v","2",str(proof)]
    proof_result=subprocess.run(proof_cmd,capture_output=True,text=True,timeout=60)
    if proof_result.returncode or not proof.is_file():
        raise RuntimeError("Final poll proof frame extraction failed")
    with Image.open(poll_frame) as expected_im, Image.open(proof) as actual_im:
        expected=expected_im.convert("L").resize((180,320))
        actual=actual_im.convert("L").resize((180,320))
        import PIL.ImageChops
        diff=PIL.ImageChops.difference(expected,actual)
        mean_difference=sum(diff.getdata())/(180*320)
    if mean_difference>18:
        raise RuntimeError(f"Final poll proof mismatch ({mean_difference:.2f}); private upload blocked")
    render_receipt={
        "duration_seconds":round(final_duration,3),
        "motion_effect":"ffmpeg zoompan Ken Burns on narration scenes",
        "narration_subtitle_cards":len(caption_chunks),
        "poll_seconds":round(poll_seconds,3),
        "poll_proof_at_seconds":round(proof_at,3),
        "poll_proof_mean_difference":round(mean_difference,3),
        "poll_proof_file":proof.name,
    }
    (OUT/"render-receipt.json").write_text(json.dumps(render_receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    return video


def fetch_article_photos(url, lead_url, article_html, meta):
    """Fetch reusable Commons file photos of the named principal figure(s).

    A news article image is not automatically reusable. The article URL remains the
    editorial source, while the visual package uses files with explicit reusable
    Wikimedia Commons license metadata and records every source in the artifact.
    """
    del url,lead_url,article_html
    story=" ".join((meta.get("headline",""),meta.get("youtube_title",""),meta.get("narration","")))
    figures=[name for name in PRIORITY_FIGURES if name in story]
    if not figures:
        raise RuntimeError("Visual quality gate: no approved principal political figure named in the package")
    api="https://commons.wikimedia.org/w/api.php"
    photos=[]; hashes=set(); sources=[]
    for name in figures:
        english=PRIORITY_FIGURES[name]
        for query in (english,f"{english} politician"):
            try:
                response=get_with_retries(api,params={
                    "action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,
                    "gsrlimit":30,"prop":"imageinfo","iiprop":"url|extmetadata",
                    "iiurlwidth":1400,"format":"json",
                },timeout=20)
                pages=response.json().get("query",{}).get("pages",{})
            except Exception as exc:
                log(f"Commons search skipped for {name}: {type(exc).__name__}")
                continue
            tokens=[part.lower() for part in english.split() if len(part)>3 and part.lower()!="politician"]
            for page in pages.values():
                title=page.get("title","")
                if tokens and not all(token in title.lower() for token in tokens[:2]):
                    continue
                info=(page.get("imageinfo") or [{}])[0]
                ext=info.get("extmetadata",{})
                license_name=ext.get("LicenseShortName",{}).get("value","")
                if not any(key in license_name.lower() for key in ("cc","public domain","pd")):
                    continue
                image_url=info.get("thumburl") or info.get("url")
                if not image_url:
                    continue
                try:
                    raw=get_with_retries(image_url,timeout=20,attempts=2).content
                    im=Image.open(BytesIO(raw)).convert("RGB")
                    if min(im.size)<300:
                        continue
                    digest=hashlib.sha256(im.resize((64,64)).tobytes()).hexdigest()
                    if digest in hashes:
                        continue
                    hashes.add(digest)
                    target=OUT/f"source-photo-{len(photos):02d}.jpg"
                    im.save(target,quality=90)
                    photos.append(target)
                    sources.append({
                        "figure":name,"title":title,"description_url":info.get("descriptionurl"),
                        "license":license_name,"sha256":hashlib.sha256(raw).hexdigest(),
                        "usage_note":"자료사진; 현재 사건 현장 사진 아님",
                    })
                    if len(photos)>=8:
                        break
                except Exception as exc:
                    log(f"Commons photo skipped for {name}: {type(exc).__name__}")
            if len(photos)>=5:
                break
        if len(photos)>=8:
            break
    (OUT/"photo-sources.json").write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding="utf-8")
    meta["principal_figures"]=figures
    meta["photo_sources"]=sources
    log(f"RIGHTS_CLEARED_POLITICIAN_PHOTOS: {len(photos)} figures={','.join(figures)}")
    if len(photos)<5:
        raise RuntimeError(f"Visual quality gate: {len(photos)}/5 reusable politician photos; private upload blocked")
    return photos

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
    ch=yt.channels().list(part="snippet,contentDetails",mine=True).execute()
    items=ch.get("items",[])
    if len(items)!=1 or items[0]["id"]!=expected:
        got=items[0]["id"] if items else "NO_CHANNEL"
        name=items[0]["snippet"]["title"] if items else "NO_CHANNEL"
        raise RuntimeError(f"채널 ID 검증 실패: 인증 채널={name} ({got}); 예상 채널과 일치하지 않아 업로드 중단.")
    # Idempotency guard: inspect recent uploads before any insert. A repeated source URL
    # or normalized title is skipped, preventing scheduled/manual runs from duplicating a Short.
    uploads_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
    recent_ids = []
    page_token = None
    for _ in range(2):  # latest 100 uploads is sufficient for daily news deduplication
        if not uploads_id:
            break
        page = yt.playlistItems().list(
            part="contentDetails", playlistId=uploads_id, maxResults=50, pageToken=page_token
        ).execute()
        recent_ids.extend(row["contentDetails"]["videoId"] for row in page.get("items", []))
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    def title_key(value):
        return re.sub(r"[^\w]+", "", str(value).casefold(), flags=re.UNICODE)
    expected_title_key = title_key(meta["youtube_title"])
    for offset in range(0, len(recent_ids), 50):
        existing = yt.videos().list(
            part="snippet,status", id=",".join(recent_ids[offset:offset+50])
        ).execute().get("items", [])
        for old in existing:
            old_snippet = old.get("snippet", {})
            old_description = old_snippet.get("description", "")
            old_title = old_snippet.get("title", "")
            if source_url in old_description or (expected_title_key and title_key(old_title) == expected_title_key):
                result = {
                    "video_id": old.get("id"),
                    "url": "https://studio.youtube.com/video/" + str(old.get("id")) + "/edit",
                    "privacy": old.get("status", {}).get("privacyStatus", "unknown"),
                    "channel_title": items[0]["snippet"]["title"],
                    "channel_id": items[0]["id"],
                    "skipped_duplicate": True,
                    "duplicate_reason": "source_url" if source_url in old_description else "normalized_title",
                }
                log("DUPLICATE_SKIPPED: " + json.dumps(result, ensure_ascii=False))
                return result
    credits=[]
    for source in meta.get("photo_sources",[])[:5]:
        if source.get("description_url"):
            credits.append(f"자료사진({source.get('figure','정치인')}, {source.get('license','재사용 가능')}): {source['description_url']}")
    description=(meta["description"].replace("[원문 기사]",source_url)+"\n\n원문 기사: "+source_url)
    if credits:
        description+="\n\n"+"\n".join(credits)+"\n자료사진은 현재 사건 현장 사진이 아닙니다."
    description+="\n\n#Shorts #서울저널 #정치뉴스"
    body={"snippet":{"title":meta["youtube_title"][:100],"description":description[:4900],"categoryId":"25","tags":["서울저널","정치뉴스","대한민국정치","Shorts"]},
          "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}}
    req=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(video),mimetype="video/mp4",resumable=True,chunksize=5*1024*1024))
    response=None
    while response is None:
        _,response=req.next_chunk()
    video_id=response["id"]
    # YouTube may initially return P0D and reject a custom thumbnail while the
    # new upload is still processing. Wait for a real duration before setting it.
    saved=[]
    for _ in range(36):
        saved=yt.videos().list(part="snippet,status,contentDetails,processingDetails",id=video_id).execute().get("items",[])
        if saved:
            processing=saved[0].get("processingDetails",{}).get("processingStatus")
            duration=saved[0].get("contentDetails",{}).get("duration")
            if processing=="failed":
                raise RuntimeError("YouTube video processing failed; private upload needs investigation")
            if duration and duration!="P0D" and processing in (None,"succeeded"):
                break
        time.sleep(5)
    else:
        raise RuntimeError("YouTube processing did not finish within 3 minutes; thumbnail was not applied")
    thumbnail_status="not_set"
    thumbnail_error=""
    for attempt in range(6):
        try:
            yt.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(str(OUT/"cover.jpg"),mimetype="image/jpeg")).execute()
            thumbnail_status="api_set"
            break
        except Exception as exc:
            thumbnail_error=f"{type(exc).__name__}: {str(exc)[:240]}"
            if attempt<5: time.sleep(10)
    if thumbnail_status!="api_set":
        raise RuntimeError("Custom thumbnail application failed after retries: "+thumbnail_error)
    saved=yt.videos().list(part="snippet,status,contentDetails",id=video_id).execute().get("items",[])
    if len(saved)!=1:
        raise RuntimeError("YouTube upload readback failed; receipt must be investigated before retry")
    saved=saved[0]
    actual_channel=saved.get("snippet",{}).get("channelId")
    actual_privacy=saved.get("status",{}).get("privacyStatus")
    if actual_channel!=expected:
        raise RuntimeError(f"YouTube readback channel mismatch: {actual_channel}")
    if actual_privacy!="private":
        raise RuntimeError(f"YouTube readback privacy mismatch: {actual_privacy}")
    thumbnails=saved.get("snippet",{}).get("thumbnails",{})
    thumbnail_url=(thumbnails.get("maxres") or thumbnails.get("standard") or thumbnails.get("high") or thumbnails.get("default") or {}).get("url")
    return {
        "video_id":video_id,"url":"https://studio.youtube.com/video/"+video_id+"/edit",
        "privacy":actual_privacy,"channel_title":items[0]["snippet"]["title"],"channel_id":actual_channel,
        "duration":saved.get("contentDetails",{}).get("duration"),"thumbnail_status":thumbnail_status,
        "thumbnail_url":thumbnail_url,"poll_cta":"댓글로 A·B·C를 눌러 참여하세요",
        "thumbnail_benchmark_receipt":"thumbnail-benchmark-receipt.json",
    }

def main():
    scope=os.getenv("SEOUL_JOURNAL_CONTENT_SCOPE","politics").strip().casefold()
    if scope != CONTENT_SCOPE:
        raise RuntimeError("서울저널 워크플로는 정치(politics) 콘텐츠만 허용합니다.")
    url=os.getenv("INPUT_ARTICLE_URL","").strip()
    if not url:
        url,title_hint,selection=choose_naver_article()
        log(f"Auto-selected from Naver Politics: {url} ({selection})")
    else:
        title_hint=""; selection="User-supplied Naver Politics article URL (politics-only workflow)"
    title,body,img,article_html=extract(url)
    if title_hint and len(title)<8: title=title_hint
    meta=draft(title,body)
    meta["source_title"]=title; meta["source_url"]=url; meta["article_selection_method"]=selection; meta["content_scope"]="politics"
    (OUT/"package.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"narration.txt").write_text(meta["narration"],encoding="utf-8")
    log("SCRIPT_READY: "+meta["youtube_title"])
    audio=tts(meta["narration"])
    photos=fetch_article_photos(url,img,article_html,meta)
    (OUT/"package.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    video=render(meta["headline"],photos[0] if photos else None,audio,photos=photos)
    meta["thumbnail_benchmark"]=json.loads((OUT/"thumbnail-benchmark-receipt.json").read_text(encoding="utf-8"))
    (OUT/"package.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    log("VIDEO_RENDERED: "+str(video))
    result=upload_private(video,meta,url)
    (OUT/"upload_receipt.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    if result.get("skipped_duplicate"):
        log("YOUTUBE_UPLOAD_SKIPPED_DUPLICATE: " + json.dumps(result, ensure_ascii=False))
    else:
        log("YOUTUBE_PRIVATE_UPLOADED: " + json.dumps(result, ensure_ascii=False))
        log("Owner review required in YouTube Studio before making public.")
if __name__=="__main__":
    try: main()
    except Exception as e:
        log("FAILED: "+str(e)); sys.exit(1)
