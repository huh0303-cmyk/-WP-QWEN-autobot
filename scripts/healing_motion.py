"""Real moving nature footage, private review presets, randomized runtime."""
import hashlib, json, os, random, re, subprocess
import requests
import healing_rain_review as job

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

Footage: Pexels, used under the Pexels License. Bird ambience, when present: Magnesus, Freesound 723913, CC0. This sample is uploaded privately for the channel owner's review.\n\n'''+job.MARKER
    return mode,seed,minutes

MODE,SEED,MINUTES=configure()
def render():
    work=job.WORK
    source_id=13166787 if MODE=='rain' else 5021254
    source=work/'source.mp4'
    download(f'https://www.pexels.com/download/video/{source_id}/',source)
    job.ff('-ss','3','-i',source,'-frames:v','1','-vf','scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080',work/'thumbnail.jpg')
    # Last second dissolves into first second; next loop begins where the dissolve ends.
    transition='[0:v]fps=24,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,split[a][b];[a]trim=start=1:end=10,setpts=PTS-STARTPTS[x];[b]trim=start=0:end=1,setpts=PTS-STARTPTS[y];[x][y]xfade=transition=fade:duration=1:offset=8[v]'
    job.ff('-i',source,'-filter_complex_threads','1','-filter_complex',transition,'-map','[v]','-an','-c:v','libx264','-preset','fast','-b:v','2200k','-maxrate','2600k','-bufsize','5200k','-pix_fmt','yuv420p',work/'scene.mp4')
    tail=f'afade=t=in:d=4,afade=t=out:st={job.DURATION-6}:d=6'
    if MODE=='rain':
        inputs=['-f','lavfi','-i',f'anoisesrc=color=pink:sample_rate=48000:amplitude=0.65:seed={SEED%2147483646+1}','-f','lavfi','-i',f'anoisesrc=color=pink:sample_rate=48000:amplitude=0.65:seed={(SEED+73)%2147483646+1}']
        filters='[1:a]highpass=f=250,lowpass=f=7500,volume=0.7*(0.92+0.08*sin(t/29)):eval=frame[l];[2:a]highpass=f=180,lowpass=f=6800,volume=0.7*(0.92+0.08*sin(t/37)):eval=frame[r];[l][r]join=inputs=2:channel_layout=stereo,'+tail+'[a]'
    else:
        import shutil
        shutil.copyfile(job.ROOT/'assets/playlist-review/forest-birds-cc0.mp3',work/'birds.mp3')
        # Crossfade the field audio once into a seamless loop, then mix gentle birds.
        job.ff('-i',source,'-filter_complex','[0:a]asplit[x][y];[x]atrim=start=1:end=18,asetpts=PTS-STARTPTS[a];[y]atrim=start=0:end=1,asetpts=PTS-STARTPTS[b];[a][b]acrossfade=d=1[c]','-map','[c]','-c:a','pcm_s16le',work/'water.wav')
        inputs=['-stream_loop','-1','-i',work/'water.wav','-stream_loop','-1','-i',work/'birds.mp3']
        filters='[1:a]loudnorm=I=-25:TP=-3:LRA=7[w];[2:a]loudnorm=I=-32:TP=-5:LRA=7[b];[w][b]amix=inputs=2:normalize=0,'+tail+'[a]'
    job.save('synthesis.json',{'minutes':MINUTES,'mode':MODE,'seed':SEED,'motion':'real footage with crossfaded loop','source_id':source_id,'license':'https://www.pexels.com/license/','bird_license':'CC0 https://freesound.org/people/Magnesus/sounds/723913/','thumbnail_text':False})
    job.ff('-stream_loop','-1','-i',work/'scene.mp4',*inputs,'-filter_complex',filters,'-map','0:v','-map','[a]','-t',job.DURATION,'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',work/'rain-75.mp4')
    seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(work/'rain-75.mp4')]))
    if abs(seconds-job.DURATION)>2: raise RuntimeError('Rendered duration mismatch')
    job.ff('-ss','30','-i',work/'rain-75.mp4','-t','20','-c','copy',work/'preview.mp4')
    print('MOTION_RENDERED',MODE,MINUTES,flush=True)

if __name__=='__main__':
    job.render=render
    print('SELECTED',MODE,MINUTES,flush=True)
    job.main()
    receipt=json.loads((job.WORK/'upload.json').read_text())
    video_id=receipt['video_id']
    result=job.ROOT/os.environ.get('ROOM_RESULT_SOURCE','artifacts/youtube_playlist_result.json')
    result.parent.mkdir(parents=True,exist_ok=True)
    result.write_text(json.dumps({'artifact_id':video_id,'video_id':video_id,'artifact_url':f'https://studio.youtube.com/video/{video_id}/edit','privacy_status':'private','channel_key':'healing','verified_channel_id':receipt['channel_id'],'public_allowed':False,'minutes':MINUTES,'variant':MODE}),encoding='utf-8')
