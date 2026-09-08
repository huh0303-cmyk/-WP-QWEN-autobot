import sys
from pathlib import Path
from collections import Counter
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from playlist_language_policy import romantic_languages, select_bank_tracks
from youtube_english_metadata import playlist_metadata, validate_metadata

def test_twenty_tracks_mix_all_four_languages():
    assert Counter(romantic_languages(20)) == dict.fromkeys(['french','japanese','spanish','italian'], 5)

def test_bank_refuses_missing_language():
    with pytest.raises(RuntimeError, match='WAITING_ASSETS'):
        select_bank_tracks([{'id':'1','name':'[fr] approved.mp3'}], 'globalmusic')

def test_every_channel_has_complete_english_metadata():
    for channel in ['globalmusic','healing','kpop','mbb','starbucks']:
        title, description, _, _ = playlist_metadata(channel, 'A Quiet Evening Together', 58)
        validate_metadata(title, description)
        assert 800 <= len(description) <= 1200
        assert len(title) <= 100

def test_metadata_rejects_short_description():
    with pytest.raises(ValueError):
        validate_metadata('Nice evening', 'Two lines are not enough.')
