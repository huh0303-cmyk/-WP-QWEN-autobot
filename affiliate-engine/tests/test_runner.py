import importlib.util, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUNNER_PATH=Path(__file__).resolve().parents[1]/"runner.py"
SPEC=importlib.util.spec_from_file_location("affiliate_runner",RUNNER_PATH)
runner=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runner)
class AffiliatePolicyTests(unittest.TestCase):
 def fixture(self):
  routing=json.loads((ROOT/"affiliate-engine/config/affiliate-routing.json").read_text(encoding="utf-8-sig"))
  offers=[]
  for slot in routing["required_slots"]:
   offers.append({"slot":slot["slot"],"provider":"coupang_partners","category":"travel","title":slot["slot"],"url":"https://link.coupang.com/"+slot["slot"],"image_url":"https://img.example/"+slot["slot"]+".jpg","affiliate_link_verified":True,"image_rights_verified":True})
  return routing,offers
 def buttons(self):
  labels={"coupang_partners":"Coupang Partners","olive_young_global":"Olive Young","trip_com":"Trip.com"}
  return [{"provider":p,"label":labels[p],"affiliate_url":"https://track.example/"+p,"verified":True} for p in labels]
 def categories(self):
  return [{"key":k,"label":k,"affiliate_url":"https://trip.example/"+k,"verified":True} for k in ["hotels","flights","tours_and_packages"]]
 def test_exactly_ten_coupang_cards_without_fixed_category_quota(self):
  routing,offers=self.fixture()
  chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  self.assertEqual(len(chosen),10)
  self.assertEqual({x["provider"] for x in chosen},{"coupang_partners"})
  self.assertEqual(len({x["url"] for x in chosen}),10)
 def test_wrong_provider_is_rejected(self):
  routing,offers=self.fixture(); offers[0]["provider"]="wrong"
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_unverified_image_or_tracking_link_is_rejected(self):
  routing,offers=self.fixture(); offers[0]["image_rights_verified"]=False
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_header_and_trip_category_links_are_rendered(self):
  routing,offers=self.fixture()
  chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  block=runner.build_block(chosen,self.buttons(),self.categories())
  self.assertEqual(block.count('<article class="london-affiliate-card">'),10)
  self.assertIn("Coupang Partners",block); self.assertIn("Olive Young",block); self.assertIn("Trip.com",block)
  self.assertIn("hotels",block); self.assertIn("flights",block); self.assertIn("tours_and_packages",block)
 def test_agoda_or_missing_trip_category_is_rejected(self):
  routing,offers=self.fixture(); chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  with self.assertRaises(ValueError): runner.build_block(chosen,self.buttons(),self.categories()[:2])
if __name__=="__main__": unittest.main()
