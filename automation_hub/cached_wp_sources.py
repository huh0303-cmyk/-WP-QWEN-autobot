"""Short-lived, public WordPress source snapshots for origin read outages."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]

def cached_posts(site_url, *, root=ROOT, now=None):
    host = urlparse(site_url).hostname
    if not host or not all(c.isalnum() or c in '.-' for c in host):
        return []
    try:
        data = json.loads((root/'data/wp-source-snapshots'/f'{host}.json').read_text())
        checked = datetime.fromisoformat(data['fetched_at'])
        age = ((now or datetime.now(timezone.utc)) - checked).total_seconds()
        if not 0 <= age <= 86400 or data['site_url'].rstrip('/') != site_url.rstrip('/'):
            return []
        return [p for p in data['posts'] if p.get('status') == 'publish'
                and urlparse(p.get('link','')).hostname == host
                and p.get('content',{}).get('rendered')]
    except (OSError, ValueError, KeyError, TypeError):
        return []

def cached_exact(url, *, root=ROOT):
    parsed = urlparse(url)
    for post in cached_posts(f'{parsed.scheme}://{parsed.netloc}', root=root):
        if unquote(post['link']).rstrip('/') == unquote(url).rstrip('/'):
            return post
    return None
