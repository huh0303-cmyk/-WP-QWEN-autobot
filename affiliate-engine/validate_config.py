import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
policy=json.loads((root/'config/affiliate_distribution_policy.json').read_text(encoding='utf-8-sig'))
shared=json.loads((root/'config/affiliate/london-shared-policy.json').read_text(encoding='utf-8-sig'))
routing=json.loads((root/'affiliate-engine/config/affiliate-routing.json').read_text(encoding='utf-8-sig'))
expected={'health_functional_foods':5,'k_beauty_skincare':5}
pool={'health_functional_foods':5,'k_beauty_skincare':5}
assert policy['policy_version']=='7.0.0'
assert policy['per_article_total']==10 and policy['provider_allocation']=={'coupang_partners':10}
assert len(policy['required_slots'])==10
assert {k:sum(1 for x in policy['required_slots'] if x['category']==k) for k in expected}==expected
assert {k:sum(1 for x in routing['required_slots'] if x['category']==k) for k in expected}==expected
assert routing['version']=='7.0.0'
assert routing['selection_policy']['pool_category_counts']==pool
assert routing['selection_policy']['per_article_category_counts']==expected
assert routing['selection_policy']['randomize_per_article'] is False
assert [x['provider'] for x in routing['top_buttons']]==['coupang_partners','olive_young_global','trip_com']
assert [x['brand_color'] for x in routing['top_buttons']]==['orange','green','blue']
assert routing['affiliate_programs']['agoda']['enabled'] is False
assert shared['product_cards']['category_count']==expected
assert shared['header_buttons']==['coupang_partners','olive_young_global','trip_com']
assert policy['header_design']['no_extra_trip_category_text_link_row_below_buttons'] is True
assert policy['header_design']['order']==['coupang_partners','olive_young_global','trip_com']
assert policy['header_design']['official_logo_image_required'] is True
assert policy['article_placement']['location']=='absolute_article_footer_only'
assert policy['article_placement']['sequence'][0]=='three_official_company_logo_banners_in_one_horizontal_row'
print('AFFILIATE_CONFIG_VALID=PASS')
print('POLICY=v7.0.0_LOCKED')
print('HEADER=COUPANG_ORANGE+OLIVEYOUNG_GREEN+TRIPCOM_BLUE')
print('PER_ARTICLE=HEALTH5+KBEAUTY_SKINCARE5')
print('SITE_POOL=10 (HEALTH5+KBEAUTY5)')
print('UP_TO_10_VERIFIED_PRODUCTS=REQUIRED')
print('AGODA=DISABLED')
