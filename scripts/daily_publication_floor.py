"""Reconcile each site's public daily minimum before claiming a bounded worker.

Public pages, not dispatch responses, satisfy the daily target. Claims are
durable GitHub content records written before dispatch; uncertain outcomes are
never blindly replayed. One site's error cannot stop the rest of the network.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import io
import json
import os
import socket
from pathlib import Path
import sys
import uuid
import zipfile

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publication_health_audit import check
from automation_hub.public_verifier import verify_publication

KST = timezone(timedelta(hours=9))

def force_ipv4_dns():
    """Avoid GitHub runner AAAA routes that cannot reach the WordPress fleet."""
    original = socket.getaddrinfo
    def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        rows = original(host, port, socket.AF_INET, type, proto, flags)
        if not rows:
            raise OSError(f"no IPv4 address for {host}")
        return rows
    socket.getaddrinfo = ipv4_only


def sites_for(platform):
    sites = json.loads((ROOT/'config/automation_hub_sites.json').read_text(encoding='utf-8'))['sites']
    if platform == 'newsroom':
        return [dict(s, platform='newsroom') for s in sites if s['platform']=='wordpress' and s.get('content_type') in {'news_ko','news_en'}]
    return [s for s in sites if s['platform'] == platform and s.get('enabled', True)
            and (platform != 'wordpress' or s.get('content_type') == 'blog')]


def public_status(site, now):
    # WordPress fleet: use the same protected application-password channel as
    # publishing. Public anonymous REST is frequently blocked by ModSecurity/
    # bot rules and must not be interpreted as "no post today".
    if site.get('platform') == 'wordpress':
        secret = os.getenv(site.get('secret_name', ''), '').strip()
        if not secret:
            return {'status': 'READ_ERROR', 'reason': 'credential_missing'}
        user = os.getenv('WP_USER', 'huh0303@gmail.com')
        try:
            response = requests.get(
                site['url'].rstrip('/') + '/wp-json/wp/v2/posts',
                auth=(user, secret),
                headers={'User-Agent': 'Korea365-Control/1.0'},
                params={'status': 'publish', 'per_page': 1, 'orderby': 'date',
                        'order': 'desc', '_fields': 'link,date_gmt,title'},
                timeout=15,
            )
            response.raise_for_status()
            posts = response.json()
            if not isinstance(posts, list):
                raise ValueError('invalid WordPress post inventory')
            result = {
                'status': 'public_post_found' if posts else 'no_public_post_in_response',
                'latest_url': posts[0].get('link','') if posts else '',
                'latest_published': (posts[0].get('date_gmt','') + 'Z') if posts and posts[0].get('date_gmt') else None,
                'latest_title': ((posts[0].get('title') or {}).get('rendered','')) if posts else '',
            }
        except (requests.RequestException, ValueError, TypeError):
            return {'status': 'READ_ERROR', 'reason': 'authenticated_wp_inventory_failed'}
    else:
        result = check(site)
        if result['status'] not in {'public_post_found', 'no_public_post_in_response'}:
            return {'status': 'READ_ERROR', 'reason': result['status']}
    raw = result.get('latest_published')
    try:
        published = datetime.fromisoformat(raw.replace('Z', '+00:00')) if raw else None
        today = published and published.astimezone(KST).date() == now.date() and published <= now
    except (ValueError, TypeError):
        return {'status': 'READ_ERROR', 'reason': 'invalid_publication_date'}
    if today:
        if not result.get('latest_title'):
            return {'status': 'READ_ERROR', 'reason': 'missing_public_title'}
        verified = verify_publication(result['latest_url'], result['latest_title'], site_url=site['url'], attempts=1, timeout=12)
        if not verified.ok:
            return {'status': 'READ_ERROR', 'reason': verified.error_code}
        return {'status': 'PUBLISHED', 'url': verified.final_url, 'published_at': raw}
    return {'status': 'DUE'}


class GitHub:
    def __init__(self, repo, token):
        self.base = 'https://api.github.com/repos/' + repo
        self.session = requests.Session()
        self.session.headers.update({'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json',
                                     'X-GitHub-Api-Version': '2026-03-10'})

    def request(self, method, path, **kwargs):
        return self.session.request(method, self.base+'/'+path, timeout=25, **kwargs)

    def load(self, site_id):
        r = self.request('GET', 'contents/data/daily-publication/'+site_id+'.json')
        if r.status_code == 404:
            return {}, None
        r.raise_for_status()
        item = r.json()
        return json.loads(base64.b64decode(item['content'])), item['sha']

    def save(self, site_id, state, sha):
        body = {'message': 'Daily publication receipt '+site_id+' [skip ci]', 'branch': 'main',
                'content': base64.b64encode(json.dumps(state, ensure_ascii=False).encode()).decode()}
        if sha:
            body['sha'] = sha
        r = self.request('PUT', 'contents/data/daily-publication/'+site_id+'.json', json=body)
        r.raise_for_status()  # conflicting claims cannot dispatch
        return r.json()['content']['sha']

    def run(self, run_id):
        r = self.request('GET', 'actions/runs/'+str(int(run_id)))
        r.raise_for_status()
        return r.json()

    def handoff(self, run_id, site_id):
        r = self.request('GET', f'actions/runs/{int(run_id)}/artifacts')
        r.raise_for_status()
        artifact = next((a for a in r.json()['artifacts'] if a['name'] == f'control-handoff-{run_id}' and not a['expired']), None)
        if not artifact:
            return None
        r = self.request('GET', f'actions/artifacts/{artifact["id"]}/zip')
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
            item = next((x for x in archive.infolist() if x.filename.endswith('control-handoff.json') and x.file_size < 100_000), None)
            if not item:
                return None
            data = json.loads(archive.read(item))
        if str(data.get('parent_run_id')) != str(run_id) or data.get('site_id') != site_id:
            raise ValueError('Mismatched publication handoff')
        return data

    def dispatch(self, workflow, inputs):
        r = self.request('POST', 'actions/workflows/'+workflow+'/dispatches',
                         json={'ref': 'main', 'return_run_details': True, 'inputs': inputs})
        r.raise_for_status()
        data = r.json()
        if not isinstance(data.get('workflow_run_id'), int):
            raise ValueError('Dispatch accepted without exact run receipt')
        return data['workflow_run_id']


def worker(site, attempt, claim_id, state):
    if site['platform'] == 'newsroom':
        return 'newsrooms-daily-publisher.yml', {'newsroom': 'koreanews365' if site['url'].rstrip('/')=='https://koreanews365.com' else 'theseouljournal'}
    if site['platform'] == 'wordpress':
        return 'daily-network-publish.yml', {'target_site_url': site['url'], 'room_id': claim_id,
                                            'publication_approved': 'true', 'force_keyword': ''}
    if state.get('child_job_id'):
        return 'platform-publish-v2.yml', {'platform': 'blogger', 'job_id': state['child_job_id'], 'max_jobs': '1'}
    return 'blogger-rewrite.yml', {'blogger_site_id': site['site_id'], 'language': site.get('language', 'en'),
        'persona': site.get('persona', 'helpful specialist editor'), 'tone': site.get('tone', 'practical and clear'),
        'target_chars': str(site.get('target_chars', 1800)), 'publish_now': 'true',
        'recover_from_wp': 'true', 'fetch_jitter_max_seconds': '30'}


def reconcile(site, public, api, now, allow_dispatch, max_attempts=2):
    sid = site['site_id']
    row = {'site_id': sid, 'url': site['url'], **public}
    if public['status'] == 'READ_ERROR':
        return row, False
    state, sha = api.load(sid)
    day = now.date().isoformat()

    # A previous calendar day's orphaned claim must never block today's
    # required publication. If it has a real run that is still active, keep
    # waiting for that run; otherwise start today's state cleanly.
    if state.get('day') and state.get('day') != day:
        old_run_id = state.get('child_run_id') or state.get('run_id')
        if old_run_id:
            try:
                old_run = api.run(old_run_id)
            except (requests.RequestException, ValueError, KeyError):
                old_run = {'status': 'completed'}
            if old_run.get('status') != 'completed':
                return {**row, 'status': 'RUNNING_PREVIOUS_DAY', 'run_id': old_run_id}, False
        state = {}

    # A same-day CLAIMED record without a run id can be left behind when a
    # dispatch is rejected before GitHub assigns a run. After a short grace
    # period, allow the bounded retry instead of blocking the site all day.
    if state.get('status') in {'CLAIMED', 'DISPATCH_UNCERTAIN'} and not (state.get('child_run_id') or state.get('run_id')):
        try:
            claimed = datetime.fromisoformat(str(state.get('claimed_at') or '').replace('Z', '+00:00'))
            if claimed.tzinfo is None:
                claimed = claimed.replace(tzinfo=KST)
            if now - claimed.astimezone(KST) >= timedelta(minutes=5):
                state['status'] = 'FAILED'
        except (ValueError, TypeError):
            state['status'] = 'FAILED'

    if public['status'] == 'PUBLISHED':
        updated = {'day': day, 'status': 'PUBLISHED', 'public_url': public['url'], 'published_at': public['published_at']}
        if state != updated:
            api.save(sid, updated, sha)
        return row, False
    if state.get('status') in {'CLAIMED', 'DISPATCHED', 'AWAITING_PUBLIC', 'DISPATCH_UNCERTAIN'}:
        run_id = state.get('child_run_id') or state.get('run_id')
        if not run_id:
            return {**row, 'status': 'DISPATCH_UNCERTAIN'}, False
        run = api.run(run_id)
        if run['status'] != 'completed':
            return {**row, 'status': 'RUNNING', 'run_id': run_id}, False
        if run.get('conclusion') == 'success' and site['platform'] == 'blogger' and not state.get('child_run_id') and not state.get('child_job_id'):
            receipt = api.handoff(run_id, sid)
            if not receipt:
                return {**row, 'status': 'HANDOFF_UNCONFIRMED', 'run_id': run_id}, False
            state.update(child_run_id=receipt['workflow_run_id'], child_job_id=receipt['job_id'])
            sha = api.save(sid, state, sha)
            run_id = state['child_run_id']
            run = api.run(run_id)
            if run['status'] != 'completed':
                return {**row, 'status': 'RUNNING', 'run_id': run_id}, False
        if run.get('conclusion') == 'success':
            # Success may mean a draft or delayed verification. Do not create another article.
            completed = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00')).astimezone(KST)
            if completed.date() == now.date():
                return {**row, 'status': 'AWAITING_PUBLIC', 'run_id': run_id}, False
            state = {'day': day, 'attempts': 0, 'status': 'NEW_DAY'}
        elif run.get('conclusion') not in {'failure', 'cancelled', 'timed_out', 'startup_failure'}:
            return {**row, 'status': 'RUN_UNCONFIRMED', 'run_id': run_id}, False
        state['status'] = 'FAILED'
    attempts = int(state.get('attempts', 0)) if state.get('day') == day else 0
    if attempts >= max_attempts:
        return {**row, 'status': 'REPAIR_REQUIRED', 'attempts': attempts}, False
    if not allow_dispatch:
        return row, False
    if site['platform'] in {'wordpress','newsroom'} and not os.getenv(site.get('secret_name', ''), '').strip():
        return {**row, 'status': 'CREDENTIAL_REQUIRED'}, False
    claim = 'daily-'+day+'-'+sid+'-'+uuid.uuid4().hex[:8]
    workflow, inputs = worker(site, attempts+1, claim, state)
    state = {'day': day, 'status': 'CLAIMED', 'attempts': attempts+1, 'claim': claim,
             'claimed_at': now.isoformat(), 'run_id': None, 'child_run_id': None,
             'child_job_id': state.get('child_job_id'), 'workflow': workflow}
    sha = api.save(sid, state, sha)
    try:
        run_id = api.dispatch(workflow, inputs)
    except (requests.RequestException, ValueError):
        # Keep the pre-dispatch claim; an accepted request may have lost its response.
        return {**row, 'status': 'DISPATCH_UNCERTAIN', 'claim': claim}, True
    state.update(status='DISPATCHED', run_id=run_id)
    try:
        api.save(sid, state, sha)
    except requests.RequestException:
        return {**row, 'status': 'DISPATCH_UNCERTAIN', 'run_id': run_id, 'claim': claim}, True
    return {**row, 'status': 'DISPATCHED', 'run_id': run_id, 'attempts': attempts+1}, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['wordpress', 'blogger', 'newsroom'], required=True)
    parser.add_argument('--max-dispatch', type=int, default=4)
    args = parser.parse_args()
    force_ipv4_dns()
    now = datetime.now(KST)
    sites = sites_for(args.platform)
    api = GitHub(os.environ['GITHUB_REPOSITORY'], os.environ['GH_DISPATCH_TOKEN'])
    with ThreadPoolExecutor(max_workers=8) as pool:
        public = list(pool.map(lambda site: public_status(site, now), sites))
    # Rotate the starting point by hour, so retries cannot starve later sites.
    offset = (now.hour*4) % len(sites) if sites else 0
    pairs = list(zip(sites, public))
    pairs = pairs[offset:] + pairs[:offset]
    rows, dispatched = [], 0
    for site, result in pairs:
        try:
            row, used = reconcile(site, result, api, now, dispatched < args.max_dispatch)
            dispatched += int(used)
        except (requests.RequestException, ValueError, KeyError) as exc:
            row = {'site_id': site['site_id'], 'url': site['url'], 'status': 'RECONCILIATION_ERROR', 'error_type': type(exc).__name__}
        rows.append(row)
    report = {'day_kst': now.date().isoformat(), 'platform': args.platform, 'target': len(sites),
              'public_verified': sum(r['status']=='PUBLISHED' for r in rows), 'dispatched': dispatched, 'sites': rows}
    Path('artifacts').mkdir(exist_ok=True)
    Path(f'artifacts/daily-publication-floor-{args.platform}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
