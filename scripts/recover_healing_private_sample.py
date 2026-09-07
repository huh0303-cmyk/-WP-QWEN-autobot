"""Recover the already-rendered CAL-0765 sample after its pre-upload OAuth failure."""
import json
import os
from pathlib import Path
import youtube_publish_approved as publisher
from automation_hub.youtube_calendar import read_calendar, update_row
from gsheets_direct import get_sheets_service
from automation_hub.youtube_identity import verify_authenticated_channel


def main():
    service = get_sheets_service()
    sid = os.environ['SHEET_ID']
    row = next(r for r in read_calendar(service, sid) if r['id'] == 'CAL-0765')
    if row['key'] != 'healing' or '[yt-worker:34133935906]' not in row['notes']:
        raise RuntimeError('Original sample identity mismatch')
    if row['url']:
        print('Already has a receipt: ' + row['url'])
        return
    marker = '[healing-recovery-upload-start]'
    if marker in row['notes']:
        raise RuntimeError('Recovery already attempted: reconcile before another upload')
    yt = publisher.get_youtube_service()
    verify_authenticated_channel(yt, 'healing')
    channel = yt.channels().list(part='contentDetails', mine=True).execute()['items'][0]
    uploads = channel['contentDetails']['relatedPlaylists']['uploads']
    recent = yt.playlistItems().list(part='snippet', playlistId=uploads, maxResults=50).execute()
    if any(v['snippet']['title'] == os.environ['YT_TITLE'] for v in recent.get('items', [])):
        raise RuntimeError('Same sample title already exists; reconcile instead of duplicating')
    update_row(service, sid, row, '자료수집', '', row['notes'] + '\n' + marker)
    publisher.main()
    result = json.loads(Path('artifacts/youtube_playlist_result.json').read_text())
    verified = yt.videos().list(part='status,snippet', id=result['video_id']).execute()['items'][0]
    if verified['status']['privacyStatus'] != 'private' or verified['snippet']['channelId'] != 'UC7yEsLM-HoXudngrD-4FIqg':
        raise RuntimeError('Private uploaded video verification failed')
    row = next(r for r in read_calendar(service, sid) if r['id'] == 'CAL-0765')
    update_row(service, sid, row, '비공개 업로드', result['studio_url'], row['notes'] + '\nRecovered existing 64-minute render; private/channel ID verified.')
    print(result['studio_url'])


if __name__ == '__main__':
    main()
