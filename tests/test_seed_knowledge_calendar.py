import datetime as dt
import unittest
from scripts.seed_knowledge_calendar import planned_rows
from scripts.knowledge_channel_cadence import KST

class SeedTest(unittest.TestCase):
 def test_idempotent_and_frequency(self):
  now=dt.datetime(2026,11,9,0,0,tzinfo=KST)
  enabled={'history','nasa','invention','silent_era','retro_reels'}
  rows=planned_rows([],now,enabled)
  self.assertEqual(sum(r[3]=='history' for r in rows),7)
  for c in enabled-{'history'}: self.assertEqual(sum(r[3]==c for r in rows),3)
  existing=[{'key':r[3],'when':dt.datetime.strptime(r[1],'%Y-%m-%d %H:%M KST').replace(tzinfo=KST)} for r in rows]
  self.assertEqual(planned_rows(existing,now,enabled),[])
 def test_no_past(self):
  now=dt.datetime(2026,11,11,23,0,tzinfo=KST)
  self.assertTrue(all(dt.datetime.strptime(r[1],'%Y-%m-%d %H:%M KST').replace(tzinfo=KST)>now for r in planned_rows([],now,{'history'})))
if __name__=='__main__': unittest.main()
