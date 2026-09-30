"""Real moving nature footage, private review presets, randomized runtime."""
import hashlib, json, os, random, re, subprocess
from pathlib import Path
import requests
import healing_rain_review as job
from automation_hub.youtube_release import public_allowed, result_url, upload_privacy_status

SOURCE_POOLS = {
    'rain': [13166787, 9632520, 5754996, 32679327],
    'creek': [18132437, 7351460, 7067022, 5257861],
}
HISTORY_LIMIT = 50


def _history_path():
    return Path(os.environ.get('HEALING_THUMBNAIL_HISTORY', job.ROOT/'data/healing_thumbnail_history.json'))


def _read_history(path):
    try:
        rows=json.loads(path.read_text(encoding='utf-8'))
        return rows if isinstance(rows,list) else []
    except (OSError,ValueError):
        return []


def select_source(mode, seed, history):
    pool=SOURCE_POOLS[mode]
    recent=[int(row.get('source_id',0)) for row in reversed(history) if row.get('mode')==mode]
    available=[source_id for source_id in pool if source_id not in recent[:min(3,len(pool)-1)]] or pool
    return available[seed % len(available)]


def select_thumbnail_second(source_id, source_seconds, seed, history):
    upper=max(2,int(source_seconds)-2)
    candidates=list(range(2,upper+1))
    # Every legacy automation thumbnail used second 3 of one of these two
    # sources. Treat those pairs as permanently used during migration.
    used={(13166787,3),(18132437,3)}
    used.update((int(row.get('source_id',0)),int(row.get('thumbnail_second',-1))) for row in history[-HISTORY_LIMIT:])
    start=seed % len(candidates)
    for offset in range(len(candidates)):
        second=candidates[(start+offset)%len(candidates)]
        if (source_id,second) not in used:
            return second
    return candidates[start]


def record_thumbnail(path, payload):
    rows=_read_history(path)
    rows.append(payload)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(rows[-HISTORY_LIMIT:],ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,path)

def download(url, path):
    with requests.get(url,stream=True,timeout=90) as response:
        response.raise_for_status()
        with path.open('wb') as output:
            for chunk in response.iter_content(1024*1024): output.write(chunk)

def configure():
    token=os.environ.get('HEALING_SAMPLE_ID') or os.environ.get('SCHEDULE_ID') or os.environ.get('VPS_JOB_ID') or os.environ.get('GITHUB_RUN_ID','local-preview')
    seed=int(hashlib.sha256(token.encode()).hexdigest()[:16],16)
    rng=random.Random(seed)
    mode=os.environ.get('HEALING_VARIANT','random')
    if mode=='random': mode=rng.choice(['rain','creek'])
    if mode not in ('rain','creek'): raise ValueError('Unknown healing preset')
    minutes=rng.randint(74,175)
    job.DURATION=minutes*60
    job.MARKER='Review reference: healing-motion-'+token
    job.TITLE=(f'Rain on Green Leaves | {minutes} Minutes of Peaceful Forest Rain, No Music' if mode=='rain' else f'Clear Forest Stream & Birds | {minutes} Minutes of Refreshing Nature Sounds')
    scene='rain falling onto green leaves' if mode=='rain' else 'flowing water around mossy forest rocks'
    sound='newly synthesized continuous stereo rain' if mode=='rain' else 'flowing-water audio gently blended with a CC0 forest bird recording'
    job.DESCRIPTION=f'''Take a quiet break with {minutes} minutes of {scene}. Watch real moving nature footage: the water and leaves move naturally throughout the video, without titles, captions, or distracting graphics covering the scene.

The soundtrack uses {sound}. There is no music or narration. The visual footage is edited into a softly joined repeating scene, while the sound creates a calm background for reading, resting, journaling, or quiet work. This is an edited ambience rather than a single uninterrupted field recording.

Choose a comfortable listening level for your room or headphones. Let the natural textures sit gently in the background, and take a moment to slow down at your own pace. No special routine is needed; enjoy the moving greenery and water whenever you want a peaceful pause.

Footage: Pexels, used under the Pexels License. Bird ambience, when present: Magnesus, Freesound 723913, CC0.\n\n'''+job.MARKER
    return mode,seed,minutes

