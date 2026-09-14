"""Read-only check of granted credentials and expected channel identity."""
import json
import os
import requests


def main():
    profile = os.environ['PROFILE']
    fields = {k: os.environ.get(k, '') for k in ('CLIENT_ID', 'CLIENT_SECRET', 'REFRESH_TOKEN')}
    if not all(fields.values()):
        raise RuntimeError(f'{profile}: missing credential configuration')
    response = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': fields['CLIENT_ID'], 'client_secret': fields['CLIENT_SECRET'],
        'refresh_token': fields['REFRESH_TOKEN'], 'grant_type': 'refresh_token'}, timeout=30)
    if not response.ok:
        raise RuntimeError(f"{profile}: refresh rejected: {response.json().get('error', response.status_code)}")
    data = response.json()
    scopes = set(data.get('scope', '').split())
    allowed = {'https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl'}
    if scopes and not scopes.intersection(allowed):
        raise RuntimeError(f'{profile}: token lacks upload permission')
    response = requests.get('https://www.googleapis.com/youtube/v3/channels',
        params={'part': 'id', 'mine': 'true'}, headers={'Authorization': 'Bearer ' + data['access_token']}, timeout=30)
    if not response.ok:
        raise RuntimeError(f'{profile}: channel verification rejected HTTP {response.status_code}')
    expected = next(c['channel_id'] for c in json.load(open('config/youtube_channels.json', encoding='utf-8'))['channels'] if c['secret_profile'] == profile)
    if expected not in {c['id'] for c in response.json().get('items', [])}:
        raise RuntimeError(f'{profile}: authenticated channel does not match registry')
    print(f'{profile}: channel identity and token verified (read-only; no upload performed)')


if __name__ == '__main__':
    main()
