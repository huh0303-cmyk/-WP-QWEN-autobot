"""Carry Tistory tags and representative media through the existing queue schema."""
import html
import json
import re

EDITOR_CATEGORIES = {
    'tistory_finance_housing': {'전월세':'전월세·임대차','청약·주택':'청약·주택구입','대출':'주택대출·생활금융','생활금융':'주택대출·생활금융'},
    'tistory_insurance_lab': {'실손·건강보험':'[실비·실손·질병보험 비교]','자동차·생활보험':'[자동차·화재·생활보험 비교]','치아보험·치과비용':'[실비·실손·질병보험 비교]','보험금청구':'[정부 지원 의료비·청구]'},
    'tistory_health_info': {'건강검진':'건강정보','만성질환':'질병별 대처법','증상·병원이용':'질병별 대처법','영양·생활습관':'건강·영양성분'},
    'tistory_life365': {'지원금·신청':'정부지원금·보조금','생활행정':'생활행정·민원','교통·시간표':'생활혜택·복지정보'},
    'tistory_ktrip365': {'숙소·계절여행':'[한국 한달살기 숙소 & 비용]'},
}

def editor_category(site_id, category):
    return EDITOR_CATEGORIES.get(site_id, {}).get(category, category)

def media_metadata(draft):
    try:
        saved = json.loads(draft.get('message') or '{}')
    except (ValueError, TypeError):
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    raw = draft.get('tags') or saved.get('tags') or draft.get('labels') or []
    if isinstance(raw, str):
        raw = re.split(r'[,#\n]', raw)
    if not isinstance(raw, (tuple, list)):
        raw = []
    tags = []
    for value in [*raw, draft.get('source_keyword', ''), draft.get('category', '')]:
        tag = re.sub(r'[,#<>\[\]]', '', str(value))
        tag = ' '.join(tag.split())[:30].strip()
        if tag and tag.casefold() not in {t.casefold() for t in tags}:
            tags.append(tag)
    url = draft.get('representative_image_url') or draft.get('image_url') or saved.get('representative_image_url') or ''
    if not url:
        match = re.search(r'<img\b[^>]*\bsrc\s*=\s*([\'"])(.*?)\1', draft.get('body_html') or draft.get('content_html') or '', re.I | re.S)
        if match:
            url = html.unescape(match.group(2))
    return {'tags': tags[:8], 'representative_image_url': url}
