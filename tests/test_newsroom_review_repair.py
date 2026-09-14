import json
import sys
from pathlib import Path
from unittest.mock import Mock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import newsroom_review_repair as repair

PACKET = dict(title='Wrong office title', content='<p>News</p><img src="https://example.org/a.jpg">',
              meta='News report', keyword='event', source_evidence={'headline': 'Source headline'})


def test_one_correction_is_rechecked_and_preserves_media(monkeypatch):
    review = Mock(side_effect=[ValueError('CONSENSUS_FAILED: office title wrong'), {'ok': True}])
    fixed = dict(title='Correct office title', content=PACKET['content'], meta='Corrected summary')
    generate = Mock(return_value=json.dumps(fixed))
    monkeypatch.setattr(repair, 'require_editorial_approval', review)
    monkeypatch.setattr(repair, 'generate_text', generate)
    title, content, meta, approved = repair.review_newsroom(**PACKET)
    assert title == fixed['title'] and approved['ok']
    assert review.call_count == 2 and generate.call_count == 1
    assert review.call_args.kwargs['content'] == content
    assert 'office title wrong' in generate.call_args.args[0]


@pytest.mark.parametrize('error', ['CONSENSUS_FAILED: check_failed: timeout', 'NEWS_SOURCE_EVIDENCE_MISSING'])
def test_infrastructure_or_missing_source_does_not_trigger_paid_rewrite(monkeypatch, error):
    monkeypatch.setattr(repair, 'require_editorial_approval', Mock(side_effect=ValueError(error)))
    generate = Mock()
    monkeypatch.setattr(repair, 'generate_text', generate)
    with pytest.raises(ValueError):
        repair.review_newsroom(**PACKET)
    generate.assert_not_called()


def test_second_rejection_stops_without_repeated_rewrites(monkeypatch):
    monkeypatch.setattr(repair, 'require_editorial_approval', Mock(side_effect=ValueError('CONSENSUS_FAILED: unsupported')))
    generate = Mock(return_value=json.dumps({k: PACKET[k] for k in ('title', 'content', 'meta')}))
    monkeypatch.setattr(repair, 'generate_text', generate)
    with pytest.raises(ValueError, match='CONSENSUS_FAILED'):
        repair.review_newsroom(**PACKET)
    assert generate.call_count == 1


def test_repair_cannot_replace_images(monkeypatch):
    monkeypatch.setattr(repair, 'require_editorial_approval', Mock(side_effect=ValueError('CONSENSUS_FAILED: incorrect')))
    monkeypatch.setattr(repair, 'generate_text', Mock(return_value=json.dumps(dict(title='Title', content='<p>Changed</p>', meta='Meta'))))
    with pytest.raises(ValueError, match='CHANGED_MEDIA_OR_LINKS'):
        repair.review_newsroom(**PACKET)


def test_harmless_attribute_formatting_change_is_not_treated_as_a_swap(monkeypatch):
    """2026-09-12: GPT re-quoting/reordering an <img> tag's own attributes (not
    its src) is not a media swap and must not fail closed the whole job."""
    monkeypatch.setattr(repair, 'require_editorial_approval', Mock(side_effect=[ValueError('CONSENSUS_FAILED: incorrect'), {'ok': True}]))
    reformatted = PACKET['content'].replace(
        '<img src="https://example.org/a.jpg">',
        "<img loading='lazy' src='https://example.org/a.jpg' alt=''>")
    monkeypatch.setattr(repair, 'generate_text', Mock(return_value=json.dumps(
        dict(title='Correct office title', content=reformatted, meta='Corrected summary'))))
    title, content, meta, approved = repair.review_newsroom(**PACKET)
    assert title == 'Correct office title' and approved['ok']
