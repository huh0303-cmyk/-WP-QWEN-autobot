import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("core_metrics", Path(__file__).resolve().parents[1] / "scripts/core_metrics_report.py")
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def test_old_snapshot_is_not_yesterday():
    history = {"days": {"2026-09-02": {"records": [{"url": "https://example.com", "total_posts": 10}]}}}
    assert metrics.previous_day(history, "2026-09-09") == {}


def test_zero_is_evidence_but_missing_is_not_zero():
    assert metrics.delta(0, 5) == -5
    assert metrics.delta(0, None) is None
    assert metrics.format_metric({"count": 0, "change": 0}, "count", "change") == "0 (+0)"
    assert metrics.format_metric({}, "count", "change") == "미확인"


def test_exact_previous_day_is_used():
    row = {"url": "https://example.com", "total_posts": 10}
    assert metrics.previous_day({"days": {"2026-09-08": {"records": [row]}}}, "2026-09-09") == {row["url"]: row}


def test_visitor_ranking_ties_zero_and_unknown():
    import re
    rows = [dict(platform="wordpress", url="https://" + name + ".com", today_visitors=value)
            for name, value in [("unknown", None), ("zero", 0), ("b", 12), ("a", 12), ("third", 4)]]
    document = metrics.report_html({"generated_at": "2026-09-10", "records": rows})
    rendered = re.findall(r'<tr><td>(.*?)</td><td><a href="(.*?)"', document)
    assert rendered == [("1", "https://a.com"), ("1", "https://b.com"), ("3", "https://third.com"),
                        ("4", "https://zero.com"), ("—", "https://unknown.com")]


def test_report_escapes_untrusted_site_and_errors():
    document = metrics.report_html({"generated_at": "<script>", "records": [
        {"platform": "blogger", "url": 'https://example.com/"<img>', "today_visitors": 1,
         "errors": ["<script>alert(1)</script>"]}]})
    assert "<script>" not in document and "<img>" not in document
    assert "&lt;script&gt;" in document and "&quot;" in document


def test_change_colors_and_prominent_kst_date():
    assert '#1d4ed8' in metrics.format_metric({'n':15,'d':3},'n','d')
    assert '#dc2626' in metrics.format_metric({'n':15,'d':-3},'n','d')
    assert 'color:' not in metrics.format_metric({'n':15,'d':0},'n','d')
    rendered=metrics.report_html({'generated_at':'2026-09-12T07:02:00+09:00','scheduled_for':'2026-09-12T07:00:00+09:00','report_kind':'daily_0700','records':[]})
    assert '2026년 9월 12일 오전 7시 00분 (KST) 기준' in rendered
    assert 'metrics-reference-time' in rendered and '32px' in rendered
