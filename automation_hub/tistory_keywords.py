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
    candidates=[]
    for item in ranked:
        matches={term:volume for term,volume in volumes.items() if normalized(item.keyword) in normalized(term) or normalized(term) in normalized(item.keyword)}
        if not matches or item.outlet_count<2 or duplicate(item.keyword,history): continue
        volume=max(matches.values())
        score=50*math.log1p(volume)/math.log1p(max(volumes.values())) + 50*min(1,item.mention_count/10)
        candidates.append((score,item.keyword,item,volume,matches))
    if not candidates: raise RuntimeError('검색량·복수 매체 언급·중복 검사를 모두 통과한 새 키워드 없음')
    score,_,item,volume,matches=max(candidates,key=lambda row:(row[0],row[1]))
    return item.keyword, round(score), {'search_volume_approx':volume,'search_matches':matches,'mentions':item.mention_count,'outlets':item.outlet_count,'evidence_urls':list(item.evidence_urls),'live_cross_media':round(score)}

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
