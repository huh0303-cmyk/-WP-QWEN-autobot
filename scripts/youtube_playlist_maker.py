#!/usr/bin/env python3
"""No-extra-generation-cost playlist pipeline: existing assets + Gemini app exports.
Gemini subscription generation happens in the app. This worker consumes Drive assets;
it never purchases API music or images and never silently substitutes another provider.
"""
import os, random, sys, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT/'scripts'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import youtube_playlist_maker_legacy as base
from PIL import Image

list_folder_files=base.list_folder_files
download_drive_file=base.download_drive_file
IMAGE_EXTS=base.IMAGE_EXTS
THUMBNAIL_FOLDER_ID=base.THUMBNAIL_FOLDER_ID
PLAYLIST_CHANNELS=base.PLAYLIST_CHANNELS
CHANNEL_KEY=base.CHANNEL_KEY
log=base.log

def select_single_bank_image(workdir, service):
    images=list_folder_files(service, THUMBNAIL_FOLDER_ID, IMAGE_EXTS, 'image/')
    if not images: raise RuntimeError('WAITING_ASSETS: add a Gemini app thumbnail export to the channel Drive folder')
    picked=random.choice(images)
    path=os.path.join(workdir, 'playlist_background'+(os.path.splitext(picked['name'])[1] or '.jpg'))
    download_drive_file(service,picked['id'],path)
    return path

def bank_images(topic, workdir, service=None):
    global THUMBNAIL_FOLDER_ID
    THUMBNAIL_FOLDER_ID=base._channel_env('THUMBNAIL_FOLDER_ID',base._DEFAULT_THUMB_FOLDER)
    path=select_single_bank_image(workdir,service or base.get_drive_service())
    with Image.open(path) as image:
        if image.width < 1280 or image.height < 720:
            raise RuntimeError('WAITING_ASSETS: thumbnail must be at least 1280x720; do not upscale a poor image')
    return [path]

def no_paid_generation(*args, **kwargs):
    raise RuntimeError('PAID_GENERATION_DISABLED: use Gemini subscription app and save exports to Drive')

def metadata(topic, caption, duration_min):
    labels={'healing':'Nature Sounds', 'kpop':'Original K-pop', 'mbb':'Classical Music', 'globalmusic':'Romantic Songs', 'starbucks':'Instrumental Cafe Music'}
    label=labels[base.CHANNEL_KEY]
    title=f'{topic} | {label} | {round(duration_min)} min'
    return title, f'{label}: {topic}.\nPlaying time: {round(duration_min)} minutes.', [label,topic], False

base.GEMINI_API_KEY=''
base.OPENAI_API_KEY=''
base.GMAIL_APP_PASSWORD=''
base.PEXELS_API_KEY=''
base.PIXABAY_KEY=''
base.gemini_generate_text=no_paid_generation
base.gemini_generate_image=no_paid_generation
base.build_ai_images=bank_images
base.fetch_healing_photo=lambda theme,workdir: bank_images(theme,workdir)[0]
base.generate_youtube_title_description=metadata
base.pick_duration_target=lambda: (50*60,70*60)
# Keep the approved Gemini composition, rather than repainting it with legacy text bars.
base.make_channel_thumbnail=lambda channel,image,out,topic,**kwargs: base.make_photo_thumbnail(image,out)
# Preserve the existing rain/stream selection and bird sound mixing.
base.HEALING_THEME_DURATION_SEC={theme:(50*60,70*60) for theme in base.HEALING_THEME_DURATION_SEC}

def make_intro_video(image_path, audio_path, out_path):
    # Six-second gentle push-in, then hold; no extra video model or audio repetition.
    vf=("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        "zoompan=z='1+min(on,150)*0.0003':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=25,"
        "fade=t=in:st=0:d=1.2,format=yuv420p")
    base.run_ffmpeg(['ffmpeg','-y','-loop','1','-framerate','25','-i',image_path,'-i',audio_path,
        '-vf',vf,'-af','afade=t=in:st=0:d=0.5','-c:v','libx264','-preset','fast','-crf','21',
        '-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',out_path])
base.make_static_video=make_intro_video


LANGUAGE_TAGS={'korean':['한국어','korean','[ko]'], 'french':['프랑스어','불어','french','[fr]'],
    'japanese':['일본어','japanese','[ja]'], 'spanish':['스페인어','spanish','[es]'], 'italian':['이탈리아어','italian','[it]']}
_selected_language=''

def strict_tracks(tracks, keyword):
    global _selected_language
    language='korean' if base.CHANNEL_KEY=='kpop' else (_selected_language or keyword.lower())
    if base.CHANNEL_KEY not in {'kpop','globalmusic'}: return base._bring_longest_to_front(list(tracks))
    if base.CHANNEL_KEY == 'globalmusic' and language not in LANGUAGE_TAGS:
        # Calendar topics often carry Mixed; resolve from actual tagged assets.
        available = [lang for lang in ('french','japanese','spanish','italian')
                     if any(any(tag in t['name'].casefold() for tag in LANGUAGE_TAGS[lang]) for t in tracks)]
        if not available:
            raise RuntimeError('WAITING_ASSETS: no identified French/Japanese/Spanish/Italian vocals in source folder')
        state_path=Path(base.RECENT_TOPICS_FILE)
        state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        counts=state.get('romantic_language_counts',{})
        minimum=min(counts.get(lang,0) for lang in available)
        language=random.choice([lang for lang in available if counts.get(lang,0)==minimum])
        _selected_language=language
    tags=LANGUAGE_TAGS.get(language,[])
    matched=[t for t in tracks if any(tag in t['name'].casefold() for tag in tags)]
    if not matched: raise RuntimeError(f'WAITING_ASSETS: no explicitly tagged {language} vocals; refusing unrelated-language fallback')
    return base._bring_longest_to_front(matched)

def balanced_language(counts):
    languages=['french','japanese','spanish','italian']
    minimum=min(counts.get(lang,0) for lang in languages)
    return random.choice([lang for lang in languages if counts.get(lang,0)==minimum])

def pick_topic():
    global _selected_language
    path=Path(base.RECENT_TOPICS_FILE)
    state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    recent=state.get('recent',[])
    if base.CHANNEL_KEY=='globalmusic':
        counts=state.setdefault('romantic_language_counts',{})
        _selected_language=balanced_language(counts)
        counts[_selected_language]=counts.get(_selected_language,0)+1
        pool=['Golden Hour Acoustic Romance','Soft Songs for a Quiet Cafe','A Sweet Unplugged Evening','Warm Guitar Love Songs']
    elif base.CHANNEL_KEY=='kpop':
        _selected_language='korean'
        pool=['Korean Acoustic Pop Evening','Unplugged Korean Love Songs','Soft Korean Acoustic R&B','Korean Folk Pop for a Quiet Cafe']
    else:
        _selected_language=''
        pool=base.CHANNEL_TOPIC_POOLS.get(base.CHANNEL_KEY,base.AUTO_TOPIC_POOL)
    topic=random.choice([t for t in pool if t not in recent] or list(pool))
    state['recent']=([topic]+[t for t in recent if t!=topic])[:base.RECENT_TOPICS_MEMORY]
    path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    return topic,_selected_language
base.pick_auto_topic=pick_topic
base.filter_tracks_by_language=strict_tracks

if __name__=='__main__': base.main()
