import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from automation_hub.tistory_media import media_metadata
from automation_hub.tistory_local_adapter import TistoryLocalPublisher
from control_center.tistory import TistoryDraft

def test_queue_metadata_survives_round_trip_and_normalizes_tags():
    import json
    original = media_metadata({'tags':['#실손보험','실손보험','서류'], 'source_keyword':'보험 청구', 'category':'보험', 'image_url':'https://example.com/a.png'})
    restored = media_metadata({'message':json.dumps(original)})
    assert restored == original
    assert restored['tags'] == ['실손보험','서류','보험 청구','보험']

def test_legacy_row_extracts_first_image_and_decodes_url():
    result = media_metadata({'content_html':'<p><img src="https://example.com/a?x=1&amp;y=2"></p>', 'labels':'건강,검진'})
    assert result['representative_image_url'] == 'https://example.com/a?x=1&y=2'
    assert result['tags'] == ['건강','검진']

def draft(**changes):
    args=dict(site_id='tistory_health_info',site_url='https://k-healthcare.tistory.com',title='검진 준비',content_html='<p>본문</p>',category='건강정보',search_description='검진 준비를 설명합니다. '*8,tags=('건강검진',),representative_image_url='https://example.com/hero.png')
    return TistoryDraft(**{**args,**changes})

def test_missing_representative_image_blocks_before_browser_navigation():
    page=Mock()
    with pytest.raises(ValueError,match='대표 이미지'):
        TistoryLocalPublisher(draft(representative_image_url='')).fill(page)
    page.goto.assert_not_called()

def test_download_error_prevents_representative_upload():
    page=Mock()
    response=Mock(headers={'content-type':'text/html'},content=b'x'*1000)
    with patch('automation_hub.tistory_local_adapter.requests.get',return_value=response):
        with pytest.raises(RuntimeError,match='이미지 파일'):
            TistoryLocalPublisher(draft())._fill_representative_image(page)
    page.get_by_role.assert_not_called()

def test_representative_upload_requires_loaded_preview():
    page=Mock()
    response=Mock(headers={'content-type':'image/png'},content=b'x'*1000)
    with patch('automation_hub.tistory_local_adapter.requests.get',return_value=response):
        TistoryLocalPublisher(draft())._fill_representative_image(page)
    payload=page.get_by_role.return_value.locator.return_value.set_input_files.call_args.args[0]
    assert payload['mimeType']=='image/png' and payload['buffer']==b'x'*1000
    page.wait_for_function.assert_called_once()

def test_signed_r2_images_are_rehosted():
    path=Path(__file__).resolve().parents[1]/'scripts/stable_image_hosting.py'
    spec=importlib.util.spec_from_file_location('stable_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.is_temporary('https://example.r2.cloudflarestorage.com/a?X-Amz-Signature=x')
    assert not module.is_temporary('https://raw.githubusercontent.com/repo/main/a.png')
