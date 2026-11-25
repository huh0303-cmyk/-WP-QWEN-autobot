#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one source-grounded Seoul Journal political Short and upload PRIVATE only."""
import os, re, json, textwrap, subprocess, sys, random, hashlib, time, base64
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from urllib.parse import quote, urlparse
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
CANONICAL_SEOUL_JOURNAL_CHANNEL_ID="UChRUdHZlXSjftAqBtdDNEWA"
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
        "examples":examples,
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
    models = [os.getenv("SEOUL_JOURNAL_GEMINI_MODEL", "").strip(), "gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    models = list(dict.fromkeys(x for x in models if x))
    prompt = f"""당신은 서울저널의 한국어 정치 뉴스 기자 겸 팩트체커입니다.
기사 제목: {title}
기사 본문:
{body[:12000]}
세로 정치 쇼츠 패키지를 작성하세요. 60초 상한을 두지 말고 핵심 발언, 상대 반박, 확인된 사실과 맥락, 마지막 중립적 투표 질문이 완결될 만큼 작성하세요. 보통 공백 포함 650~1100자, 최소 5개 문단을 목표로 하되 근거가 부족하면 억지로 늘리지 마세요.
기사에 있는 배경·당사자 발언·확인된 사실을 구체적으로 설명하고 마지막은 '서울저널이 알려드립니다.'로 마무리하세요. 투표 질문은 내레이션이 모두 끝난 뒤 별도 화면에 표시합니다.
실제 쌍방 충돌이나 반박이 기사에서 확인될 때만 헤드라인에 '공방!', '대격돌!', '정면 대립!' 같은 강한 표현을 자연스럽게 사용할 수 있습니다. 실제 대립이 없으면 이런 표현을 만들지 마세요.
poll_question은 이 기사에서 시청자가 판단할 핵심 질문으로 쓰고, poll_options는 기사 속 서로 다른 입장 2개와 중립·추가확인 선택지 1개를 A/B/C 순서로 만드세요. 서로 겹치지 않게 하고 사람·주장을 정확히 표시하세요.
기사에 없는 사실·추측·숫자·인용은 만들지 마세요. JSON 객체 하나만 반환:
{{"headline":"썸네일용 10~18자 헤드라인","youtube_title":"사실에 근거한 제목 100자 이내","narration":"650~1100자 기자 내레이션(근거가 부족하면 더 짧게)","description":"중립적 요약과 [원문 기사] 자리","source_note":"확인된 사실과 한계","poll_question":"15~28자 중립 질문","poll_options":["18자 이내 선택지","18자 이내 선택지","18자 이내 중립 선택지"]}}"""
    errors = []
    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)
            result = model.generate_content(prompt, generation_config={"temperature": 0.35, "response_mime_type": "application/json"})
            raw = (result.text or "").strip().strip("`")
            data = json.loads(raw)
            narration = str(data.get("narration", "")).strip()
            poll_question=str(data.get("poll_question","")).strip()
            poll_options=[str(choice).strip() for choice in data.get("poll_options",[]) if str(choice).strip()]
            poll_valid=(15<=len(poll_question)<=32 and len(poll_options)==3
                        and all(2<=len(choice)<=22 for choice in poll_options)
                        and len(set(poll_options))==3)
            if len(narration) >= 420 and poll_valid:
                data["narration"] = narration
                data["poll_question"] = poll_question
                data["poll_options"] = poll_options
                log(f"WRITER_ENGINE=gemini model={model_name} narration_chars={len(narration)}")
                return data
            errors.append(f"{model_name}:narration={len(narration)}:poll_valid={poll_valid}")
        except Exception as exc:
            errors.append(f"{model_name}:{type(exc).__name__}")
    raise RuntimeError("Gemini writing chain failed or narration too short: " + ", ".join(errors))

# Keep this list limited to voice names returned by Edge's current voice list.
# Invalid/retired names make the timestamp fallback fail before rendering.
EDGE_VOICES = [
    ("ko-KR-HyunsuMultilingualNeural", "male_deep"),
    ("ko-KR-InJoonNeural", "male_documentary"),
    ("ko-KR-SunHiNeural", "female_anchor"),
]

