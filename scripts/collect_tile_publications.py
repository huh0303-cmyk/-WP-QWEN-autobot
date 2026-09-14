"""Persist per-site run receipts independently of the web server's lifetime."""
import argparse
import base64
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO = 'huh0303-cmyk/-WP-QWEN-autobot'
DEST = 'data/site-publication-history.json'


def gh(*args):
    return subprocess.check_output(['gh', *args], encoding='utf-8', errors='replace')


def extract(run, log, sites):
    targets = set(re.findall(r'🌐\s+(https?://[^\s]+)', log))
    ids = set(re.findall(r'\b(?:SITE_ID|site_id):\s*([\w-]+)', log))
    public = re.findall(r'(?:공개 발행:|OK published[^\n]*? ->)\s*(https?://[^\s|]+)', log)
    events = []
    for site in sites:
        url = site.get('url', '').rstrip('/')
        if not url or (url not in {u.rstrip('/') for u in targets} and site['site_id'] not in ids):
            continue
        published = next((u for u in reversed(public) if u.startswith(url + '/')), '')
        failed = run.get('conclusion') != 'success'
        events.append({
            'site_id': site['site_id'], 'run_id': run['id'],
            'at': run.get('updated_at') or run['created_at'],
            'status': 'published' if published else 'failed' if failed else 'workflow_success',
            'public_url': published, 'run_url': run['html_url'],
            'reason': 'REST API 403 · 서버 접근 차단' if failed and '403' in log else ('실행 실패 · 상세 로그 확인' if failed else ''),
        })
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id')
    parser.add_argument('--backfill', action='store_true')
    args = parser.parse_args()
    sites = json.loads(Path('config/automation_hub_sites.json').read_text(encoding='utf-8'))['sites']
    if args.backfill:
        runs = json.loads(gh('api', f'repos/{REPO}/actions/workflows/daily-network-publish.yml/runs?per_page=100'))['workflow_runs']
    else:
        runs = [json.loads(gh('api', f'repos/{REPO}/actions/runs/{args.run_id}'))]
    additions = []
    for run in runs:
        if run['status'] != 'completed':
            continue
        log = gh('run', 'view', str(run['id']), '--repo', REPO, '--log')
        additions.extend(extract(run, log, sites))
    if not additions:
        print('No attributable site receipts; no success inferred.')
        return
    for attempt in range(5):
        try:
            remote = json.loads(gh('api', f'repos/{REPO}/contents/{DEST}'))
            old = json.loads(base64.b64decode(remote['content']))
            sha = remote['sha']
        except subprocess.CalledProcessError:
            old, sha = {'events': []}, None
        merged = {(str(e['run_id']), e['site_id']): e for e in old.get('events', [])}
        merged.update({(str(e['run_id']), e['site_id']): e for e in additions})
        events = sorted(merged.values(), key=lambda e: e['at'], reverse=True)[:3000]
        payload = {'updated_at': datetime.now(timezone.utc).isoformat(), 'events': events}
        body = {'message': 'Record site publication outcomes [skip ci]', 'content': base64.b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode(), 'branch': 'main'}
        if sha:
            body['sha'] = sha
        request = Path('.tile-receipts-request.json')
        request.write_text(json.dumps(body), encoding='utf-8')
        try:
            gh('api', f'repos/{REPO}/contents/{DEST}', '--method', 'PUT', '--input', str(request))
            print(f'Saved {len(additions)} site receipts.')
            return
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise


if __name__ == '__main__':
    main()
