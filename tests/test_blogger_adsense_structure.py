import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from blogger_adsense_structure import structure_issues

GOOD = "<p>intro</p>" + "<h2>Key takeaways</h2><ul><li>a</li></ul>" + "".join(f"<h2>S{i}</h2><p>{'word ' * 220}</p>" for i in range(5)) \
    + "<h2>Frequently asked questions</h2><p>q</p><h2>Before you decide</h2><p>Check the ministry.</p><p><em>Informational only, not professional advice; consult a qualified professional.</em></p>"


def test_good_passes():
    assert structure_issues(GOOD, "Insurance in Korea", "en") == []


def test_missing_sections_flagged():
    issues = structure_issues("<p>x</p><h2>One</h2>" + "word " * 1000, "Korea travel", "en")
    assert any("key takeaways" in i for i in issues) and any("FAQ" in i for i in issues)


def test_ymyl_requires_disclaimer():
    body = GOOD.replace("<p><em>Informational only, not professional advice; consult a qualified professional.</em></p>", "")
    assert any("YMYL" in i for i in structure_issues(body, "Personal finance in Korea", "en"))
    assert structure_issues(body, "Korea travel", "en") == []


def test_h1_rejected():
    assert "contains <h1>" in structure_issues("<h1>x</h1>" + GOOD, "Korea travel", "en")
