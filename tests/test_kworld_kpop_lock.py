from scripts.queue_blogger_rewrite import KPOP_SITE_ID, is_kpop_source


def _post(title: str, body: str = "") -> dict:
    return {
        "title": {"rendered": title},
        "content": {"rendered": body},
    }


def test_kworld_kpop_source_lock_accepts_only_kpop_topics():
    assert KPOP_SITE_ID == "blogger_kworld365_kpop"
    assert is_kpop_source(_post("BTS comeback schedule and album details"))
    assert is_kpop_source(_post("Concert ticket guide", "<p>K-pop fandom safety</p>"))
    assert not is_kpop_source(_post("Seoul apartment rental contract checklist"))


def test_kworld_kpop_daily_policy_is_visible_in_control_room():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    template = (root / "control_center/templates/index.html").read_text(encoding="utf-8")
    assert "K-pop 전문 · 매일 1회" in template
    assert "K-pop과 무관한 원문을 차단" in (root / "scripts/queue_blogger_rewrite.py").read_text(encoding="utf-8")
