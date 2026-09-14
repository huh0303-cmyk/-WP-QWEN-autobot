import pytest
from automation_hub.editorial_language_policy import body_cliches, title_cliches


@pytest.mark.parametrize("title", [
    "Unlock Your Korea Career", "The Ultimate Guide to Seoul", "A Comprehensive Guide to Visa Rules",
    "Discover the Power of Korean Skincare", "Navigate the Complexities of Tax", "Your Path to Korea",
    "Mastering the Art of Investing", "A Game-Changer for Expats", "Everything You Need to Know About TOPIK",
    "Korea Visa Secrets Revealed", "The Future of K-Beauty", "한국 보험 완벽 가이드", "지원금 총정리",
])
def test_mass_produced_title_formulas_are_blocked(title):
    assert title_cliches(title)


@pytest.mark.parametrize("text", [
    "In today's fast-paced world, readers need help.", "Let's delve into the details.",
    "Embark on a journey through Korea.", "Korea is a tapestry of experiences.",
    "In the realm of finance, rules matter.", "Look no further for the answer.",
    "Whether you're a seasoned traveler or a beginner.", "Elevate your experience today.",
    "It's important to note that rules change.", "In conclusion, check the source.",
])
def test_mass_produced_body_fillers_require_rewrite(text):
    assert body_cliches(text)
