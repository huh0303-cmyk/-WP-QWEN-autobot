from __future__ import annotations
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publish_survival_adjective_shorts import validate_language_asset
from survival_adjective_short import LANGUAGES, channel_map
class SurvivalLanguageGuardTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
  self.folder=self.root/"2026-11-03"/"en"; self.folder.mkdir(parents=True)
  self.video=self.folder/"2026-11-03_en_test-pair.mp4"; self.video.write_bytes(b"test english video bytes")
  profile=LANGUAGES["en"]; channel=channel_map()["en"]
  self.manifest={"date":"2026-11-03","language_code":"en","language_label":profile.label,"channel_id":channel["channel_id"],"voice":profile.voice,"voice_locale":profile.locale,"content_key":"en:test-pair","tags":["content-en-test-pair"],"video_path":str(self.video.resolve()),"video_sha256":hashlib.sha256(self.video.read_bytes()).hexdigest()}
  self.manifest_path=self.folder/"manifest.json"; self.manifest_path.write_text(json.dumps(self.manifest),encoding="utf-8")
 def tearDown(self): self.temp.cleanup()
 def test_valid_english_asset_passes(self):
  code,cid,path=validate_language_asset(self.manifest_path,self.manifest); self.assertEqual(code,"en"); self.assertEqual(cid,self.manifest["channel_id"]); self.assertEqual(path,self.video.resolve())
 def test_japanese_filename_cannot_be_uploaded_as_english(self):
  jp=self.folder/"2026-11-03_ja_test-pair.mp4"; jp.write_bytes(b"japanese asset")
  bad=dict(self.manifest,video_path=str(jp.resolve()),video_sha256=hashlib.sha256(jp.read_bytes()).hexdigest())
  with self.assertRaisesRegex(RuntimeError,"filename does not match language"): validate_language_asset(self.manifest_path,bad)
 def test_wrong_channel_is_rejected(self):
  bad=dict(self.manifest,channel_id="UC"+"0"*22)
  with self.assertRaisesRegex(RuntimeError,"Manifest channel mismatch"): validate_language_asset(self.manifest_path,bad)
 def test_changed_video_bytes_are_rejected(self):
  self.video.write_bytes(b"replaced with different-language content")
  with self.assertRaisesRegex(RuntimeError,"Video bytes changed"): validate_language_asset(self.manifest_path,self.manifest)
if __name__=="__main__": unittest.main()
