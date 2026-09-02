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
