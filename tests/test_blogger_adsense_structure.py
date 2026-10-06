import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from blogger_adsense_structure import structure_issues, source_link_issues

GOOD = "<p>intro</p>" + "<h2>Key takeaways</h2><ul><li>a</li></ul>" + "".join(f"<h2>S{i}</h2><p>{'word ' * 220}</p>" for i in range(5)) \
    + "<h2>Frequently asked questions</h2><p>q</p><h2>Before you decide</h2><ul><li><a href='https://www.gov.kr/'>FSS</a></li><li><a href='https://www.korea.kr/'>NHIS</a></li></ul><p><em>Informational only, not professional advice; consult a qualified professional.</em></p>"


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


def test_source_gate_requires_two_official_homepages():
    assert source_link_issues('<a href="https://www.kdca.go.kr/">a</a><a href="https://www.mohw.go.kr/">b</a>', "건강") == []
    assert source_link_issues('<a href="https://www.kdca.go.kr/">a</a>', "건강")


def test_source_gate_rejects_deep_links_and_other_sites():
    iss = source_link_issues('<a href="https://www.kdca.go.kr/a/b">a</a><a href="https://blog.example.com/">b</a><a href="https://www.mohw.go.kr/">c</a>', "건강")
    assert any("disallowed" in i for i in iss)
