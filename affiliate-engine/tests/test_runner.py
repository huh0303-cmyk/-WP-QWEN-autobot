import importlib.util, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUNNER_PATH=Path(__file__).resolve().parents[1]/"runner.py"
SPEC=importlib.util.spec_from_file_location("affiliate_runner",RUNNER_PATH)
runner=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runner)
class AffiliatePolicyTests(unittest.TestCase):
 def test_fixed_provider_mix_and_ten_slots(self):
  routing=json.loads((ROOT/"affiliate-engine/config/affiliate-routing.json").read_text(encoding="utf-8-sig"))
  offers=[]
  for slot in routing["required_slots"]:
   offers.append({"slot":slot["slot"],"provider":slot["provider"],"title":slot["slot"],"url":"https://track.example/"+slot["slot"],"image_url":"https://img.example/"+slot["slot"]+".jpg","affiliate_link_verified":True,"image_rights_verified":True,"keywords":["travel"]})
  chosen=runner.select_offers("Travel guide","travel",routing,"test_site",offers)
  self.assertEqual(len(chosen),10)
  counts={}
  for x in chosen: counts[x["provider"]]=counts.get(x["provider"],0)+1
  self.assertEqual(counts,{"coupang_partners":4,"olive_young_global":2,"trip_com":2,"agoda":2})
 def test_wrong_provider_is_rejected(self):
  routing=json.loads((ROOT/"affiliate-engine/config/affiliate-routing.json").read_text(encoding="utf-8-sig"))
  offers=[{"slot":s["slot"],"provider":"wrong","title":"x","url":"https://track.example/x","image_url":"https://img.example/x.jpg","affiliate_link_verified":True,"image_rights_verified":True,"keywords":["travel"]} for s in routing["required_slots"]]
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_unverified_image_or_tracking_link_is_rejected(self):
  routing=json.loads((ROOT/"affiliate-engine/config/affiliate-routing.json").read_text(encoding="utf-8-sig"))
  offers=[{"slot":s["slot"],"provider":s["provider"],"title":"x","url":"https://track.example/"+s["slot"],"image_url":"https://img.example/x.jpg","affiliate_link_verified":True,"image_rights_verified":True,"keywords":["travel"]} for s in routing["required_slots"]]
  offers[0]["image_rights_verified"]=False
  with self.assertRaises(ValueError): runner.select_offers("Travel guide","travel",routing,"test_site",offers)
 def test_card_html_has_image_and_sponsored_link(self):
  block=runner.build_block([{"title":"Example","url":"https://track.example/a","image_url":"https://img.example/a.jpg"}])
  self.assertIn(runner.MARKER,block); self.assertIn("<img",block); self.assertIn('rel="sponsored nofollow noopener"',block)
if __name__=="__main__": unittest.main()
