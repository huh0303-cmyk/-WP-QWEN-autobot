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
   offers.append({"slot":slot["slot"],"provider":"coupang_partners","category":slot["category"],"title":slot["slot"],"url":"https://link.coupang.com/"+slot["slot"],"image_url":"https://img.example/"+slot["slot"]+".jpg","affiliate_link_verified":True,"image_rights_verified":True,"keywords":["travel"]})
  return routing,offers
 def test_exactly_ten_coupang_cards_and_five_categories(self):
  routing,offers=self.fixture()
  chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  self.assertEqual(len(chosen),10)
  self.assertEqual({x["provider"] for x in chosen},{"coupang_partners"})
  self.assertEqual({c:sum(x["category"]==c for x in chosen) for c in ["beauty","electronics","health_functional_foods","korea_travel_packages","korea_hotels"]},{c:2 for c in ["beauty","electronics","health_functional_foods","korea_travel_packages","korea_hotels"]})
 def test_wrong_provider_is_rejected(self):
  routing,offers=self.fixture()
  offers[0]["provider"]="wrong"
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_unverified_image_or_tracking_link_is_rejected(self):
  routing,offers=self.fixture()
  offers[0]["image_rights_verified"]=False
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_header_button_gate_and_coupang_only_cards(self):
  labels={"coupang_partners":"Coupang Partners","olive_young_global":"Olive Young","trip_com":"Trip.com"}
  buttons=[{"provider":p,"label":labels[p],"affiliate_url":"https://track.example/"+p,"verified":True} for p in ["coupang_partners","olive_young_global","trip_com"]]
  offers=[{"title":"Example","url":"https://link.coupang.com/a","image_url":"https://img.example/a.jpg","category":"beauty"}]
  block=runner.build_block(offers,buttons)
  self.assertIn("Coupang Partners",block)
  self.assertIn("Olive Young",block)
  self.assertIn("Trip.com",block)
  self.assertIn("???? ????",block)
  with self.assertRaises(ValueError): runner.build_block(offers,buttons[:2])
if __name__=="__main__": unittest.main()
