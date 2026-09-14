"""Require both measured search interest and independent media mentions."""
import math
import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
import requests

def normalized(text):
    return re.sub(r'[^0-9a-z가-힣]', '', str(text).lower())

def duplicate(text, history):
    from .repetition_guard import title_repeats
    if any(title_repeats(text, old) for old in history): return True
    key = normalized(text)
    return any(key and (key == normalized(old) or SequenceMatcher(None,key,normalized(old)).ratio() >= .72) for old in history)

def search_volumes():
    response=requests.get('https://trends.google.com/trending/rss?geo=KR',timeout=20)
    response.raise_for_status()
    result={}
    for item in ET.fromstring(response.content).findall('.//item'):
        title=item.findtext('title','').strip()
        traffic=next((node.text or '' for node in item if node.tag.endswith('approx_traffic')), '')
        value=float(re.sub(r'[^0-9.]','',traffic) or 0)
        value *= 1000000 if 'M' in traffic.upper() else 1000 if 'K' in traffic.upper() else 1
        if title and value>0: result[title]=int(value)
    if not result: raise RuntimeError('검색량 근거 없음: 고정 주제로 대체하지 않습니다')
    return result

def choose(ranked, volumes, history):
    """Require independent multi-outlet coverage and no duplicate topic.

    A niche site's real, multi-outlet-verified topic (`ranked` already
    enforces outlet_count>=2 and profile fit in blogger_topic_router.rank_topics)
    rarely happens to also appear in Korea's *general* daily trending-search
    list - a travel keyword competing for a slot against whatever celebrity
    or sports story is trending nationwide that day. Requiring a literal
    substring match against that unrelated general list as a hard gate
    starved niche sites of every candidate on most days (observed 2026-09-09,
    tistory_ktrip365: zero candidates despite real ranked topics existing).
    Generic trend overlap is now a scoring bonus when it happens to be
    present, not a requirement - the real quality bars (2+ independent
    outlets, not a repeat of recent history) are unchanged.
    """
    candidates=[]
    max_volume=max(volumes.values()) if volumes else 0
    for item in ranked:
        if item.outlet_count<2 or duplicate(item.keyword,history): continue
        matches={term:volume for term,volume in volumes.items() if normalized(item.keyword) in normalized(term) or normalized(term) in normalized(item.keyword)}
        volume=max(matches.values()) if matches else 0
        trend_bonus=50*math.log1p(volume)/math.log1p(max_volume) if matches and max_volume else 0
        score=trend_bonus + 50*min(1,item.mention_count/10)
        candidates.append((score,item.keyword,item,volume,matches))
    if not candidates: raise RuntimeError('복수 매체 언급·중복 검사를 통과한 새 키워드 없음 (관련 뉴스 자체가 없음)')
    score,_,item,volume,matches=max(candidates,key=lambda row:(row[0],row[1]))
    return item.keyword, round(score), {'search_volume_approx':volume,'search_matches':matches,'general_trend_match':bool(matches),'mentions':item.mention_count,'outlets':item.outlet_count,'evidence_urls':list(item.evidence_urls),'live_cross_media':round(score)}

def recent_history(site):
    # Include public posts predating the queue as well as all reserved/queued topics.
    response=requests.get(site['url'].rstrip('/')+'/rss',timeout=20)
    response.raise_for_status()
    titles=[node.text or '' for node in ET.fromstring(response.content).findall('.//item/title')]
    import os
    from gsheets_direct import get_sheets_service
    from sync_automation_hub_to_sheets import QUEUE_TAB
    values=get_sheets_service().spreadsheets().values().get(spreadsheetId=os.environ['SHEET_ID'],range=f"'{QUEUE_TAB}'!A1:Q").execute().get('values',[])
    if not values: raise RuntimeError('중복 검사용 발행 이력 없음')
    for row in values[1:]:
        record=dict(zip(values[0],row))
        if record.get('site_id')==site['site_id']:
            titles.extend([record.get('title',''),record.get('source_keyword','')])
    return [title for title in titles if title]


def reserve_topic(site, day):
    """Use configured evergreen search intents without inventing trend volume."""
    candidates = [topic for topic in site.get('seed_topics', [])
                  if not duplicate(topic, site.get('recent_history', []))]
    if not candidates:
        raise RuntimeError('비축 주제 중복 검사 후 잔여 없음: 주제 보충 필요')
    import hashlib
    index = int(hashlib.sha256((site['site_id'] + day).encode()).hexdigest()[:8], 16) % len(candidates)
    return candidates[index], 0, {'evergreen_reserve': True, 'search_volume_approx': None,
                                  'official_sources': site.get('official_sources', [])}