def tts(text):
    """Create narration plus word/phrase timestamps for exact subtitle timing."""
    p = OUT / "voice.mp3"
    errors = []
    # Primary path: rotating 3-male/3-female narrators, synthesized sentence by sentence so
    # every word time is measured (exact subtitle sync). Fish/Edge below are fallbacks only,
    # unless SEOUL_JOURNAL_TTS_ENGINE=fish is set explicitly.
    if os.getenv("SEOUL_JOURNAL_TTS_ENGINE", "roster").strip().casefold() != "fish":
        try:
            import sj_av
            res = sj_av.synthesize_roster_voice(text, OUT, log=log)
            log(f"TTS_ENGINE=edge_sentence_timed voice={res['voice']} gender={res['gender']} tone={res['tone']} sentences={res['sentences']} audio={res['audio_seconds']}s")
            return p
        except Exception as exc:
            errors.append(f"Roster TTS failed ({type(exc).__name__}: {str(exc)[:200]})")
            log("TTS_ROSTER_FAILED " + errors[-1])
    voice_name, voice_role = random.choice(EDGE_VOICES)
    fish_ids = [x.strip() for x in os.getenv("FISH_AUDIO_VOICE_IDS","").split(",") if x.strip()]
    fish_voice = random.choice(fish_ids) if fish_ids else ""
    api_key = os.getenv("FISH_AUDIO_API_KEY", "").strip()
    if api_key:
        try:
            r = requests.post(
                "https://api.fish.audio/v1/tts/stream/with-timestamp",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "model": "s2.1-pro-free",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json={"text": text, "format": "mp3", "latency":"balanced", **({"reference_id": fish_voice} if fish_voice else {})},
                timeout=180,stream=True,
            )
            r.raise_for_status()
            audio_chunks=[]; alignment_by_chunk={}
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                try:
                    event=json.loads(line.removeprefix("data: "))
                except json.JSONDecodeError:
                    continue
                if event.get("audio_base64"):
                    audio_chunks.append(base64.b64decode(event["audio_base64"]))
                if event.get("alignment") is not None:
                    alignment_by_chunk[int(event["chunk_seq"])]=event
            p.write_bytes(b"".join(audio_chunks))
            timeline=[]
            for chunk_seq,event in sorted(alignment_by_chunk.items()):
                offset=float(event.get("chunk_audio_offset_sec",0))
                for segment in event["alignment"].get("segments",[]):
                    timeline.append({"text":str(segment.get("text","")).strip(),"start":float(segment["start"])+offset,"end":float(segment["end"])+offset,"chunk_seq":chunk_seq})
            timeline=[row for row in timeline if row["text"] and row["end"]>row["start"]]
            if p.stat().st_size<2000 or not timeline:
                raise RuntimeError("Fish Audio returned audio without usable timestamp alignment")
            # Reject unusable provider transcripts before rendering; fall back to Edge.
            # This preserves the approved narration and prevents fabricated subtitles.
            import difflib
            expected="".join(c.casefold() for c in text if c.isalnum())
            actual="".join(c.casefold() for seg in timeline for c in seg["text"] if c.isalnum())
            similarity=difflib.SequenceMatcher(None,expected,actual,autojunk=False).ratio() if expected and actual else 0.0
            if similarity < 0.85:
                raise RuntimeError(f"Fish timestamp transcript mismatch (similarity={similarity:.3f}); trying Edge TTS")
            (OUT/"tts-timeline.json").write_text(json.dumps({"engine":"fish_audio","segments":timeline},ensure_ascii=False,indent=2),encoding="utf-8")
            log(f"TTS_ENGINE=fish_audio_timestamped model=s2.1-pro-free voice_role={voice_role} segments={len(timeline)} bytes={p.stat().st_size}")
            return p
        except Exception as exc:
            errors.append(f"Fish Audio failed ({type(exc).__name__}: {str(exc)[:180]})")
    else:
        errors.append("Fish Audio API key not configured; trying free Edge TTS")

    # Edge TTS is a free fallback. No paid provider is called if it fails.
    try:
        import asyncio
        import edge_tts
        async def save_edge():
            audio=[]; timeline=[]
            async for chunk in edge_tts.Communicate(
                text, voice_name, boundary="WordBoundary"
            ).stream():
                if chunk["type"]=="audio": audio.append(chunk["data"])
                elif chunk["type"]=="WordBoundary":
                    start=float(chunk["offset"])/10_000_000
                    timeline.append({"text":chunk["text"],"start":start,"end":start+float(chunk["duration"])/10_000_000})
            p.write_bytes(b"".join(audio))
            (OUT/"tts-timeline.json").write_text(json.dumps({"engine":"edge_tts","segments":timeline},ensure_ascii=False,indent=2),encoding="utf-8")
            return timeline
        edge_timeline=[]
        for attempt in range(3):
            try:
                edge_timeline=asyncio.run(save_edge())
                if p.exists() and p.stat().st_size >= 2000 and edge_timeline:
                    break
            except Exception as edge_exc:
                if attempt == 2:
                    raise
                import time
                time.sleep(2 * (attempt + 1))
        if p.exists() and p.stat().st_size >= 2000 and edge_timeline:
            log(f"TTS_ENGINE=edge_tts_timestamped voice={voice_name} voice_role={voice_role} segments={len(edge_timeline)} bytes={p.stat().st_size}")
            return p
        errors.append("Edge TTS returned invalid audio")
    except Exception as exc:
        errors.append(f"Edge TTS failed ({type(exc).__name__}: {str(exc)[:180]})")

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

