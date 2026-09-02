from unittest.mock import Mock, patch

from scripts.knowledge_narrator import _documentary_candidates, select_documentary_narrator


def test_filters_to_english_documentary_male_and_female_voices():
    response = Mock()
    response.json.return_value = {"voices": [
        {"voice_id": "usm", "name": "US Man", "labels": {"accent": "american", "gender": "male", "use case": "narration"}},
        {"voice_id": "ukf", "name": "UK Woman", "labels": {"accent": "british", "gender": "female", "use case": "documentary"}},
        {"voice_id": "cartoon", "name": "Character", "labels": {"accent": "american", "gender": "male", "use case": "characters"}},
    ]}
    response.raise_for_status.return_value = None
    with patch("scripts.knowledge_narrator.requests.get", return_value=response):
        assert {voice["voice_id"] for voice in _documentary_candidates("key")} == {"usm", "ukf"}


def test_blank_config_never_overrides_fallback(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_VOICE_US_MALE_ID", "")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert select_documentary_narrator()["voice_id"]
