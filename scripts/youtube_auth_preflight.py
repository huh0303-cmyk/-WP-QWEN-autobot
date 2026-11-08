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
        try:
            error = response.json().get('error', str(response.status_code))
        except ValueError:
            error = str(response.status_code)
        guidance = {
            'unauthorized_client': 'OAuth client is not authorized for this refresh grant. Verify CLIENT_ID and CLIENT_SECRET belong to the same OAuth client that issued REFRESH_TOKEN; check Google Cloud OAuth client type/status and re-authorize that exact YouTube channel if necessary.',
            'invalid_grant': 'Refresh token expired, revoked, or issued for another client. Re-authorize the expected YouTube channel and replace REFRESH_TOKEN.',
            'invalid_client': 'OAuth client ID or secret rejected. Verify the matching Google Cloud OAuth client credentials.',
        }.get(error, 'Inspect Google OAuth client configuration and granted YouTube scopes.')
        raise RuntimeError(f'{profile}: OAUTH_PREFLIGHT_FAILED [{error}]. {guidance} Publishing blocked before generation.')
    data = response.json()
    scopes = set(data.get('scope', '').split())
    allowed = {'https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl'}
    if scopes and not scopes.intersection(allowed):
        raise RuntimeError(f'{profile}: token lacks upload permission')
    response = requests.get('https://www.googleapis.com/youtube/v3/channels',
        params={'part': 'id', 'mine': 'true'}, headers={'Authorization': 'Bearer ' + data['access_token']}, timeout=30)
    if not response.ok:
        raise RuntimeError(f'{profile}: channel verification rejected HTTP {response.status_code}')
    expected = os.environ.get('EXPECTED_CHANNEL_ID', '').strip()
    if not expected:
        expected = next(c['channel_id'] for c in json.load(open('config/youtube_channels.json', encoding='utf-8'))['channels'] if c['secret_profile'] == profile)
    if expected not in {c['id'] for c in response.json().get('items', [])}:
        raise RuntimeError(f'{profile}: authenticated channel does not match registry')
    print(f'{profile}: channel identity and token verified (read-only; no upload performed)')


if __name__ == '__main__':
    main()
