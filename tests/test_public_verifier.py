from types import SimpleNamespace
from automation_hub.public_verifier import verify_publication


def test_wordpress_smart_quotes_match_public_plain_quotes(monkeypatch):
    monkeypatch.setattr('automation_hub.public_verifier.requests.get',lambda *a,**k: SimpleNamespace(
        text="<title>스튜어드십 &#39;주가 누르기&#39; 관행 - 한국신문</title>",url='https://example.com/article',status_code=200))
    assert verify_publication('https://example.com/article', '스튜어드십 &#8216;주가 누르기&#8217; 관행', attempts=1).ok


def test_empty_title_is_not_proof_of_publication(monkeypatch):
    monkeypatch.setattr('automation_hub.public_verifier.requests.get',lambda *a,**k: SimpleNamespace(
        text='<html>Sign in</html>',url='https://example.com/article',status_code=200))
    assert not verify_publication('https://example.com/article','Expected article',attempts=1).ok


def test_different_article_remains_blocked(monkeypatch):
    monkeypatch.setattr('automation_hub.public_verifier.requests.get',lambda *a,**k: SimpleNamespace(
        text='<title>Unrelated news</title>',url='https://example.com/article',status_code=200))
    assert not verify_publication('https://example.com/article','Expected article',attempts=1).ok
