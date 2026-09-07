import pytest
import youtube_playlist_maker as maker

def test_paid_generation_is_blocked():
    with pytest.raises(RuntimeError, match='PAID_GENERATION_DISABLED'):
        maker.base.gemini_generate_image('prompt', 'output.png')

def test_hour_target_and_existing_nature_routing():
    assert maker.base.pick_duration_target() == (3540,3660)
    assert all(v == (3540,3660) for v in maker.base.HEALING_THEME_DURATION_SEC.values())
    assert maker.base.build_healing_theme_audio.__name__ == 'build_healing_theme_audio'

def test_metadata_does_not_call_paid_writer(monkeypatch):
    monkeypatch.setattr(maker.base, 'CHANNEL_KEY', 'kpop')
    title, description, tags, fallback = maker.metadata('Tonight in Seoul', '', 60)
    assert 'Original K-pop' in title
    assert fallback is False

def test_bank_empty_is_explicit_wait(monkeypatch,tmp_path):
    monkeypatch.setattr(maker,'list_folder_files',lambda *a:[])
    with pytest.raises(RuntimeError,match='WAITING_ASSETS'):
        maker.select_single_bank_image(str(tmp_path),object())
