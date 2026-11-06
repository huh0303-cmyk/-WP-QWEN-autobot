import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('meta_account_preflight',ROOT/'scripts'/'meta_account_preflight.py')
mod=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mod)
class MetaFiveAccountPolicyTests(unittest.TestCase):
 def test_exact_five_handles(self):
  d=mod.load_policy(); self.assertEqual([a['handle'] for a in d['accounts']],['seoul_topik','seoul_jisoo','seoul_chris','english_pick1','japanese_pick'])
 def test_ten_platform_connections(self):
  d=mod.load_policy(); self.assertEqual(len(d['accounts'])*len(d['platforms']),10)
 def test_publish_disabled(self):
  d=mod.load_policy(); self.assertFalse(d['authentication']['publish_enabled'])
 def test_missing_credentials_are_reported_and_blocked(self):
  with patch.dict(os.environ, {}, clear=True):
   r=mod.readiness(mod.load_policy())
  self.assertEqual(r['ready_connections'],0)
  self.assertEqual(len(r['missing_secret_names']),10)
  self.assertFalse(r['publish_enabled'])
  self.assertFalse(r['publication_performed'])
if __name__=='__main__': unittest.main()