def _cover_frame(headline,photo,style,index,caption="",poll=False,thumbnail=False,
                 poll_question="",poll_options=None):
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
    # Badge width follows its text so it never collides with the brand name.
    badge_font=_font(42)
    badge_w=draw.textbbox((0,0),style["badge"],font=badge_font)[2]
    badge_right=42+badge_w+32
    draw.rectangle((42,34,badge_right,105),fill=style["accent"])
    draw.text((58,43),style["badge"],font=badge_font,fill=(255,255,255),stroke_width=1,stroke_fill=(0,0,0))
    draw.text((badge_right+26,36),"서울저널",font=_font(54),fill=(255,255,255))
    draw.text((W-290,52),"자율 구독",font=_font(36),fill=(255,255,255))
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
            choices=list(poll_options or [])
            if len(choices)!=3:
                raise RuntimeError("Final poll requires exactly three story-specific choices")
            lines=textwrap.wrap(poll_question,width=14,break_long_words=True,break_on_hyphens=False)[:2]
            lines += [f"{letter}  {choice}" for letter,choice in zip("ABC",choices)]
            font=_font(58); y=560
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
    if not thumbnail:
        draw.text((540,1620),"서울저널  |  자율 후원  농협 352-2371-04-7373",
                  anchor="mt",font=_font(36),fill=(255,224,75),stroke_width=5,stroke_fill=(0,0,0))
    return base.convert("RGB")

