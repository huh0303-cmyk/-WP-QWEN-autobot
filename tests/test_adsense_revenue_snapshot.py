from scripts.adsense_revenue_snapshot import parse_domain_report


def test_parse_domain_report_keeps_only_real_cumulative_amounts():
    payload = {
        "rows": [
            {"cells": [{"value": "www.example.com"}, {"value": "20.04"}]},
            {"cells": [{"value": "small.example"}, {"value": "1.3"}]},
            {"cells": [{"value": "bad.example"}, {"value": "not-a-number"}]},
        ]
    }

    assert parse_domain_report(payload) == {"example.com": 20.04, "small.example": 1.3}
