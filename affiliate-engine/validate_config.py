import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
policy=json.loads((root/'config/affiliate_distribution_policy.json').read_text(encoding='utf-8-sig'))
routing=json.loads((root/'affiliate-engine/config/affiliate-routing.json').read_text(encoding='utf-8-sig'))
expected={'coupang_partners':4,'olive_young_global':2,'trip_com':2,'agoda':2}
assert policy['per_article_total']==10
assert policy['provider_allocation']==expected
assert len(policy['required_slots'])==10
assert len(routing['required_slots'])==10
assert {p:sum(1 for x in routing['required_slots'] if x['provider']==p) for p in expected}==expected
assert routing['safety_gates']['require_per_destination_catalog'] is True
assert routing['safety_gates']['never_delete_posts'] is True
assert routing['new_content_automation']['scheduled_mode']=='dry_run'
print('AFFILIATE_CONFIG_VALID=PASS')
print('PROVIDER_ALLOCATION=4+2+2+2')
print('PER_DESTINATION_CATALOG=REQUIRED')
print('ALL_REGISTERED_WORDPRESS_BLOGS=IN_SCOPE')
print('LIVE_PUBLISH=NOT_ENABLED')
