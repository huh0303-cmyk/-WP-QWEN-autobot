import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from core_metrics_header import publication_counts, header_summary
from core_metrics_report import report_html


def test_kst_boundary_and_same_time_comparison():
    posts=[{"link":"https://s/a","date_gmt":"2026-09-10T15:00:00"},
           {"link":"https://s/b","date_gmt":"2026-09-10T22:01:00"},
           {"link":"https://s/c","date_gmt":"2026-09-09T17:00:00"}]
    assert publication_counts(posts,"2026-09-11T07:00:00+09:00","date_gmt") == {"published_today":1,"published_previous_same_time":1}


def test_missing_publication_date_is_not_zero():
    assert publication_counts([{"url":"https://s/a"}],"2026-09-11T07:00:00+09:00","published")["published_today"] is None
    rows=[{"published_today":2,"published_previous_same_time":1},{}]
    result=header_summary(rows,"2026-09-11T07:00:00+09:00",{})
    assert result["published_today"] is None and result["confirmed_published_today"] == 2


def test_estimated_reservation_cannot_be_reported_as_total_cost():
    result=header_summary([{"published_today":2,"published_previous_same_time":1}],"2026-09-11T07:00:00+09:00",{"calls":[{"at":"2026-09-11T06:00:00+09:00","amount_usd":0.03}]})
    assert result["published_today"] == 2 and result["published_delta"] == 1
    assert result["api_cost_total"] is None and result["api_cost_delta"] is None
    assert result["recorded_estimate_usd"] == 0.03
    rendered=report_html({"generated_at":"2026-09-11T07:00:00+09:00","records":[],"daily_header":result})
    header=rendered.split('class="metrics-reference-time"')[1].split('</p>')[0]
    assert '당일 총발행 2건' in header and 'API 총비용 미확인' in header
    assert '#1d4ed8' in header


def test_duplicate_urls_do_not_inflate_publication_count():
    post={"url":"https://s/a","published":"2026-09-11T01:00:00+09:00"}
    assert publication_counts([post,post],"2026-09-11T07:00:00+09:00","published")["published_today"] is None
