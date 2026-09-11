from scripts.replicate_image_provider import build_editorial_prompt


def test_blog_image_prompt_forbids_all_visible_and_fake_text():
    prompt = build_editorial_prompt("Korea housing consultation", "real estate").lower()
    for phrase in (
        "no text anywhere",
        "documents",
        "screens",
        "illegible pseudo-text",
        "fake hangul",
        "fake chinese/japanese",
        "random glyphs",
    ):
        assert phrase in prompt


def test_newsroom_prompt_cannot_fake_documentary_evidence():
    prompt = build_editorial_prompt(
        "breaking political event",
        "NEWS ILLUSTRATION ONLY — politics",
    ).lower()
    assert "conceptual illustration" in prompt
    assert "not evidence of the real event" in prompt
    assert "not a photograph" in prompt
