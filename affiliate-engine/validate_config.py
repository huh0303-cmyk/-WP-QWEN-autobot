import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
policy=json.loads((root/'config/affiliate_distribution_policy.json').read_text(encoding='utf-8-sig'))
routing=json.loads((root/'affiliate-engine/config/affiliate-routing.json').read_text(encoding='utf-8-sig'))
expected={'coupang_partners':10}
assert policy['per_article_total']==10
assert policy['provider_allocation']==expected
assert len(policy['required_slots'])==10
assert len(routing['required_slots'])==10
assert {p:sum(1 for x in routing['required_slots'] if x['provider']==p) for p in expected}==expected
assert [x['provider'] for x in routing['top_buttons']]==['coupang_partners','olive_young_global','trip_com']
assert routing['affiliate_programs']['agoda']['enabled'] is False
assert routing['safety_gates']['require_per_destination_catalog'] is True
assert routing['safety_gates']['never_delete_posts'] is True
assert routing['safety_gates']['provider_card_mix']=='coupang_only_10'
assert routing['new_content_automation']['scheduled_mode']=='dry_run'
print('AFFILIATE_CONFIG_VALID=PASS')
print('HEADER_BUTTONS=COUPANG+OLIVEYOUNG+TRIPCOM')
print('PRODUCT_CARDS=10_COUPANG_ONLY')
print('AGODA=DISABLED')
print('PER_DESTINATION_CATALOG=REQUIRED')
print('LIVE_PUBLISH=NOT_ENABLED')
