import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from knowledge_scene_edit import validate_scene, render_scenes, generate_grounded_scene_narration


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


def test_alignment_feedback_gets_one_grounded_rewrite_without_weakening_gate():
    prompts = []
    checks = []
    responses = iter((
        '{"narration":"A generic account of the topic."}',
        '{"narration":"A worker turns the hand crank beside the machine."}',
    ))

    def generate(prompt, **kwargs):
        prompts.append(prompt)
        return next(responses)

    def verify(topic, clips, narration, generate_fn):
        checks.append(narration)
        if len(checks) == 1:
            raise RuntimeError('alignment 5/100: narration does not match the machine')
        return {'alignment_score': 96, 'verdict': 'PASS'}

    narration, review = generate_grounded_scene_narration(
        'an early telephone exchange', 'invention',
        {'title': 'Switchboard at work', 'duration': 12,
         'visual_analysis': {'visual_summary': 'An operator turns a hand crank beside a switchboard.'}},
        12, generate, lambda value: value, verify,
    )

    assert len(checks) == 2
    assert 'alignment reviewer rejected' in prompts[1]
    assert 'hand crank' in prompts[1]
    assert review['alignment_score'] == 96
    assert narration == checks[1]


def test_alignment_retry_still_fails_closed():
    responses = iter((
        '{"narration":"First mismatch."}',
        '{"narration":"Second mismatch."}',
    ))
    checks = []

    def verify(*args):
        checks.append(True)
        raise RuntimeError('alignment rejected')

    with pytest.raises(RuntimeError, match='alignment rejected'):
        generate_grounded_scene_narration(
            'topic', 'invention', {'duration': 12, 'visual_analysis': {}}, 12,
            lambda *a, **k: next(responses), lambda value: value, verify,
        )
    assert len(checks) == 2
