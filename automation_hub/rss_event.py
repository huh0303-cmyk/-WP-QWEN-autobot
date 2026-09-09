"""Validate the RSS item captured by the watcher, without re-reading a rolling feed."""
import json
import math
import time


def resolve_rss_event(raw, exact_url, sources, language, *, now=None):
    item = json.loads(raw)
    source = next((s for s in sources if s['key'] == item.get('source_key') and s['language'] == language), None)
    if source is None:
        raise ValueError('RSS event source is not configured for this newsroom')
    url = str(item.get('url', '')).split('#')[0].rstrip('/')
    if not url.startswith(('https://', 'http://')) or url != exact_url.split('#')[0].rstrip('/'):
        raise ValueError('RSS event URL does not match the requested article')
    published = float(item.get('published') or 0)
    age = (time.time() if now is None else now) - published
    if not math.isfinite(published) or not -600 <= age <= 72 * 3600:
        raise ValueError('RSS event publication date is missing, stale or in the future')
    title = str(item.get('title', '')).strip()
    if not title:
        raise ValueError('RSS event title is missing')
    return title[:500], str(item.get('summary', ''))[:5000], source['name'], item['url'], source.get('category', '')