def build_caption_cues(timeline_path, max_chars=26, max_seconds=3.0):
    """Group timestamped TTS segments into fast, speech-synchronous caption cues."""
    data=json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    segments=data.get("segments",[])
    if not segments:
        raise RuntimeError("Timestamped narration has no segments; subtitle render blocked")
    narration=Path(timeline_path).with_name("narration.txt").read_text(encoding="utf-8")
    # Fish timestamp text can omit punctuation, split words, or normalize spoken
    # numerals. Never replace approved narration with unverified provider text.
    indices=[index for index,char in enumerate(narration) if char.isalnum()]
    normalized="".join(narration[index].casefold() for index in indices)
    spoken_parts=["".join(c.casefold() for c in seg.get("text","") if c.isalnum()) for seg in segments]
    combined="".join(spoken_parts)
    if not normalized:
        raise RuntimeError("Approved narration is empty; subtitles blocked")
    if combined==normalized:
        offset=0; source_start=0
        for segment,spoken in zip(segments,spoken_parts):
            if not spoken:
                segment["text"]=""
                continue
            offset+=len(spoken)
            source_end=indices[offset] if offset<len(indices) else len(narration)
            segment["text"]=narration[source_start:source_end]
            source_start=source_end
    else:
        # A provider transcription mismatch is not permission to invent subtitles.
        # Fall back to the exact approved text and allocate its characters over the
        # measured TTS segment durations. Preserve audio timing and log the drift.
        import difflib
        similarity=difflib.SequenceMatcher(None,normalized,combined,autojunk=False).ratio()
        if similarity<0.85 or not combined:
            raise RuntimeError(f"TTS transcript differs materially from approved narration (similarity={similarity:.3f}); subtitles blocked")
        log(f"TTS_ALIGNMENT_FALLBACK similarity={similarity:.3f}; approved narration retained")
        weights=[max(0.001,float(seg.get("end",0))-float(seg.get("start",0))) for seg in segments]
        total=sum(weights); cumulative=0.0; source_start=0
        for i,(segment,weight) in enumerate(zip(segments,weights)):
            cumulative+=weight
            char_end=round(len(indices)*cumulative/total)
            char_end=max(char_end,0 if i==0 else previous_end)
            char_end=min(len(indices),char_end)
            source_end=indices[char_end] if char_end<len(indices) else len(narration)
            segment["text"]=narration[source_start:source_end]
            source_start=source_end
            previous_end=char_end
    cues=[]; current=[]; cue_words=[]; cue_start=None; cue_end=None
    def clean_join(parts):
        value="".join(parts)
        return re.sub(r"\s+([,.!?。！？])",r"\1",value).strip()
    def flush():
        nonlocal current,cue_words,cue_start
        if current:
            cues.append({"text":clean_join(current),"start":cue_start,"end":cue_end,"words":cue_words})
        current=[]; cue_words=[]; cue_start=None
    for segment in segments:
        text=segment.get("text","")
        start=float(segment.get("start",0)); end=float(segment.get("end",0))
        if not text or end<=start: continue
        trial=clean_join(current+[text])
        if current and (len(trial)>max_chars or end-cue_start>max_seconds):
            flush()
        if cue_start is None: cue_start=start
        current.append(text); cue_end=end
        cue_words.append({"text":text,"start":round(start,3),"end":round(end,3)})
        # Break captions at natural phrase ends so each card reads as one thought.
        so_far=len(clean_join(current))
        stripped=text.rstrip()
        if (stripped.endswith((".","!","?","。","！","？")) and so_far>=8) or (stripped.endswith((",","，")) and so_far>=14):
            flush()
    flush()
    if not cues:
        raise RuntimeError("Timestamped narration could not form subtitle cues")
    for index,cue in enumerate(cues):
        cue["start"]=round(float(cue["start"]),3); cue["end"]=round(float(cue["end"]),3)
        if index and cue["start"]<cues[index-1]["end"]-0.15:
            raise RuntimeError("Subtitle timestamp overlap exceeds tolerance")
        if cue["end"]-cue["start"]>max_seconds+0.75:
            raise RuntimeError("A subtitle cue is too slow; timing alignment blocked")
    receipt={"engine":data.get("engine"),"max_chars":max_chars,"max_seconds":max_seconds,"cues":cues}
    (OUT/"subtitle-cues.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    return cues

def _repair_scene_groups(raw, n, photo_count):
    """Make the model's scene plan structurally valid (gaps, overlaps, adjacent duplicates)
    without changing the photo it picked for any cue it did cover. A low-confidence or
    out-of-range photo choice is still rejected."""
    mapping=[None]*n
    for g in sorted(raw,key=lambda x:int(x.get("start",0)) if isinstance(x,dict) else 0):
        try:
            s=int(g["start"]); e=int(g["end"]); p=int(g["photo_index"]); c=float(g.get("confidence",0))
        except Exception:
            continue
        if not 0<=p<photo_count or c<0.65:
            raise RuntimeError("Scene plan low-confidence/invalid photo")
        for i in range(max(0,s),min(n-1,e)+1):
            if mapping[i] is None: mapping[i]=p
    first=next((m for m in mapping if m is not None),None)
    if first is None:
        raise RuntimeError("Scene plan empty")
    last=first
    for i in range(n):
        if mapping[i] is None: mapping[i]=last
        else: last=mapping[i]
    groups=[]
    for i,p in enumerate(mapping):
        if groups and groups[-1]["photo_index"]==p: groups[-1]["end"]=i
        else: groups.append({"start":i,"end":i,"photo_index":p,"confidence":0.8})
    return groups

def plan_visual_sequence(cues, photos, photo_sources):
    """Use actual image pixels and narration meaning to choose semantic change points."""
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key:
        raise RuntimeError("Visual scene matching requires GEMINI_API_KEY; round-robin photos are forbidden")
    genai.configure(api_key=key)
    cue_lines="\n".join(f"CUE_{i} [{cue['start']:.2f}-{cue['end']:.2f}]: {cue['text']}" for i,cue in enumerate(cues))
    photo_lines=[]
    for i,source in enumerate(photo_sources[:len(photos)]):
        photo_lines.append(f"PHOTO_{i}: figure={source.get('figure','')}; title={source.get('title','')}; description={source.get('visual_description','')}; categories={source.get('categories','')}")
    prompt=f"""당신은 서울저널 정치 쇼츠의 영상 편집 감독입니다. 실제 사진 픽셀과 내레이션 자막 의미를 함께 보고 사진을 배치하세요.
규칙:
- 단순 0,1,2 순환은 금지합니다. 인물·발언·기자회견·국회/회의·법률 맥락을 실제 사진 내용과 맞추세요.
- 화제가 바뀌는 지점에서만 사진을 교체하고 보통 연속 자막 2~6개를 한 그룹으로 묶으세요.
- 연결이 약한 사진은 사용하지 마세요. 최소 4개, 최대 12개 그룹, 실제 사진 최소 3개를 사용하세요.
- 한 사진이 전체 자막의 45%를 넘지 않게 하세요. confidence 0.65 미만이면 blocked=true로 하세요.
자막:\n{cue_lines}\n사진 메타데이터:\n{chr(10).join(photo_lines)}
JSON만 반환: {{"blocked":false,"groups":[{{"start":0,"end":3,"photo_index":0,"confidence":0.86,"reason":"발언 자막과 기자회견 사진"}}]}}
start/end는 포함 범위이며 CUE_0부터 CUE_{len(cues)-1}까지 중복·누락 없이 덮어야 합니다."""
    content=[prompt]; opened=[]
    try:
        for i,photo in enumerate(photos):
            image=Image.open(photo).convert("RGB"); opened.append(image)
            content.extend([f"PHOTO_{i} 실제 이미지:",image])
        errors=[]
        models=[os.getenv("SEOUL_JOURNAL_GEMINI_MODEL","").strip(),"gemini-3.1-flash-lite","gemini-2.5-flash-lite","gemini-2.5-flash"]
        for model_name in dict.fromkeys(x for x in models if x):
            try:
                response=genai.GenerativeModel(model_name).generate_content(content,generation_config={"temperature":0.15,"response_mime_type":"application/json"})
                plan=json.loads((response.text or "").strip().strip("`"))
                if plan.get("blocked"): raise RuntimeError("Scene director found insufficient visual relevance")
                groups=_repair_scene_groups(plan.get("groups",[]),len(cues),len(photos)); expected=0; mapping=[None]*len(cues); used=[]
                for group in groups:
                    start=int(group["start"]); end=int(group["end"]); photo_index=int(group["photo_index"]); confidence=float(group.get("confidence",0))
                    if start!=expected or end<start or end>=len(cues): raise RuntimeError("Scene plan range gap/overlap")
                    if not 0<=photo_index<len(photos) or confidence<0.65: raise RuntimeError("Scene plan low-confidence/invalid photo")
                    for idx in range(start,end+1): mapping[idx]=photo_index
                    used.append(photo_index); expected=end+1
                if expected!=len(cues) or any(index is None for index in mapping): raise RuntimeError("Scene plan does not cover narration")
                if len(groups)<min(4,len(cues)) or len(groups)>12 or len(set(used))<min(3,len(photos)): raise RuntimeError("Scene plan variety/change-point rules failed")
                if any(groups[i]["photo_index"]==groups[i-1]["photo_index"] for i in range(1,len(groups))): raise RuntimeError("Adjacent duplicate visual groups must be merged")
                counts={index:mapping.count(index) for index in set(mapping)}
                if max(counts.values())/len(mapping)>0.65: raise RuntimeError("One photo dominates over 65 percent")
                receipt={"engine":model_name,"groups":groups,"cue_to_photo":mapping,"photo_usage":counts}
                (OUT/"visual-plan.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
                return mapping
            except Exception as exc:
                errors.append(f"{model_name}:{type(exc).__name__}:{str(exc)[:100]}")
        raise RuntimeError("Semantic visual planning failed: "+" | ".join(errors))
    finally:
        for image in opened: image.close()

def render(headline, photo, audio, photos=None, poll_question="", poll_options=None):
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
    duration = float(probe.stdout.strip())
    poll_seconds = 6.0
    # The minimum is five distinct source photos, not every downloaded candidate.
    # The final poll is a separate six-second scene after narration.
    required_photo_seconds = 5 * 1.5
    if duration < required_photo_seconds:
        raise RuntimeError(f"Narration is too short for five source images: {duration:.2f}s < {required_photo_seconds:.2f}s")
    frames = []
    cues=build_caption_cues(OUT/"tts-timeline.json")
    if cues[-1]["end"]>duration+0.5 or duration-cues[-1]["end"]>2.5:
        raise RuntimeError("Narration audio and timestamp timeline duration do not agree")
    active_cues=list(cues)
    if len(active_cues)<4:
        raise RuntimeError("Too few timestamped subtitle cues before the final poll")
    photo_sources=json.loads((OUT/"photo-sources.json").read_text(encoding="utf-8"))
    if len(photo_sources)<len(unique):
        raise RuntimeError("Photo metadata is incomplete; semantic scene matching blocked")
    photo_mapping=plan_visual_sequence(active_cues,unique,photo_sources)
    # Captions are drawn by libass from subtitles.ass (outlined text, active word
    # highlighted). Background scenes follow the photo plan, so a photo keeps one
    # continuous Ken Burns move instead of restarting at every caption.
    import sj_av
    FPS=30
    groups=[]
    for idx in range(len(active_cues)):
        photo_index=photo_mapping[idx]
        if groups and groups[-1]["photo"]==photo_index:
            groups[-1]["end_cue"]=idx
        else:
            groups.append({"photo":photo_index,"start_cue":idx,"end_cue":idx})
    previous_frame=0
    for gi,group in enumerate(groups):
        end_t=duration if gi+1==len(groups) else active_cues[groups[gi+1]["start_cue"]]["start"]
        # Quantize every scene boundary to a whole frame from the running total so
        # rounding can never accumulate into audio/subtitle drift.
        end_frame=max(previous_frame+1,round(end_t*FPS))
        hold_seconds=(end_frame-previous_frame)/FPS
        previous_frame=end_frame
        if hold_seconds>12.0:
            raise RuntimeError(f"Photo scene too long to stay lively: scene={gi} hold={hold_seconds:.2f}")
        frame = OUT/f"scene-{gi:02d}.jpg"
        _cover_frame(headline,unique[group["photo"]],style,gi+1).save(frame,quality=92)
        frames.append((frame,hold_seconds))
    subtitle_events=sj_av.write_ass(active_cues,OUT/"subtitles.ass")
    # Narration and every synchronized subtitle end first. Only then does the
    # separate silent poll hold begin.
    poll_frame = OUT/"scene-poll.jpg"
    _cover_frame(headline, unique[0], style, len(unique)+1, poll=True,
                 poll_question=poll_question,poll_options=poll_options).save(poll_frame, quality=92)
    frames.append((poll_frame,poll_seconds))
    cmd = [ffmpeg, "-y"]
    for frame,hold_seconds in frames:
        # -framerate 30 is essential: without it the looped still is read at 25 fps while
        # zoompan emits one frame per input frame, which made the video 17% shorter than
        # the narration (subtitles drifted early and the end of the audio was cut off).
        cmd += ["-framerate", "30", "-loop", "1", "-t", f"{hold_seconds:.6f}", "-i", str(frame)]
    cmd += ["-i", str(audio)]
    filters=[]
    for i in range(len(frames)):
        prefix=f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
        if i < len(frames)-1:
            # Smooth, centred Ken Burns (alternating push-in / pull-out). The still is
            # upscaled first so zoompan's integer cropping does not shimmer.
            zoom="min(1.045,1+0.00013*on)" if i%2==0 else "max(1.0,1.045-0.00013*on)"
            motion=f"scale=1620:2880,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
            filters.append(prefix+","+motion+f",format=yuv420p[v{i}];")
        else:
            # Keep the final poll steady for legibility.
            filters.append(prefix+f",fps=30,format=yuv420p[v{i}];")
    inputs="".join(filters)
    inputs += "".join(f"[v{i}]" for i in range(len(frames))) + f"concat=n={len(frames)}:v=1:a=0[cv];"
    inputs += "[cv]ass=filename=subtitles.ass[outv];"
    inputs += f"[{len(frames)}:a]apad=pad_dur={poll_seconds:.3f}[outa]"
    video = OUT/"seoul-journal-short.mp4"
    cmd += ["-filter_complex", inputs, "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(video)]
    # cwd=OUT lets the ass filter use a plain relative path (no drive-letter escaping).
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=str(OUT))
    if result.returncode:
        raise RuntimeError("FFmpeg multi-scene render failed: " + result.stderr[-1200:])
    # Prove the poll survived the final mux instead of trusting an intermediate frame.
    final_probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(video)],capture_output=True,text=True,check=True)
    final_duration=float(final_probe.stdout.strip())
    # Sync gate: video must be exactly narration + poll long. A shortfall means the
    # subtitles and photos have drifted away from the voice, so block the upload.
    expected_total=previous_frame/FPS+poll_seconds
    if abs(final_duration-expected_total)>0.35 or abs(final_duration-(duration+poll_seconds))>0.5:
        raise RuntimeError(f"A/V length mismatch: video={final_duration:.2f}s expected={expected_total:.2f}s narration+poll={duration+poll_seconds:.2f}s")
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
        "narration_subtitle_cards":len(active_cues),
        "subtitle_engine":"libass (subtitles.ass, active-word highlight)",
        "subtitle_events":subtitle_events,
        "photo_scenes":len(frames)-1,
        "expected_total_seconds":round(expected_total,3),
        "subtitle_timing_source":"TTS word timestamps, sentence-by-sentence synthesis",
        "subtitle_max_hold_seconds":round(max(c["end"]-c["start"] for c in active_cues),3),
        "visual_plan_file":"visual-plan.json",
        "poll_seconds":round(poll_seconds,3),
        "poll_starts_after_narration_seconds":round(duration,3),
        "poll_question":poll_question,
        "poll_options":list(poll_options or []),
        "poll_proof_at_seconds":round(proof_at,3),
        "poll_proof_mean_difference":round(mean_difference,3),
        "poll_proof_file":proof.name,
        "support_line_present":True,
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
                    "gsrlimit":30,"prop":"imageinfo","iiprop":"url|extmetadata|mime",
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
                lower_title=title.casefold()
                mime=info.get("mime","").casefold()
                if any(word in lower_title for word in ("signature","logo","flag","map","diagram","coat of arms")):
                    continue
                if mime in ("image/svg+xml","image/gif"):
                    continue
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
                        "license":license_name,
                        "license_url":ext.get("LicenseUrl",{}).get("value",""),
                        "artist":BeautifulSoup(ext.get("Artist",{}).get("value",""),"html.parser").get_text(" ",strip=True),
                        "credit_url":((BeautifulSoup(ext.get("Credit",{}).get("value",""),"html.parser").find("a") or {}).get("href","") if ext.get("Credit",{}).get("value") else ""),
                        "visual_description":BeautifulSoup(ext.get("ImageDescription",{}).get("value","") or ext.get("ObjectName",{}).get("value",""),"html.parser").get_text(" ",strip=True)[:500],
                        "categories":ext.get("Categories",{}).get("value","")[:500],
                        "attribution_required":ext.get("AttributionRequired",{}).get("value","").casefold()=="true",
                        "sha256":hashlib.sha256(raw).hexdigest(),
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

