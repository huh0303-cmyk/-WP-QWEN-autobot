"""Site-level evidence, shared by bulk and individual launch tiles."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
import xml.etree.ElementTree as ET
import requests

KST = timezone(timedelta(hours=9))


def summarize(events):
    unique = {}
    for event in events:
        key = (str(event.get('run_id') or event.get('at')), event.get('site_id'))
        prior = unique.get(key)
        if prior is None or event.get('status') == 'published' or (prior.get('status') != 'published' and (event.get('at') or '') >= (prior.get('at') or '')):
            unique[key] = event
    ordered = sorted(unique.values(), key=lambda e: e.get('at') or '', reverse=True)
    return {
        'latest': ordered[0] if ordered else None,
        'success': next((e for e in ordered if e.get('status') == 'published'), None),
        'failure': next((e for e in ordered if e.get('status') == 'failed'), None),
        'events': ordered[:5],
    }


def local_events(state, site_id):
    result = []
    for item in state.get('items', []):
        if item.get('site_id') != site_id:
            continue
        done = item.get('status') == 'done'
        result.append({
            'site_id': site_id, 'run_id': item.get('run_id'),
            'at': item.get('finished_at') or state.get('finished_at') or item.get('dispatched_at') or state.get('started_at') or '',
            # A green workflow is not proof of a public post (draft/video jobs).
            'status': ('workflow_success' if item.get('conclusion') == 'success' else 'failed') if done else 'running',
            'run_url': item.get('run_url', ''), 'reason': item.get('reason', ''),
        })
    return result


@lru_cache(maxsize=256)
def new_content(url, platform, bucket):
    """Count public posts today versus yesterday in KST; never infer zero on error."""
    today = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    try:
        if platform == 'wordpress':
            r = requests.get(url.rstrip('/') + '/wp-json/wp/v2/posts', params={
                'per_page': 20, '_fields': 'id,date_gmt', 'status': 'publish',
            }, timeout=8)
            r.raise_for_status()
            rows = r.json()
            dates = [datetime.fromisoformat(row['date_gmt'].rstrip('Z') + '+00:00').astimezone(KST) for row in rows]
            if len(rows) == 20 and min(dates) >= yesterday:
                return {'new_posts': None, 'new_posts_delta': None}
            counts = [sum(today <= d < today + timedelta(days=1) for d in dates), sum(yesterday <= d < today for d in dates)]
        else:
            endpoint = '/feeds/posts/default?alt=rss&max-results=150' if platform == 'blogger' else '/rss'
            r = requests.get(url.rstrip('/') + endpoint, timeout=8)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            if root.find('channel') is None:
                raise ValueError('Not an RSS feed')
            dates = [parsedate_to_datetime(item.findtext('pubDate')).astimezone(KST) for item in root.findall('./channel/item')]
            # Truncated feeds cannot establish a complete two-day count.
            if dates and min(dates) >= yesterday:
                return {'new_posts': None, 'new_posts_delta': None}
            counts = [sum(today <= d < today + timedelta(days=1) for d in dates), sum(yesterday <= d < today for d in dates)]
        return {'new_posts': counts[0], 'new_posts_delta': counts[0] - counts[1]}
    except (requests.RequestException, ValueError, TypeError, KeyError, ET.ParseError):
        return {'new_posts': None, 'new_posts_delta': None}
