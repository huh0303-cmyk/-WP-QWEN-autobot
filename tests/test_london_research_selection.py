from scripts import london_four_agent_pipeline as pipeline


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
