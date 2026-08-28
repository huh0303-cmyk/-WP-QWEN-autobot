import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import tistory_writer

JOB = {"job_id": "tistory_dental_cost:2026-08-28", "site_id": "tistory_dental_cost", "title": "한국치과비용연구소", "language": "ko", "audience": "한국인", "categories": ["임플란트", "치아보험"], "intent": ["비용"], "seed_topic": "임플란트 비용이 병원마다 다른 이유", "trend_mode": False, "official_source_required": False}
BODY = "<h2>비용이 달라지는 순간</h2><p>비용을 확인하는 독자를 위한 설명입니다.</p><ul><li>확인 항목</li></ul><h2>상담 전 질문</h2><p>" + ("충분한 새 설명 " * 100) + "</p>"
VALID = json.dumps({"title": "상담실에서 당황하지 않게, 임플란트 비용이 달라지는 순간", "category": "임플란트", "meta_description": "임플란트 상담 전 비용 차이를 만드는 항목을 차분히 확인합니다.", "image_prompt": "치과 상담실에서 견적서를 살펴보는 사람의 안도감", "body_html": BODY})
AUDIT_OK = json.dumps({"ok": True, "issues": []})


def test_gemini_then_claude_then_image_chain():
    with patch("tistory_writer.gemini_generate_text", return_value=VALID) as gemini, patch("tistory_writer.claude_available", return_value=True), patch("tistory_writer.claude_generate_text", return_value=AUDIT_OK), patch("tistory_writer.generate_image_url", return_value="https://example.test/image.webp"):
        draft = tistory_writer.generate_draft(JOB)
    gemini.assert_called_once()
    assert draft["status"] == "DRAFT_READY"
    assert draft["quality_score"] >= 70
    assert draft["first_image_priority"] is True


def test_gpt_rewrites_after_gemini_generation_failure():
    with patch("tistory_writer.gemini_generate_text", side_effect=RuntimeError("failed")), patch("tistory_writer.openai_available", return_value=True), patch("tistory_writer.openai_generate_text", return_value=VALID) as gpt, patch("tistory_writer.claude_available", return_value=True), patch("tistory_writer.claude_generate_text", return_value=AUDIT_OK), patch("tistory_writer.generate_image_url", return_value=None):
        draft = tistory_writer.generate_draft(JOB)
    gpt.assert_called_once()
    assert draft["engine"] == "gpt"


def test_claude_is_a_blocking_gate():
    with patch("tistory_writer.gemini_generate_text", return_value=VALID), patch("tistory_writer.claude_available", return_value=False):
        draft = tistory_writer.generate_draft(JOB)
    assert draft["status"] == "AUDIT_FAILED"
    assert draft["public_allowed"] is False


def test_prompt_forbids_copy_and_repeated_ai_titles():
    prompt = tistory_writer.build_writer_prompt(JOB).lower()
    assert "never copy" in prompt
    assert "ai-sounding" in prompt
    assert "emotionally resonant" in prompt
