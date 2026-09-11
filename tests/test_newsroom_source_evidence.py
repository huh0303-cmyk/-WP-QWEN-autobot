import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import newsroom_source_evidence as evidence

@pytest.mark.parametrize('url', ['http://www.gov.uk/government/news/x', 'https://www.gov.uk.evil.test/government/news/x', 'https://example.org/story', 'https://user@www.gov.uk/government/news/x'])
def test_only_allowlisted_primary_release_is_fetched(monkeypatch, url):
    request=Mock()
    monkeypatch.setattr(evidence.requests, 'get', request)
    assert evidence.enrich_source(url, 'RSS facts') == 'RSS facts'
    request.assert_not_called()

def test_extracts_official_body_not_navigation(monkeypatch):
    response=Mock(status_code=200, text='<nav>Other headlines</nav><div class="gem-c-govspeak">' + ('Official factual evidence. ' * 20) + '</div>')
    request=Mock(return_value=response)
    monkeypatch.setattr(evidence.requests, 'get', request)
    result=evidence.enrich_source('https://www.gov.uk/government/news/x','RSS facts')
    assert 'Official factual evidence.' in result and 'Other headlines' not in result
    assert request.call_args.kwargs['allow_redirects'] is False

def test_redirect_is_not_followed_or_claimed_verified(monkeypatch):
    monkeypatch.setattr(evidence.requests, 'get', Mock(return_value=Mock(status_code=302)))
    assert evidence.enrich_source('https://www.gov.uk/government/news/x','RSS facts') == 'RSS facts'
