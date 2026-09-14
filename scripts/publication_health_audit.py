"""Read-only public delivery checks. A reachable feed is not a publishing receipt."""
import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parents[1]


def destinations():
    sites = json.loads((ROOT / 'config/automation_hub_sites.json').read_text(encoding='utf-8'))['sites']
    rows = [{'platform': 'newsroom' if s['url'].rstrip('/') in {
        'https://koreanews365.com', 'https://theseouljournal.com'} else 'wordpress',
        'url': s['url'].rstrip('/')} for s in sites if s['platform'] == 'wordpress']
    channels = json.loads((ROOT / 'config/blogger_portfolio.json').read_text(encoding='utf-8'))['channels']
    rows += [{'platform': 'blogger', 'url': s['blogspot'].rstrip('/')} for s in channels]
    rows += [{'platform': 'tistory', 'url': 'https://' + s + '.tistory.com'} for s in
             ['huh0303', 'k-healthcare', 'k-insight-vietnam', 'k-vietnam', 'k-trip365']]
    rows += [{'platform': 'naver', 'url': 'https://blog.naver.com/k-insight-vietnam'}]
    return rows


def check(site):
    row = dict(site)
    platform, url = row['platform'], row['url']
    endpoint = url + ({'blogger': '/feeds/posts/default?alt=json&max-results=1',
                       'tistory': '/rss', 'wordpress': '/wp-json/wp/v2/posts?per_page=1',
                       'newsroom': '/wp-json/wp/v2/posts?per_page=1'}.get(platform, ''))
    row['checked_at'] = datetime.now(timezone.utc).isoformat()
    try:
        response = requests.get(endpoint, timeout=12)
        row['http_status'] = response.status_code
        response.raise_for_status()
        if platform == 'blogger':
            feed = response.json()['feed']
            entries = feed.get('entry', [])
            row['public_count'] = int(feed.get('openSearch$totalResults', {}).get('$t', 0))
            row['latest_url'] = next((x['href'] for x in entries[0].get('link', []) if x.get('rel') == 'alternate'), '') if entries else ''
            row['latest_published'] = entries[0]['published']['$t'] if entries else None
            row['latest_title'] = entries[0].get('title', {}).get('$t', '') if entries else ''
        elif platform in {'wordpress', 'newsroom'}:
            posts = response.json()
            if not isinstance(posts, list):
                raise ValueError('Expected a WordPress post list')
            row['latest_url'] = posts[0]['link'] if posts else ''
            row['latest_published'] = posts[0]['date_gmt'] + 'Z' if posts else None
            row['latest_title'] = posts[0].get('title', {}).get('rendered', '') if posts else ''
            row['public_count'] = int(response.headers['X-WP-Total']) if response.headers.get('X-WP-Total') else None
        elif platform == 'tistory':
            item = ET.fromstring(response.content).find('./channel/item')
            row['latest_url'] = item.findtext('link') if item is not None else ''
            row['latest_published'] = item.findtext('pubDate') if item is not None else None
        else:
            row['status'] = 'browser_authentication_check_required'
            return row
        row['status'] = 'public_post_found' if row.get('latest_url') else 'no_public_post_in_response'
    except requests.HTTPError:
        row['status'] = 'http_error'
    except requests.RequestException as exc:
        row['status'] = 'connection_error'
        row['error_type'] = type(exc).__name__
    except (ValueError, KeyError, ET.ParseError):
        row['status'] = 'unexpected_response'
    return row


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(check, destinations()))
    payload = {'checked_at': datetime.now(timezone.utc).isoformat(),
               'scope': 'Public read access only; no authenticated write or Google indexing verification',
               'sites': rows}
    output = ROOT / 'artifacts/publication-health.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'total': len(rows), 'statuses': {s: sum(r['status'] == s for r in rows)
          for s in sorted({r['status'] for r in rows})}}))


if __name__ == '__main__':
    main()
