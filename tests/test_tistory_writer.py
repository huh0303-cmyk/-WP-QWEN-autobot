import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import claude_text
import openai_text
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

VALID_PAYLOAD = json.dumps({
    "title": "임플란트 비용, 병원마다 다른 진짜 이유",
    "category": "임플란트",
    "body_html": "<h2>핵심</h2><p>본문</p>",
})


def test_gemini_primary_is_used_when_it_succeeds():
    with patch("tistory_writer.gemini_generate_text", return_value=VALID_PAYLOAD) as gemini_call, \
         patch.object(claude_text, "CLAUDE_ENABLED", False):
        draft = tistory_writer.generate_draft(JOB)
    gemini_call.assert_called_once()
    assert draft["status"] == "DRAFT_READY"
    assert draft["engine"] == "gemini"
    assert draft["publish_policy"] == "awaiting_approval"
    assert draft["public_allowed"] is False


def test_gpt_escalation_when_gemini_fails():
    with patch("tistory_writer.gemini_generate_text", side_effect=RuntimeError("quota")), \
         patch.object(openai_text, "OPENAI_API_KEY", "test"), \
         patch.object(openai_text, "OPENAI_ENABLED", True), \
         patch("tistory_writer.openai_generate_text", return_value=VALID_PAYLOAD) as gpt_call, \
         patch.object(claude_text, "CLAUDE_ENABLED", False):
        draft = tistory_writer.generate_draft(JOB)
    gpt_call.assert_called_once()
    assert draft["status"] == "DRAFT_READY"
    assert draft["engine"] == "gpt-rewrite"


def test_write_failed_when_both_gemini_and_gpt_are_unavailable():
    with patch("tistory_writer.gemini_generate_text", side_effect=RuntimeError("quota")), \
         patch.object(openai_text, "OPENAI_API_KEY", ""), \
         patch.object(openai_text, "OPENAI_ENABLED", False):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["status"] == "WRITE_FAILED"
    assert draft["public_allowed"] is False


def test_category_outside_allowed_list_is_corrected_not_trusted():
    payload = json.dumps({
        "title": "제목", "category": "완전히 관련없는 카테고리", "body_html": "<p>본문</p>",
    })
    with patch("tistory_writer.gemini_generate_text", return_value=payload), \
         patch.object(claude_text, "CLAUDE_ENABLED", False):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["category"] in JOB["categories"]


def test_unparseable_response_is_reported_not_silently_dropped():
    with patch("tistory_writer.gemini_generate_text", return_value="not json at all"), \
         patch.object(claude_text, "CLAUDE_ENABLED", False):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["status"] == "PARSE_FAILED"
    assert draft["public_allowed"] is False


def test_official_source_sites_get_an_explicit_no_fabrication_instruction():
    job = {**JOB, "official_source_required": True, "trend_mode": True}
    prompt = tistory_writer.build_writer_prompt(job)
    assert "official source" in prompt.lower()
    assert "check the official source instead of inventing" in prompt.lower()


def test_claude_never_writes_only_audits_a_finished_draft():
    audit_response = json.dumps({"ok": True, "issues": []})
    with patch("tistory_writer.gemini_generate_text", return_value=VALID_PAYLOAD), \
         patch.object(claude_text, "ANTHROPIC_API_KEY", "test"), \
         patch.object(claude_text, "CLAUDE_ENABLED", True), \
         patch("tistory_writer.claude_generate_text", return_value=audit_response) as claude_call:
        draft = tistory_writer.generate_draft(JOB)
    # Claude is called exactly once, for the audit — never to produce the body/title.
    claude_call.assert_called_once()
    audit_prompt = claude_call.call_args[0][0]
    assert draft["title"] in audit_prompt or "임플란트" in audit_prompt
    assert draft["audit"] == {"ok": True, "issues": []}


def test_claude_disabled_skips_audit_without_blocking_the_draft():
    with patch("tistory_writer.gemini_generate_text", return_value=VALID_PAYLOAD), \
         patch.object(claude_text, "CLAUDE_ENABLED", False):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["status"] == "DRAFT_READY"
    assert draft["audit"] is None
