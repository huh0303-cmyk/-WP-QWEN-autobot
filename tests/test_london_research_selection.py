import json
import importlib
from pathlib import Path

import pytest

from scripts import london_four_agent_pipeline as pipeline
from scripts import direct_topic_research


def test_research_preserves_selected_models(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "STATE_DIR", tmp_path)
    run_id = "lgpt-20260928-120000-abcdef"
    pipeline._write_state({"run_id": run_id, "site_id": "blogger_koreanews", "publish_mode": "manual",
                           "writer_model": "gemini-3.1-flash-lite", "image_model": "pexels",
                           "category": "Health", "created_at": "2026-09-28T00:00:00Z"})
    started = pipeline._research_start_state("blogger_koreanews", run_id, "", "blogger")
    assert started["writer_model"] == "gemini-3.1-flash-lite"
    assert started["image_model"] == "pexels"
    assert started["publish_mode"] == "manual"
    assert started["category"] == "Health"


def test_research_removes_unverified_search_volumes_and_prompt_template():
    raw = "KEYWORD: vaccine guidance\nGOOGLE: 10000+\nNAVER: 2000+\nVOLUME: 10000+\nRATIONALE: current interest\nKEYWORD: <3-6 word search-style phrase>"
    clean = pipeline._clean_research_evidence(raw)
    assert "10000" not in clean and "2000" not in clean
    assert "<3-6" not in clean
    assert "KEYWORD: vaccine guidance" in clean


@pytest.mark.parametrize(
    "keyword",
    [
        "study abroad",
        "one two three four five six seven",
        "<3-6 word search-style phrase>",
        "https://example.com study Korea",
    ],
)
def test_research_rejects_invalid_search_phrases(keyword):
    with pytest.raises(RuntimeError):
        pipeline._parse_keyword(f"KEYWORD: {keyword}")


def test_research_accepts_specific_three_to_six_word_phrase():
    assert pipeline._parse_keyword("KEYWORD: study in Korea scholarships") == "study in Korea scholarships"


def test_direct_research_uses_bounded_local_generation(monkeypatch):
    captured = {}

    def fake_generate(prompt, **kwargs):
        captured.update(kwargs)
        return "KEYWORD: study in Korea scholarships"

    local_text = importlib.import_module("local_text")
    monkeypatch.setattr(local_text, "local_generate_text", fake_generate)
    direct_topic_research.choose_keyword(
        {"wordpress": {"theme": "International Students", "persona": "Student adviser"}, "language": "en"},
        {"google_news_headlines": ["Scholarship applications open"]},
    )
    assert captured["timeout"] == 120
    assert captured["max_tokens"] == 320


def test_all_london_webhooks_acknowledge_immediately():
    workflow_path = Path(__file__).parents[1] / "deploy/n8n/workflows/london_content_four_agent.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    webhooks = [node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.webhook"]
    assert len(webhooks) == 6
    assert all(node["parameters"].get("responseMode") == "onReceived" for node in webhooks)
