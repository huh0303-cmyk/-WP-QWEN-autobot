import unittest
from scripts.audit_youtube15 import audit, PLAYLISTS, LANGUAGES

class AuditTest(unittest.TestCase):
 def test_scope(self):
  self.assertEqual(len(PLAYLISTS),5)
  self.assertEqual(len(LANGUAGES),10)
 def test_missing_workflow_is_detected(self):
  problems=audit()
  self.assertTrue(any('registered workflow missing' in p for p in problems),problems)
if __name__=='__main__': unittest.main()
