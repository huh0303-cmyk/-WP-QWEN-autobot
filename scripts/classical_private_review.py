"""Public-domain actual piano performance, private Cafe Mozart review."""
import hashlib,json,subprocess
from urllib.parse import quote
import requests
import healing_rain_review as job
from PIL import Image,ImageOps
job.CHANNEL='mbb'
job.EXPECTED_CHANNEL='UC7jOhyMa-FIrzZuea97z1Pw'
job.MARKER='Review reference: classical-goldberg-20260908'
job.TITLE='Bach by the Sea | Beautiful Piano for Reading & Quiet Mornings | Cafe Mozart'
IMAGE_ASSET='classical-piano.png'
manifest=json.loads((job.ROOT/'assets/playlist-review/classical-tracks.json').read_text())
job.DURATION=round(sum(float(t['seconds']) for t in manifest))
job.DESCRIPTION='''Open the windows to a peaceful morning of solo piano. This Cafe Mozart selection brings together complete movements from J. S. Bach's Goldberg Variations, performed by pianist Kimiko Ishizaka for the Open Goldberg Variations project. The piano's clear lines and changing textures offer a thoughtful companion for reading, quiet work, or simply listening.

These are real piano performances, not newly generated AI music. The 2012 Open Goldberg recording was dedicated to the public domain under CC0. No movement is repeated within this selection, and each track plays through to its natural ending. The original performance dynamics are preserved with gentle level adjustment between files.

An airy piano-room illustration and a subtle audio-reactive waveform accompany the music. Listen at a comfortable volume and enjoy the small details as the variations unfold.

Performance: Kimiko Ishizaka. Composition: J. S. Bach, BWV 988. Source and license: opengoldbergvariations.org and the Internet Archive Open Goldberg collection, CC0. Prepared privately for the channel owner's review.\n\n'''+job.MARKER

def render():
    files=[];seen=set()
    for i,t in enumerate(manifest):
        path=job.WORK/f'track-{i:02d}.mp3'
        response=requests.get(t['url'],timeout=120);response.raise_for_status();path.write_bytes(response.content)
        digest=hashlib.sha256(response.content).hexdigest()
        if digest in seen:raise RuntimeError('Duplicate classical recording')
        seen.add(digest);t['sha256']=digest
        wav=job.WORK/f'track-{i:02d}.wav'
        job.ff('-i',path,'-ar','48000','-ac','2',wav)
        files.append(wav)
    job.save('tracks.json',manifest)
    (job.WORK/'concat.txt').write_text('\n'.join("file '"+str(p)+"'" for p in files))
    audio=job.WORK/'audio.m4a'
    job.ff('-f','concat','-safe','0','-i',job.WORK/'concat.txt','-c:a','aac','-b:a','192k',audio)
    image=ImageOps.fit(Image.open(job.ROOT/'assets/playlist-review'/IMAGE_ASSET).convert('RGB'),(1280,720))
    image.save(job.WORK/'thumbnail.jpg',quality=93)
    video=job.WORK/'rain-75.mp4'
    job.ff('-loop','1','-framerate','10','-i',job.WORK/'thumbnail.jpg','-i',audio,'-filter_complex','[1:a]showwaves=s=1152x44:mode=cline:rate=10:colors=white:scale=sqrt[w];[0:v][w]overlay=64:652:shortest=1[v]','-map','[v]','-map','1:a','-c:v','libx264','-preset','ultrafast','-crf','24','-threads','2','-pix_fmt','yuv420p','-c:a','copy','-shortest','-movflags','+faststart',video)
    job.ff('-ss','30','-i',video,'-t','20','-c','copy',job.WORK/'preview.mp4')
    print('CLASSICAL_RENDERED',job.DURATION,flush=True)

if __name__=='__main__':
    job.WORK=job.ROOT/'data/classical-private-review';job.WORK.mkdir(parents=True,exist_ok=True)
    job.render=render
    job.main()
