import importlib.util, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUNNER_PATH=Path(__file__).resolve().parents[1]/"runner.py"
SPEC=importlib.util.spec_from_file_location("affiliate_runner",RUNNER_PATH)
runner=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runner)
MIX={"health_functional_foods":5,"k_beauty_skincare":5}
POOL={"health_functional_foods":5,"k_beauty_skincare":5}
class AffiliatePolicyTests(unittest.TestCase):
 def fixture(self):
  routing=json.loads((ROOT/"affiliate-engine/config/affiliate-routing.json").read_text(encoding="utf-8-sig"))
  offers=[]
  for cat,count in POOL.items():
   for i in range(count):
    offers.append({"provider":"coupang_partners","category":cat,"title":f"{cat} product {i}","url":f"https://link.coupang.com/{cat}/{i}","image_url":f"https://img.example/{cat}/{i}.jpg","affiliate_link_verified":True,"image_rights_verified":True})
  return routing,offers
 def buttons(self):
  labels={"coupang_partners":"Coupang Partners","trip_com":"Trip.com","olive_young_global":"OLIVE YOUNG"}
  return [{"provider":p,"label":labels[p],"affiliate_url":"https://track.example/"+p,"verified":True} for p in ("coupang_partners","trip_com","olive_young_global")]
 def test_exact_fixed_mix_and_ten_unique_coupang_cards(self):
  routing,offers=self.fixture(); chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  self.assertEqual(len(chosen),10); self.assertEqual({x["provider"] for x in chosen},{"coupang_partners"})
  self.assertEqual({k:sum(1 for x in chosen if x["category"]==k) for k in MIX},MIX)
  self.assertEqual(len({x["url"] for x in chosen}),10)
 def test_fixed_ten_item_set_is_reused(self):
  routing,offers=self.fixture()
  a=runner.select_offers("Article A","content A",routing,"test_site",offers)
  b=runner.select_offers("Article B","content B",routing,"test_site",offers)
  self.assertEqual({x["url"] for x in a},{x["url"] for x in b})
 def test_short_category_pool_is_blocked(self):
  routing,offers=self.fixture(); offers=[x for x in offers if not (x["category"]=="health_functional_foods" and x["title"].endswith("4"))]
  with self.assertRaisesRegex(ValueError,"insufficient_unique_offers|missing_verified_offer"):
   runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_wrong_provider_is_rejected(self):
  routing,offers=self.fixture(); offers[0]["provider"]="wrong"
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_unverified_image_or_tracking_link_is_rejected(self):
  routing,offers=self.fixture(); offers[0]["image_rights_verified"]=False
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_header_and_brand_colours_render_without_trip_text_row(self):
  routing,offers=self.fixture(); chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  block=runner.build_block(chosen,self.buttons())
  self.assertEqual(block.count('<article class="london-affiliate-card">'),10)
  self.assertIn('background:var(--brand-color)',block); self.assertIn('Coupang Partners',block); self.assertIn('OLIVE YOUNG',block); self.assertIn('Trip.com',block)
  self.assertNotIn('london-trip-category-buttons',block); self.assertNotIn('Trip.com &middot;',block)
 def test_wrong_category_mix_rejected_at_render(self):
  routing,offers=self.fixture(); chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  chosen[0]["category"]="hotel_products"
  with self.assertRaisesRegex(ValueError,"product_category_mix_mismatch"):
   runner.build_block(chosen,self.buttons())
if __name__=="__main__": unittest.main()
