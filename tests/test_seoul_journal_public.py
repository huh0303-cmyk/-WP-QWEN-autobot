import datetime,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from seoul_journal_slot_gate import due,KST
from seoul_journal_public_daily import extract
class PublicJournalTests(unittest.TestCase):
    def test_thirty_dates_exactly_three_slot_windows(self):
        for day in range(1,29):
            groups={}
            for minute in range(1440):
                now=datetime.datetime(2026,11,day,minute//60,minute%60,tzinfo=KST)
                slot,category,selected=due(now)
                if slot!="none": groups.setdefault(slot,set()).add(selected)
            self.assertEqual(set(groups),{"morning","midday","evening"})
            self.assertTrue(all(len(x)==1 for x in groups.values()))
    def test_reject_cross_host_before_request(self):
        with self.assertRaises(RuntimeError): extract("https://naver.com.evil.example/report")
    def article(self,title):
        stamp=datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        return '<h2 id="title_area">'+title+'</h2><div id="dic_area">'+"검증 가능한 기사 본문 "*80+'</div><span data-date-time="'+stamp+'"></span>'
    def test_non_korean_series_sports_rejected(self):
        from unittest.mock import Mock
        response=Mock(text=self.article("KBO 정규리그 야구 경기 소식"))
        with patch("seoul_journal_public_daily.requests.get",return_value=response):
            with self.assertRaisesRegex(RuntimeError,"Korean Series"): extract("https://n.news.naver.com/mnews/article/001/123")
    def test_korean_series_eligible(self):
        from unittest.mock import Mock
        response=Mock(text=self.article("한국시리즈 야구 우승 관련 소식"))
        with patch("seoul_journal_public_daily.requests.get",return_value=response):
            self.assertEqual(extract("https://n.news.naver.com/mnews/article/001/123")[0],"한국시리즈 야구 우승 관련 소식")
if __name__=="__main__": unittest.main()