def compact_photo_credits(photo_sources):
    """Keep only legally required, deduplicated attribution lines in the public description."""
    rows=[]; seen=set()
    for source in photo_sources:
        if not source.get("attribution_required"):
            continue
        artist=source.get("artist") or source.get("figure") or "자료사진 제공자"
        credit_url=source.get("credit_url") or source.get("description_url") or ""
        license_name=source.get("license") or "재사용 허용"
        license_url=source.get("license_url") or ""
        key=(artist,credit_url,license_name,license_url)
        if key in seen:
            continue
        seen.add(key)
        links=" · ".join(x for x in (credit_url,license_url) if x)
        rows.append(f"사진: {artist} · {license_name}"+(f" · {links}" if links else ""))
    return rows

def upload_private(video,meta,source_url):
    client_id=os.getenv("YOUTUBE_OAUTH_CLIENT_ID","").strip()
    client_secret=os.getenv("YOUTUBE_OAUTH_CLIENT_SECRET","").strip()
    refresh=os.getenv("SEOUL_JOURNAL_YOUTUBE_OAUTH_REFRESH_TOKEN","").strip()
    configured_expected=os.getenv("SEOUL_JOURNAL_YOUTUBE_CHANNEL_ID","").strip()
    expected=CANONICAL_SEOUL_JOURNAL_CHANNEL_ID
    if configured_expected and configured_expected!=expected:
        raise RuntimeError(f"서울저널 채널 ID 설정 오류: configured={configured_expected}; canonical={expected}")
    if not all([client_id,client_secret,refresh]):
        raise RuntimeError("YouTube 안전 업로드 차단: 서울저널 OAuth client/refresh token 중 하나 이상 누락되었습니다.")
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
    summary=meta.get("description","").split("[원문 기사]",1)[0].strip()
    summary=re.sub(r"https?://\S+","",summary).strip()
    description=summary[:700]+"\n\n원문: "+source_url
    credits=compact_photo_credits(meta.get("photo_sources",[]))
    if credits:
        description+="\n\n"+"\n".join(credits)
    description+="\n\n#Shorts #서울저널 #정치뉴스\n\n자율 후원\n농협 352-2371-04-7373"
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
        log("YOUTUBE_PROCESSING_PENDING: private upload exists; skip thumbnail and verify upload receipt")
    thumbnail_status="not_set"
    thumbnail_error=""
    for attempt in range(6) if saved and saved[0].get("contentDetails",{}).get("duration") not in (None, "P0D") else range(0):
        try:
            yt.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(str(OUT/"cover.jpg"),mimetype="image/jpeg")).execute()
            thumbnail_status="api_set"
            break
        except Exception as exc:
            thumbnail_error=f"{type(exc).__name__}: {str(exc)[:240]}"
            if attempt<5: time.sleep(10)
    if thumbnail_status!="api_set":
        log("THUMBNAIL_WARNING: private upload retained; "+(thumbnail_error or "YouTube processing pending"))
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
    auto_public=os.getenv("AUTO_PUBLIC_AFTER_VALIDATION","").strip().casefold()=="true"
    if auto_public:
        yt.videos().update(
            part="status",
            body={"id":video_id,"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}},
        ).execute()
        released=yt.videos().list(part="snippet,status,contentDetails",id=video_id).execute().get("items",[])
        if len(released)!=1 or released[0].get("snippet",{}).get("channelId")!=expected:
            raise RuntimeError("Automatic public release readback channel mismatch")
        actual_privacy=released[0].get("status",{}).get("privacyStatus")
        if actual_privacy!="public":
            raise RuntimeError(f"Automatic public release readback failed: {actual_privacy}")
        saved=released[0]
    thumbnails=saved.get("snippet",{}).get("thumbnails",{})
    thumbnail_url=(thumbnails.get("maxres") or thumbnails.get("standard") or thumbnails.get("high") or thumbnails.get("default") or {}).get("url")
    return {
        "video_id":video_id,"url":"https://studio.youtube.com/video/"+video_id+"/edit",
        "privacy":actual_privacy,"channel_title":items[0]["snippet"]["title"],"channel_id":actual_channel,
        "duration":saved.get("contentDetails",{}).get("duration"),"thumbnail_status":thumbnail_status,
        "thumbnail_url":thumbnail_url,"poll_cta":"댓글로 A·B·C를 눌러 참여하세요",
        "thumbnail_benchmark_receipt":"thumbnail-benchmark-receipt.json",
        "release_mode":"automatic_public_after_validation" if auto_public else "manual_private_review",
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
    video=render(
        meta["headline"], photos[0] if photos else None, audio, photos=photos,
        poll_question=meta["poll_question"], poll_options=meta["poll_options"],
    )
    meta["thumbnail_benchmark"]=json.loads((OUT/"thumbnail-benchmark-receipt.json").read_text(encoding="utf-8"))
    (OUT/"package.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    log("VIDEO_RENDERED: "+str(video))
    if os.getenv("VERIFY_ONLY","").strip().casefold()=="true":
        result={"upload_skipped":True,"privacy":"not_uploaded","reason":"verify_only","channel_id":CANONICAL_SEOUL_JOURNAL_CHANNEL_ID}
    else:
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
