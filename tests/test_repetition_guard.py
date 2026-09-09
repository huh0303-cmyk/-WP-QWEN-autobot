import pytest
from automation_hub.repetition_guard import title_repeats, repetition_issues, clean_opening, opening, fetch_wp_history
from automation_hub.content_identity import is_similar_content

def test_reworded_same_topic_title_is_blocked():
    # 2026-09-10: k-trip365.com published both of these within 2 days - the
    # prefix/sequence checks alone missed it because the wording diverges at
    # the third word ("palaces" vs "cultural"), even though the underlying
    # topic (Seoul central area, subway, timed itinerary, seasonal notes) is
    # identical.
    assert title_repeats(
        "Seoul central palaces and markets by subway — an 8-hour timed tourism route with ticketing and seasonal cautions",
        "Seoul central cultural loop by subway — a timed public-transport itinerary with admission and seasonal notes",
    )

def test_reported_investment_template():
    assert title_repeats("How to evaluate Korean AI Digital Finance exposure in listed stocks and ETFs: data, drivers and investor access", "How to evaluate South Korea ESG ETF investment: market snapshot, drivers, risks and access for foreign investors")

def test_distinct_factual_headlines_are_allowed():
    assert not title_repeats("Foreign investors face new ETF disclosure requirements", "Bank earnings rise as credit losses decline")

def test_html_entities_and_case():
    assert title_repeats("Costs &amp; risks of foreign ETF investing", "Costs & risks of foreign ETF investing")

def test_remove_only_exact_leading_title():
    body = clean_opening("ETF disclosure changes", "<h1>ETF disclosure changes</h1><p>Investors must check the revised documents before placing their order.</p><h2>Fees</h2>")
    assert '<h1>' not in body
    assert '<h2>Fees</h2>' in body
    assert opening(body).startswith('Investors')

def test_different_title_cannot_hide_copied_opening():
    lead = '<p>Investors must check the revised documents before placing an order because the disclosure rules have changed.</p>'
    assert repetition_issues('Bank costs explained', lead, [{'title': 'ETF disclosure changes', 'content_html': lead}])

def test_cross_site_history_does_not_block():
    assert not is_similar_content({'site_id':'other', 'title':'How to evaluate Korean stocks'}, site_id='target', title='How to evaluate Korean ETFs', content_html='')

def test_same_site_template_is_blocked():
    assert is_similar_content({'site_id':'target', 'title':'How to evaluate Korean stocks'}, site_id='target', title='How to evaluate Korean ETFs', content_html='')

def test_history_errors_fail_closed():
    class Response:
        def raise_for_status(self): raise RuntimeError('unavailable')
    class Session:
        def get(self, *a, **k): return Response()
    with pytest.raises(RuntimeError): fetch_wp_history(Session(), 'https://example.com', None)
