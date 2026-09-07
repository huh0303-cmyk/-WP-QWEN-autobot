"""Carry Tistory tags and representative media through the existing queue schema."""
import html
import json
import re

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
