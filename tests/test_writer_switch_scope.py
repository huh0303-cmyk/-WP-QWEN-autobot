import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import economy_text as engine
from editorial_topic_scope import topic_fits, choose_scoped_keyword

def test_repair_changes_gpt_to_gemini(monkeypatch):
    monkeypatch.setattr(engine,'last_writer_model','gpt-5-mini')
    monkeypatch.setattr(engine,'_try_gemini',lambda p,t:'gemini repaired')
    monkeypatch.setattr(engine,'_try_gpt',lambda p,t: (_ for _ in ()).throw(AssertionError('same writer')))
    assert engine.generate_text('repair',repair=True)=='gemini repaired'

def test_repair_changes_gemini_to_gpt(monkeypatch):
    monkeypatch.setattr(engine,'last_writer_model','gemini-2.5-flash')
    monkeypatch.setattr(engine,'_try_gpt',lambda p,t:'gpt repaired')
    monkeypatch.setattr(engine,'_try_gemini',lambda p,t: (_ for _ in ()).throw(AssertionError('same writer')))
    assert engine.generate_text('repair',repair=True)=='gpt repaired'

def test_geography_alone_does_not_qualify_keyword():
    assert not topic_fits('https://jobinkorea365.com','Korea election results')
    assert not topic_fits('https://k-trip365.com','Korea salary negotiation')
    assert topic_fits('https://jobinkorea365.com','Korea job interview preparation')
    assert topic_fits('https://k-trip365.com','Seoul autumn walking routes')
    assert choose_scoped_keyword('https://jobinkorea365.com','Korea election results',
                                ['Korea bitcoin','Korea job interview preparation'])=='Korea job interview preparation'


def test_two_attempt_cap_includes_transport_and_quality_failure(monkeypatch):
    import pytest
    engine.begin_article()
    calls=[]
    def gpt(p,t):
        calls.append('gpt')
        raise RuntimeError('provider unavailable')
    def gemini(p,t):
        calls.append('gemini')
        return 'draft failing quality'
    monkeypatch.setattr(engine,'_try_gpt',gpt)
    monkeypatch.setattr(engine,'_try_gemini',gemini)
    assert engine.generate_text('first',force_gpt=True)=='draft failing quality'
    with pytest.raises(RuntimeError,match='WRITERS_EXHAUSTED'):
        engine.generate_text('repair',repair=True)
    assert calls==['gpt','gemini']
    monkeypatch.setattr(engine,'_article_attempts',None)
