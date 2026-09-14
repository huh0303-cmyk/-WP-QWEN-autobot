import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from knowledge_scene_edit import validate_scene, render_scenes


def test_reject_overlong_narration():
    with pytest.raises(ValueError):
        validate_scene('word ' * 100, 10)


def test_reject_empty_narration():
    with pytest.raises(ValueError):
        validate_scene('', 20)


def test_no_loop_when_speech_exceeds_source(tmp_path):
    def tts(*args):
        return 'audio', [], 25
    with pytest.raises(RuntimeError, match='exceeds footage'):
        render_scenes('space', 'nasa', [{'path': 'source', 'duration': 10}],
                      str(tmp_path), lambda *a, **k: '{"narration":"The Moon is visible."}',
                      lambda x: x, lambda *a: {'alignment_score': 99}, tts,
                      None, None, None, None, None)


def test_each_scene_keeps_own_clip_and_voice(tmp_path):
    pairs = []
    def tts(*a):
        return 'audio', [], 8
    def normalize(source, dest, seconds):
        pairs.append((source, seconds))
    render_scenes('film', 'silent_era', [{'path': 'first', 'duration': 10}, {'path': 'second', 'duration': 12}],
                  str(tmp_path), lambda *a, **k: '{"narration":"The actor enters the room."}',
                  lambda x: x, lambda *a: {'alignment_score': 99}, tts,
                  lambda *a: None, lambda *a: None, normalize, lambda *a: None, lambda *a: 8)
    assert pairs == [('first', 8), ('second', 8)]
    assert (tmp_path / 'scene_manifest.json').exists()
