import unittest
from scripts.audit_youtube15 import audit, PLAYLISTS, LANGUAGES

class AuditTest(unittest.TestCase):
 def test_scope(self):
  self.assertEqual(len(PLAYLISTS),5)
  self.assertEqual(len(LANGUAGES),10)
 def test_workflow_mapping_is_valid(self):
  self.assertEqual(audit(),[])
if __name__=='__main__': unittest.main()
