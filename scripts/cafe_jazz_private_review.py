"""Licensed instrumental cafe selection; original artist credits retained."""
import json
import classical_private_review as renderer
job=renderer.job
job.CHANNEL='starbucks'
job.EXPECTED_CHANNEL='UC_e-sbLkVgwJNYEeobolNog'
job.MARKER='Review reference: cafe-jazz-20260908'
job.TITLE='Seaside Coffee & Easy Jazz | A Gentle Instrumental Playlist for Your Workday'
renderer.IMAGE_ASSET='cafe-jazz.png'
renderer.manifest=json.loads((job.ROOT/'assets/playlist-review/cafe-jazz-tracks.json').read_text())
job.DURATION=sum(t['seconds'] for t in renderer.manifest)
job.DESCRIPTION='''Settle beside an open cafe window with an easy instrumental mix of jazz, bossa rhythms, warm bass, and relaxed melodies. This selection accompanies reading, writing, or a quiet coffee break, with no spoken narration. Choose a comfortable volume and let the music sit gently behind your day.

This is a curated selection of existing licensed recordings, not newly composed Lyria music. Each piece appears once and finishes naturally. The seaside cafe illustration and audio-reactive waveform provide a simple setting without extra captions.

Music: Kevin MacLeod (incompetech.com). Licensed under Creative Commons Attribution 3.0: https://creativecommons.org/licenses/by/3.0/
Tracks: '''+', '.join(t['name'] for t in renderer.manifest)+'''.

Edits: sequencing, audio format conversion, visual accompaniment. Original compositions and performances belong to their credited creator. This video is private for the channel owner's review.\n\n'''+job.MARKER
if __name__=='__main__':
    job.WORK=job.ROOT/'data/cafe-jazz-private-review';job.WORK.mkdir(parents=True,exist_ok=True)
    job.render=renderer.render
    job.main()
