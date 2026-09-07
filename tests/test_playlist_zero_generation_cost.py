import pytest
import youtube_playlist_maker as maker

def test_paid_generation_is_blocked():
    with pytest.raises(RuntimeError, match='PAID_GENERATION_DISABLED'):
        maker.base.gemini_generate_image('prompt', 'output.png')

def test_hour_target_and_existing_nature_routing():
    assert maker.base.pick_duration_target() == (3000,4200)
    assert all(v == (3000,4200) for v in maker.base.HEALING_THEME_DURATION_SEC.values())
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

def test_intro_uses_local_ffmpeg_and_keeps_audio(monkeypatch):
    calls=[]
    monkeypatch.setattr(maker.base,'run_ffmpeg',lambda cmd:calls.append(cmd))
    maker.make_intro_video('cover.png','music.m4a','video.mp4')
    assert calls[0][0]=='ffmpeg'
    assert 'music.m4a' in calls[0]
    assert '-shortest' in calls[0]
    assert 'min(on,150)' in calls[0][calls[0].index('-vf')+1]

def test_language_cycle_is_balanced():
    counts={}
    for _ in range(40):
        chosen=maker.balanced_language(counts)
        counts[chosen]=counts.get(chosen,0)+1
    assert set(counts.values())=={10}

def test_kpop_never_falls_back_to_other_languages(monkeypatch):
    monkeypatch.setattr(maker.base,'CHANNEL_KEY','kpop')
    with pytest.raises(RuntimeError,match='WAITING_ASSETS'):
        maker.strict_tracks([{'name':'[ja] Japanese song.mp3'}],'mixed')
