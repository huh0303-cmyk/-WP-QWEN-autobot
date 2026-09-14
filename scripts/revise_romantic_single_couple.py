"""Manual bright one-couple correction. Never make the review public."""
import hashlib,json,os,shutil
import render_romantic_review as job
MARKER='Review revision: single-couple-sea-20260908'
job.WORK=job.ROOT/'data/romantic-review-single-couple-20260908'
job.WORK.mkdir(parents=True,exist_ok=True)
os.chdir(job.WORK)
source=job.ROOT/'assets/playlist-review/single-couple.png'
shutil.copyfile(source,job.WORK/'review-background.png')
image=job.maker.base._resize_cover(job.Image.open(source).convert('RGB'),1280,720)
image.save(job.WORK/'thumbnail.jpg',quality=93)
service=job.publisher.get_youtube_service()
job.verify_authenticated_channel(service,'globalmusic')
old_id='htai4c5jPH4'
old=service.videos().list(part='status,snippet',id=old_id).execute()['items'][0]
if old['status']['privacyStatus']!='private' or old['snippet']['channelId']!='UCbJfEtsffpgI5MsKkB7BYvQ':
    raise RuntimeError('Original review identity or privacy changed')
service.thumbnails().set(videoId=old_id,media_body=job.MediaFileUpload(str(job.WORK/'thumbnail.jpg'))).execute()
job.save('original-thumbnail-updated.json',{'video_id':old_id,'single_couple':True,'privacy':'private'})
print('ORIGINAL_THUMBNAIL_UPDATED',old_id,flush=True)
uploads=service.channels().list(part='contentDetails',mine=True).execute()['items'][0]['contentDetails']['relatedPlaylists']['uploads']
items=service.playlistItems().list(part='contentDetails',playlistId=uploads,maxResults=50).execute().get('items',[])
ids=','.join(item['contentDetails']['videoId'] for item in items)
existing=service.videos().list(part='snippet,status',id=ids).execute().get('items',[]) if ids else []
match=next((v for v in existing if MARKER in v['snippet'].get('description','')),None)
tracks=json.loads((job.ROOT/'assets/playlist-review/verified-tracks.json').read_text())
seconds=sum(t['seconds'] for t in tracks)
if match:
    if match['status']['privacyStatus']!='private':raise RuntimeError('Existing correction is no longer private')
    job.save('upload.json',{'video_id':match['id']})
    job.upload(job.WORK/'final-waveform.mp4',seconds)
else:
    drive=job.maker.base.get_drive_service()
    for track in tracks:
        path=job.WORK/(track['id']+'.mp3')
        if not path.exists():job.maker._bank_download(drive,track['id'],str(path))
        if hashlib.sha256(path.read_bytes()).hexdigest()!=track['sha256']:raise RuntimeError('Audio checksum changed')
        track['path']=str(path)
    job.save('tracks.json',tracks)
    original_ff=job.ff
    def render_ff(args):
        args=list(args)
        if '-preset' in args:
            args[args.index('-preset')+1]='ultrafast'
            args=args[:-1]+['-progress',str(job.WORK/'render-progress.txt')]+args[-1:]
        return original_ff(args)
    job.ff=render_ff
    original_metadata=job.playlist_metadata
    def metadata(channel,topic,minutes):
        title,description,tags,fallback=original_metadata(channel,'Sweet Cafe for Two by the Sea',minutes)
        return title,description+'\n\n'+MARKER,tags,fallback
    job.playlist_metadata=metadata
    video,seconds=job.render(tracks)
    job.upload(video,seconds)
