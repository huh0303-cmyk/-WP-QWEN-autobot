"""One durable, resumable private review using existing music; never publish publicly."""
import base64, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
os.environ.update(json.loads(Path('/etc/korea365/youtube-runtime.json').read_text()))
os.environ['CHANNEL_KEY']='globalmusic'
for key in ('CLIENT_ID','CLIENT_SECRET','REFRESH_TOKEN'):
    os.environ['YOUTUBE_OAUTH_'+key]=os.environ['YOUTUBE_OAUTH_'+key+'_GLOBALMUSIC']
import youtube_playlist_maker as maker
import youtube_publish_approved as publisher
from googleapiclient.http import MediaFileUpload
from automation_hub.youtube_identity import verify_authenticated_channel
from youtube_english_metadata import playlist_metadata
from PIL import Image, ImageDraw, ImageFont
import requests
WORK=ROOT/'data/romantic-review-20260908'
WORK.mkdir(parents=True,exist_ok=True)
os.chdir(WORK)
def save(name,data):
    p=WORK/name; q=p.with_suffix('.tmp');q.write_text(json.dumps(data,ensure_ascii=False,indent=2));q.replace(p)
def ff(args):
    target=Path(args[-1]); temporary=target.with_name(target.stem+'.partial'+target.suffix)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y']+args[:-1]+[str(temporary)],check=True)
    temporary.replace(target)
def stem(name):
    return re.sub(r'(_dup\d+|_\d+| \(\d+\))','',Path(name).stem).strip()
def language(path):
    cached=path.with_suffix('.analysis.json')
    if cached.exists():return json.loads(cached.read_text())
    clip=path.with_suffix('.clip.mp3')
    ff(['-ss','30','-i',str(path),'-t','35','-ac','1','-ar','16000','-b:a','48k',str(clip)])
    global _whisper
    if '_whisper' not in globals():
        from faster_whisper import WhisperModel
        _whisper=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=2)
    segments,info=_whisper.transcribe(str(clip),beam_size=1)
    words=' '.join(seg.text for seg in segments)
    languages={'fr':'french','ja':'japanese','es':'spanish','it':'italian'}
    result={'language':languages.get(info.language,'other'),'confidence':info.language_probability,'transcript':words,'method':'local_whisper_base','vocal':'unverified'}
    cached.write_text(json.dumps(result,ensure_ascii=False));return result
def prepare():
    service=maker.base.get_drive_service()
    tracks=maker._bank_list(service,maker.base.MUSIC_SOURCE_FOLDER_ID,maker.base.AUDIO_EXTS,'audio/')
    # Title is only a candidate hint. Audible language is checked independently below.
    candidates={
      'french':['Biscuit et Pluie','Mon Jardin Secret','Rue des Citrons','Dans tes bras','Tout doucement','French cafe A','Reste avec moi','Nous ici'],
      'japanese':['しあわせの湯気','ひだまりの合鍵','綿雲みたいな恋','桜色の約束','駅前のミルク','Japanese Romance','花びらの距離','雨あがり'],
      'spanish':['Bajo el sol','Bajo la luna','Boca de Miel','Amor en el Aire','Puerta Azul','Spanish morning coffee','No te vayas','Bajo el puente'],
      'italian':['Amore In Due','Baci di carta','Cartolina di Napoli','Finestra Aperta','Resta Qui','Strada di limoni','Vetro e Mandorle','Vieni più vicino']}
    groups={}; hashes=set()
    for lang,names in candidates.items():
      selected=[]
      for name in names:
        if len(selected)>=5:break
        found=sorted([t for t in tracks if stem(t['name']).casefold()==name.casefold()],key=lambda t:(len(t['name']),t['name']))
        if not found:continue
        track=found[0];path=WORK/(track['id']+'.mp3')
        if not path.exists():maker._bank_download(service,track['id'],str(path))
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in hashes:continue
        review=language(path)
        print('REVIEW',name,review,flush=True)
        if review.get('language')!=lang or float(review.get('confidence',0))<.8:continue
        duration=maker.base.get_duration(str(path))
        if not 100<=duration<=360:continue
        selected.append({'id':track['id'],'name':name,'language':lang,'path':str(path),'seconds':duration,'sha256':digest,'review':review});hashes.add(digest)
      groups[lang]=selected
      save('selection-progress.json',groups)
      if len(selected)<5:raise RuntimeError('Insufficient verified '+lang+' tracks: '+str(len(selected)))
    ordered=[groups[lang][i] for i in range(5) for lang in ('french','japanese','spanish','italian')]
    seconds=sum(t['seconds'] for t in ordered)
    if not 50*60<=seconds<=70*60:raise RuntimeError('Selected music is outside 50–70 minutes: '+str(seconds/60))
    save('tracks.json',ordered)
    print('AUDIO_READY',len(ordered),seconds/60,flush=True)
    return ordered
