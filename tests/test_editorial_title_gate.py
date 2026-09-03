import ast
import sys
from pathlib import Path
from unittest.mock import Mock
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import editorial_title_gate as gate


@pytest.mark.parametrize("title", ["", "Unlock Your Korea Future", "UNLOCK the Secrets of Korea", "Unlocking Korea Visa Success", "A Guide Q&A: Answers From the Field", "Korea, From Someone Who's Been There", "Housing: Practical Guide Q&A"])
def test_bad_templates_never_reach_model_review(monkeypatch, title):
    check = Mock()
    monkeypatch.setattr(gate, "three_model_consensus", check)
    with pytest.raises(ValueError, match="TITLE_QUALITY_FAIL"):
        gate.require_editorial_approval(title=title, content="body", meta="meta", keyword="key", gemini_generate=Mock())
    check.assert_not_called()


@pytest.mark.parametrize("reject", ["gpt_1", "gpt_2", "missing"])
def test_any_missing_or_failed_check_blocks(monkeypatch, reject):
    checks = {name: {"ok": True} for name in ["gpt_1", "gpt_2"]}
    if reject == "missing":
        del checks["gpt_2"]
    else:
        checks[reject]["ok"] = False
    monkeypatch.setattr(gate, "three_model_consensus", lambda **kw: {"ok": True, "checks": checks})
    with pytest.raises(ValueError, match="CONSENSUS_FAILED"):
        gate.require_editorial_approval(title="Renting in Korea: Deposits and Contracts", content="body", meta="meta", keyword="key", gemini_generate=Mock())


def test_success_reviews_exact_final_packet(monkeypatch):
    check = Mock(return_value={"checks": {name: {"ok": True} for name in ["gpt_1", "gpt_2"]}})
    monkeypatch.setattr(gate, "three_model_consensus", check)
    content = "actual final HTML" * 2000
    title = "Renting in Korea: Deposits and Contracts"
    gate.require_editorial_approval(title=title, content=content, meta="meta", keyword="key", gemini_generate=Mock())
    assert check.call_args.kwargs["content"] == content
    assert check.call_args.kwargs["title"] == title


def test_live_wp_path_cannot_override_title_and_gates_before_save():
    tree = ast.parse((ROOT / "scripts/autopost_mega.py").read_text(encoding="utf-8"))
    process = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "process_one")
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"build_diverse_title", "build_news_headline"} for n in ast.walk(process))
    publish = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "wp_post")
    review = next(n for n in ast.walk(publish) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "require_editorial_approval")
    writes = [n.lineno for n in ast.walk(publish) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "post"]
    assert review.lineno < min(writes)
    for name in ["daily-network-publish.yml", "newsrooms-daily-publisher.yml"]:
        workflow = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert 'CLAUDE_ENABLED: "false"' in workflow
        assert 'AI_TEXT_PROVIDER: "openai"' in workflow
        assert 'OPENAI_MODEL: "gpt-5-mini"' in workflow
