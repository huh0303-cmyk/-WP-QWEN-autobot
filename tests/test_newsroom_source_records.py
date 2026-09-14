from scripts.news_source_registry import get_enabled_rss_source_records


def test_newsroom_source_records_keep_rights_and_category_metadata():
    for language in ("ko", "en"):
        records = get_enabled_rss_source_records(language)
        assert records
        for record in records:
            assert record["feed"].startswith("https://")
            assert record["category"]
            assert record["license"]
            assert record["license_url"].startswith("https://")
            assert record["use"] in {
                "headline_fact_lead",
                "headline_fact_lead_translate",
                "primary_fact_lead",
                "primary_fact_lead_translate",
            }
