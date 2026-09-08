"""Keep last verified evidence visible when a later refresh fails."""


def index_metrics(entry):
    summary = entry.get('summary') or {}
    unknown = summary.get('unknown')
    indexed = summary.get('indexed')
    verified_at = entry.get('audited_at') or ''
    error = entry.get('error')
    if not verified_at or (unknown and not indexed and not summary.get('unindexed')):
        indexed = None
    stale = bool(error and indexed is not None)
    if stale:
        status = '마지막 확인값 · 최근 갱신 실패'
    elif error == 'gsc_property_not_accessible':
        status = 'Search Console 권한 연결 필요'
    elif indexed is None:
        status = '확인 실패 · 재검사 필요' if error or unknown else '정밀 집계 중'
    else:
        status = f'Google URL별 확인 · 미확인 {unknown}개' if unknown else 'Google URL별 전수 확인'
    return {'indexed': indexed,
            'indexed_delta': None if error or unknown else summary.get('indexed_delta'),
            'index_unknown': unknown, 'index_unindexed': summary.get('unindexed'),
            'index_total': summary.get('total_published'),
            'index_partial': bool(unknown), 'index_stale': stale,
            'index_checked_at': verified_at, 'index_status': status}


from datetime import datetime, timedelta, timezone
from functools import lru_cache
import time
import requests


@lru_cache(maxsize=128)
def recent_post_counts(site_url, bucket):
    """Count actual published posts by GMT timestamp converted to Korea date."""
    today = datetime.now(timezone(timedelta(hours=9))).date()
    yesterday = today - timedelta(days=1)
    counts = {today: 0, yesterday: 0}
    try:
        for page in range(1, 11):
            for attempt in range(3):
                try:
                    response = requests.get(site_url.rstrip('/') + '/wp-json/wp/v2/posts',
                        params={'status': 'publish', 'per_page': 100, 'page': page,
                                'orderby': 'date', 'order': 'desc', '_fields': 'id,date_gmt'},
                        timeout=(5, 12))
                    response.raise_for_status()
                    posts = response.json()
                    if not isinstance(posts, list):
                        raise ValueError('Invalid posts response')
                    break
                except requests.RequestException:
                    if attempt == 2:
                        raise
                    time.sleep(.3 * (attempt + 1))
            oldest = today
            for post in posts:
                stamp = datetime.fromisoformat(post['date_gmt'].replace('Z', '+00:00'))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                day = stamp.astimezone(timezone(timedelta(hours=9))).date()
                oldest = min(oldest, day)
                if day in counts:
                    counts[day] += 1
            if len(posts) < 100 or oldest < yesterday:
                return {'new_posts': counts[today], 'new_posts_delta': counts[today] - counts[yesterday]}
    except (requests.RequestException, ValueError, TypeError, KeyError):
        pass
    return {'new_posts': None, 'new_posts_delta': None}
