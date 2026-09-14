import json
import requests
from scripts.newsroom_real_photos import CATALOG, figure, select_photo


class Response:
    text = '<h4>PUBLIC DOMAIN</h4><p>NAVCENT Public Affairs</p>'
    def raise_for_status(self): pass


def test_relevant_asset_keeps_original_credit_date_and_archive_context():
    photo = select_photo('Iranian oil tankers and a U.S. warship', get=lambda *a, **k: Response())
    rendered = figure(photo)
    assert '20 April 2026' in rendered
    assert 'not a photograph of the latest strikes' in rendered
    assert photo['source_page'] in rendered
    assert photo['license_url'] in rendered
    assert 'endorsement' in rendered


def test_unrelated_story_does_not_get_a_military_photo():
    assert select_photo('Iranian poetry festival', get=lambda *a, **k: Response()) is None


def test_missing_item_rights_or_source_outage_falls_back_without_blocking_news():
    bad = Response(); bad.text = '<h1>All rights reserved</h1>'
    assert select_photo('Iran tanker', get=lambda *a, **k: bad) is None
    def offline(*a, **k): raise requests.Timeout()
    assert select_photo('Iran tanker', get=offline) is None


def test_unreviewed_or_nonpublic_asset_is_rejected():
    asset = json.loads(CATALOG.read_text(encoding='utf-8'))['assets'][0]
    asset['license'] = 'all_rights_reserved'
    assert select_photo('Iran tanker', catalog=[asset], get=lambda *a, **k: Response()) is None


def test_caption_cannot_insert_html():
    asset = json.loads(CATALOG.read_text(encoding='utf-8'))['assets'][0]
    asset['caption_en'] = '<script>bad</script>'
    assert '<script>' not in figure(asset)
