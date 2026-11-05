import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
policy=json.loads((root/'config/affiliate_distribution_policy.json').read_text(encoding='utf-8-sig'))
shared=json.loads((root/'config/affiliate/london-shared-policy.json').read_text(encoding='utf-8-sig'))
routing=json.loads((root/'affiliate-engine/config/affiliate-routing.json').read_text(encoding='utf-8-sig'))
expected={'health_functional_foods':5,'k_beauty_skincare':5}
pool={'health_functional_foods':5,'k_beauty_skincare':5}
assert policy['policy_version']=='6.0.0'
assert policy['per_article_total']==10 and policy['provider_allocation']=={'coupang_partners':10}
assert len(policy['required_slots'])==10
assert {k:sum(1 for x in policy['required_slots'] if x['category']==k) for k in expected}==expected
assert {k:sum(1 for x in routing['required_slots'] if x['category']==k) for k in expected}==expected
assert routing['version']=='6.0.0'
assert routing['selection_policy']['pool_category_counts']==pool
assert routing['selection_policy']['per_article_category_counts']==expected
assert routing['selection_policy']['randomize_per_article'] is False
assert [x['provider'] for x in routing['top_buttons']]==['coupang_partners','trip_com','olive_young_global']
assert [x['brand_color'] for x in routing['top_buttons']]==['orange','blue','green']
assert routing['affiliate_programs']['agoda']['enabled'] is False
assert shared['product_cards']['category_count']==expected
assert shared['header_buttons']==['coupang_partners','trip_com','olive_young_global']
assert policy['header_design']['no_extra_trip_category_text_link_row_below_buttons'] is True
assert policy['header_design']['order']==['coupang_partners','trip_com','olive_young_global']
print('AFFILIATE_CONFIG_VALID=PASS')
print('POLICY=v6.0.0_LOCKED')
print('HEADER=COUPANG_ORANGE+TRIPCOM_BLUE+OLIVEYOUNG_GREEN')
print('PER_ARTICLE=HEALTH5+KBEAUTY_SKINCARE5')
print('SITE_POOL=10 (HEALTH5+KBEAUTY5)')
print('FIXED_TEN_PER_DESTINATION=REQUIRED')
print('AGODA=DISABLED')
