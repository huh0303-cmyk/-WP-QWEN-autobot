import json
import pytest
from automation_hub.rss_event import resolve_rss_event

SOURCES=[{'key':'desk','name':'News Desk','language':'ko','category':'속보'}]

def event(**changes):
    item=dict(source_key='desk',title='New verified story',url='https://example.com/story',published=1000000,summary='Facts captured from RSS.')
    return json.dumps(dict(item,**changes))

def test_captured_story_survives_feed_rotation_without_network_reads():
    result=resolve_rss_event(event(), 'https://example.com/story',SOURCES,'ko',now=1000010)
    assert result==('New verified story','Facts captured from RSS.','News Desk','https://example.com/story','속보')

@pytest.mark.parametrize('change',[{'source_key':'unknown'},{'published':None},{'published':1},{'published':2000000},{'url':'https://other.example/story'}])
def test_invalid_captured_event_cannot_be_published(change):
    with pytest.raises(ValueError):
        resolve_rss_event(event(**change),'https://example.com/story',SOURCES,'ko',now=1000010)
