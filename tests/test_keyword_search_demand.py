import datetime as dt
import json
from scripts.collect_keyword_search_demand import matching_property, demand_context


def test_blogspot_custom_domain_uses_parent_verified_property():
    assert matching_property('https://skin.k-health365.com', {'sc-domain:k-health365.com'}) == 'sc-domain:k-health365.com'
    assert matching_property('https://k-health365.com.attacker.test', {'sc-domain:k-health365.com'}) is None
    assert matching_property('https://example.blogspot.com', {'sc-domain:k-health365.com'}) is None


def test_unavailable_or_stale_query_data_is_not_presented_as_demand(tmp_path):
    path = tmp_path / 'demand.json'
    value = {'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(), 'period':{},
             'sites':{'https://example.com':{'status':'not_accessible_to_service_account','queries':[]}}}
    path.write_text(json.dumps(value))
    assert 'unavailable' in demand_context('https://example.com', path)
    value['sites']['https://example.com'] = {'status':'available','queries':[{'query':'rail ticket','impressions':42}]}
    path.write_text(json.dumps(value))
    assert 'rail ticket' in demand_context('https://example.com', path)
    assert 'not total market search volume' in demand_context('https://example.com', path)
    value['checked_at'] = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=10)).isoformat()
    path.write_text(json.dumps(value))
    assert 'unavailable' in demand_context('https://example.com', path)
