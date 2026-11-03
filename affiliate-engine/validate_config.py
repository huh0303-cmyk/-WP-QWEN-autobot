import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
policy=json.loads((root/'config/affiliate_distribution_policy.json').read_text(encoding='utf-8-sig'))
shared=json.loads((root/'config/affiliate/london-shared-policy.json').read_text(encoding='utf-8-sig'))
routing=json.loads((root/'affiliate-engine/config/affiliate-routing.json').read_text(encoding='utf-8-sig'))
expected={'beauty_cosmetics':2,'laptop':1,'tablet':1,'health_supplements':2,'korea_travel_packages':2,'hotel_products':2}
pool={'beauty_cosmetics':20,'laptop':10,'tablet':10,'health_supplements':20,'korea_travel_packages':20,'hotel_products':20}
assert policy['policy_version']=='5.0.0'
assert policy['per_article_total']==10 and policy['provider_allocation']=={'coupang_partners':10}
assert len(policy['required_slots'])==10
assert {k:sum(1 for x in policy['required_slots'] if x['category']==k) for k in expected}==expected
assert {k:sum(1 for x in routing['required_slots'] if x['category']==k) for k in expected}==expected
assert routing['version']=='5.0.0'
assert routing['selection_policy']['pool_category_counts']==pool
assert [x['provider'] for x in routing['top_buttons']]==['coupang_partners','olive_young_global','trip_com']
assert [x['brand_color'] for x in routing['top_buttons']]==['orange','green','blue']
assert routing['affiliate_programs']['agoda']['enabled'] is False
assert shared['product_cards']['per_article_category_count']==expected
assert shared['product_cards']['pool_category_count']==pool
assert policy['header_design']['no_extra_trip_category_text_link_row_below_buttons'] is True
print('AFFILIATE_CONFIG_VALID=PASS')
print('POLICY=v5.0.0_LOCKED')
print('HEADER=COUPANG_ORANGE+OLIVEYOUNG_GREEN+TRIPCOM_BLUE')
print('PER_ARTICLE=BEAUTY2+LAPTOP1+TABLET1+HEALTH2+TRAVEL_PACKAGE2+HOTEL2')
print('SITE_POOL=100 (20+10+10+20+20+20)')
print('RANDOM_PER_ARTICLE=REQUIRED')
print('AGODA=DISABLED')