MODE,SEED,MINUTES=configure()
def render():
    work=job.WORK
    history_path=_history_path()
    history=_read_history(history_path)
    source_id=select_source(MODE,SEED,history)
    source=work/'source.mp4'
    download(f'https://www.pexels.com/download/video/{source_id}/',source)
    # Last second dissolves into first second; next loop begins where the dissolve ends.
    source_seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(source)]))
    end=min(40,int(source_seconds))
    if end<10: raise RuntimeError('Nature source is too short')
    thumbnail_second=select_thumbnail_second(source_id,source_seconds,SEED,history)
    job.ff('-ss',str(thumbnail_second),'-i',source,'-frames:v','1','-vf','scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080',work/'thumbnail.jpg')
    transition=f'[0:v]fps=24,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,split[a][b];[a]trim=start=1:end={end},setpts=PTS-STARTPTS[x];[b]trim=start=0:end=1,setpts=PTS-STARTPTS[y];[x][y]xfade=transition=fade:duration=1:offset={end-2}[v]'
    job.ff('-i',source,'-filter_complex_threads','1','-filter_complex',transition,'-map','[v]','-an','-c:v','libx264','-preset','fast','-b:v','2200k','-maxrate','2600k','-bufsize','5200k','-pix_fmt','yuv420p',work/'scene.mp4')
    tail=f'afade=t=in:d=4,afade=t=out:st={job.DURATION-6}:d=6'
    if MODE=='rain':
        inputs=['-f','lavfi','-i',f'anoisesrc=color=pink:sample_rate=48000:amplitude=0.65:seed={SEED%2147483646+1}','-f','lavfi','-i',f'anoisesrc=color=pink:sample_rate=48000:amplitude=0.65:seed={(SEED+73)%2147483646+1}']
        filters='[1:a]highpass=f=250,lowpass=f=7500,volume=0.7*(0.92+0.08*sin(t/29)):eval=frame[l];[2:a]highpass=f=180,lowpass=f=6800,volume=0.7*(0.92+0.08*sin(t/37)):eval=frame[r];[l][r]join=inputs=2:channel_layout=stereo,'+tail+'[a]'
    else:
        import shutil
        shutil.copyfile(job.ROOT/'assets/playlist-review/forest-birds-cc0.mp3',work/'birds.mp3')
        water_source=work/'water-source.mp4'
        download('https://www.pexels.com/download/video/5021254/',water_source)
        # Crossfade the field audio once into a seamless loop, then mix gentle birds.
        job.ff('-i',water_source,'-filter_complex','[0:a]asplit[x][y];[x]atrim=start=1:end=18,asetpts=PTS-STARTPTS[a];[y]atrim=start=0:end=1,asetpts=PTS-STARTPTS[b];[a][b]acrossfade=d=1[c]','-map','[c]','-c:a','pcm_s16le',work/'water.wav')
        inputs=['-stream_loop','-1','-i',work/'water.wav','-stream_loop','-1','-i',work/'birds.mp3']
        filters='[1:a]loudnorm=I=-25:TP=-3:LRA=7[w];[2:a]loudnorm=I=-32:TP=-5:LRA=7[b];[w][b]amix=inputs=2:normalize=0,'+tail+'[a]'
    job.save('synthesis.json',{'minutes':MINUTES,'mode':MODE,'seed':SEED,'motion':'real footage with crossfaded loop','source_id':source_id,'source_page':f'https://www.pexels.com/video/{source_id}/','thumbnail_second':thumbnail_second,'license':'https://www.pexels.com/license/','bird_license':'CC0 https://freesound.org/people/Magnesus/sounds/723913/','thumbnail_text':False})
    job.ff('-stream_loop','-1','-i',work/'scene.mp4',*inputs,'-filter_complex',filters,'-map','0:v','-map','[a]','-t',job.DURATION,'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',work/'rain-75.mp4')
    seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(work/'rain-75.mp4')]))
    if abs(seconds-job.DURATION)>2: raise RuntimeError('Rendered duration mismatch')
    job.ff('-ss','30','-i',work/'rain-75.mp4','-t','20','-c','copy',work/'preview.mp4')
    record_thumbnail(history_path,{'token':job.MARKER.rsplit('-',1)[-1],'mode':MODE,'source_id':source_id,'thumbnail_second':thumbnail_second})
    print('MOTION_RENDERED',MODE,MINUTES,flush=True)

if __name__=='__main__':
    job.render=render
    print('SELECTED',MODE,MINUTES,flush=True)
    job.main()
    receipt=json.loads((job.WORK/'upload.json').read_text())
    video_id=receipt['video_id']
    result=job.ROOT/os.environ.get('ROOM_RESULT_SOURCE','artifacts/youtube_playlist_result.json')
    result.parent.mkdir(parents=True,exist_ok=True)
    privacy_status=upload_privacy_status()
    result.write_text(json.dumps({'artifact_id':video_id,'video_id':video_id,'artifact_url':result_url(video_id),'studio_url':f'https://studio.youtube.com/video/{video_id}/edit','public_url':f'https://youtu.be/{video_id}','privacy_status':privacy_status,'channel_key':'healing','verified_channel_id':receipt['channel_id'],'public_allowed':public_allowed(),'minutes':MINUTES,'variant':MODE}),encoding='utf-8')
