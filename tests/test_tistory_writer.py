import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import claude_text
import tistory_writer

JOB = {
    "job_id": "tistory_dental_cost:2026-08-28",
    "site_id": "tistory_dental_cost",
    "title": "K-치과비용연구소",
    "language": "ko",
    "audience": "한국인",
    "categories": ["임플란트", "치아보험"],
    "intent": ["비용"],
    "seed_topic": "임플란트 비용이 병원마다 다른 이유",
    "trend_mode": False,
    "official_source_required": False,
}


def test_claude_disabled_skips_without_calling_the_api():
    with patch.object(claude_text, "ANTHROPIC_API_KEY", ""), \
         patch.object(claude_text, "CLAUDE_ENABLED", False):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["status"] == "SKIPPED_CLAUDE_DISABLED"
    assert draft["public_allowed"] is False


def test_valid_json_response_becomes_a_draft_ready_for_review():
    payload = json.dumps({
        "title": "임플란트 비용, 병원마다 다른 진짜 이유",
        "category": "임플란트",
        "body_html": "<h2>핵심</h2><p>본문</p>",
    })
    with patch.object(claude_text, "ANTHROPIC_API_KEY", "test"), \
         patch.object(claude_text, "CLAUDE_ENABLED", True), \
         patch("tistory_writer.claude_generate_text", return_value=payload):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["status"] == "DRAFT_READY"
    assert draft["publish_policy"] == "awaiting_approval"
    assert draft["public_allowed"] is False
    assert draft["category"] == "임플란트"


def test_category_outside_allowed_list_is_corrected_not_trusted():
    payload = json.dumps({
        "title": "제목",
        "category": "완전히 관련없는 카테고리",
        "body_html": "<p>본문</p>",
    })
    with patch.object(claude_text, "ANTHROPIC_API_KEY", "test"), \
         patch.object(claude_text, "CLAUDE_ENABLED", True), \
         patch("tistory_writer.claude_generate_text", return_value=payload):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["category"] in JOB["categories"]


def test_unparseable_response_is_reported_not_silently_dropped():
    with patch.object(claude_text, "ANTHROPIC_API_KEY", "test"), \
         patch.object(claude_text, "CLAUDE_ENABLED", True), \
         patch("tistory_writer.claude_generate_text", return_value="not json at all"):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["status"] == "PARSE_FAILED"
    assert draft["public_allowed"] is False


def test_official_source_sites_get_an_explicit_no_fabrication_instruction():
    job = {**JOB, "official_source_required": True, "trend_mode": True}
    prompt = tistory_writer.build_prompt(job)
    assert "official source" in prompt.lower()
    assert "check the official source instead of inventing" in prompt.lower()