def render(tracks):
    audio=WORK/'playlist.m4a'
    if not audio.exists():
      normal=[]
      for i,t in enumerate(tracks):
        p=WORK/f'normalized-{i:02d}.wav'
        if not p.exists():ff(['-i',t['path'],'-vn','-af','loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.15','-ar','48000','-ac','2',str(p)])
        normal.append(p)
      (WORK/'audio-list.txt').write_text('\n'.join("file '"+str(p)+"'" for p in normal))
      ff(['-f','concat','-safe','0','-i',str(WORK/'audio-list.txt'),'-c:a','aac','-b:a','192k',str(audio)])
    photo=WORK/'review-background.png'
    if not photo.exists():
      raise RuntimeError('WAITING_ASSETS: original review background is missing; no paid fallback')
    image=maker.base._resize_cover(Image.open(photo).convert('RGB'),1280,720)
    if Image.open(photo).width<1280:raise RuntimeError('Thumbnail source too small')
    draw=ImageDraw.Draw(image)
    font=ImageFont.truetype(maker.base.ensure_font(),76)
    draw.text((640,358),'Sweet Cafe',anchor='mm',font=font,fill='white',stroke_width=2,stroke_fill=(35,24,24))
    image.save(WORK/'thumbnail.jpg',quality=93)
    video=WORK/'final.mp4'
    if not video.exists():
      vf="scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='1+min(on,149)*0.0003':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=25,fade=t=in:st=0:d=1,format=yuv420p"
      ff(['-loop','1','-framerate','25','-i',str(photo),'-t','6','-vf',vf,'-c:v','libx264','-preset','fast','-crf','20','-an',str(WORK/'intro.mp4')])
      ff(['-loop','1','-framerate','25','-i',str(photo),'-t','10','-vf','scale=2006:1129:force_original_aspect_ratio=increase,crop=1920:1080,format=yuv420p','-c:v','libx264','-preset','fast','-tune','stillimage','-crf','20','-an',str(WORK/'still.mp4')])
      seconds=maker.base.get_duration(str(audio))
      clips=[WORK/'intro.mp4']+[WORK/'still.mp4']*int(seconds/10+2)
      (WORK/'video-list.txt').write_text('\n'.join("file '"+str(p)+"'" for p in clips))
      ff(['-f','concat','-safe','0','-i',str(WORK/'video-list.txt'),'-i',str(audio),'-map','0:v','-map','1:a','-c','copy','-t',str(seconds),'-movflags','+faststart',str(video)])
    seconds=maker.base.get_duration(str(video))
    if not 3000<=seconds<=4200:raise RuntimeError('Final duration outside 50–70 minutes')
    return video,seconds
def upload(video,seconds):
    youtube=publisher.get_youtube_service();verify_authenticated_channel(youtube,'globalmusic')
    receipt=WORK/'upload.json'
    if receipt.exists():video_id=json.loads(receipt.read_text())['video_id']
    else:
      if (WORK/'upload-started.json').exists():raise RuntimeError('Upload previously started: reconcile channel before retry to avoid duplicate')
      title,description,tags,_=playlist_metadata('globalmusic','Sweet Cafe at Sunset',seconds/60)
      save('upload-started.json',{'title':title,'time':time.time()})
      # Save video ID before setting thumbnail so a thumbnail retry never uploads another video.
      video_id=publisher.upload_to_youtube(youtube,str(video),None,title,description,tags)
      save('upload.json',{'video_id':video_id,'channel_id':'UCbJfEtsffpgI5MsKkB7BYvQ','privacy_status':'private','duration_seconds':seconds})
    youtube.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(str(WORK/'thumbnail.jpg'))).execute()
    actual=None
    for _ in range(60):
      actual=youtube.videos().list(part='status,snippet,contentDetails,processingDetails',id=video_id).execute()['items'][0]
      processing=actual.get('processingDetails',{}).get('processingStatus')
      if processing in ('failed','terminated'):raise RuntimeError('YouTube processing failed')
      if processing=='succeeded':break
      print('WAITING_YOUTUBE_PROCESSING',processing,flush=True);time.sleep(10)
    if actual.get('processingDetails',{}).get('processingStatus')!='succeeded':raise RuntimeError('YouTube still processing; resume receipt without reupload')
    if actual['status']['privacyStatus']!='private' or actual['snippet']['channelId']!='UCbJfEtsffpgI5MsKkB7BYvQ':raise RuntimeError('Post-upload identity/privacy verification failed')
    save('completed.json',{'video_id':video_id,'url':'https://studio.youtube.com/video/'+video_id+'/edit','privacy':'private','duration':actual['contentDetails']['duration'],'thumbnail_set':True,'actual':actual})
    print('COMPLETED',video_id,actual['contentDetails']['duration'],'private',flush=True)
if __name__=='__main__':
    tracks=json.loads((WORK/'tracks.json').read_text()) if (WORK/'tracks.json').exists() else prepare()
    video,seconds=render(tracks)
    upload(video,seconds)
