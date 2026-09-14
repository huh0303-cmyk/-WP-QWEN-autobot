"""Load the private server runtime then enter the queue worker."""
import json, os, runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
values=json.loads(Path('/etc/korea365/youtube-runtime.json').read_text())
os.environ.update({key:str(value) for key,value in values.items() if value})
os.environ.setdefault('PLAYLIST_MUSIC_SOURCE','approved_bank')
os.environ.setdefault('PLAYLIST_IMAGE_SOURCE','gemini_app_export')
os.environ.setdefault('PLAYLIST_PAID_API_ENABLED','false')
runpy.run_path(str(root/'scripts/youtube_vps_worker.py'),run_name='__main__')
