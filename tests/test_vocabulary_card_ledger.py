import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.vocabulary_card_ledger import Ledger, daily_schedule, CONFIG
from control_center.vocabulary import vocabulary_status

class VocabularyTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(CONFIG.read_text(encoding='utf-8'))
        self.tmp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.tmp.name)/'ledger.sqlite')
        self.ledger=Ledger(self.path,self.config)
    def tearDown(self):
        self.ledger.db.close();self.tmp.cleanup()
    def prepare(self,i,brand='TOPIK'):
        day=(datetime(2026,9,9)+timedelta(days=i//2)).date().isoformat()
        return self.ledger.prepare(day,'morning' if i%2==0 else 'evening',brand,
            f'word-{i}',f'word{i}',f'sentence {i}',f'meaning{i}',f'meaning sentence{i}',f'image-{i}.png')
    def publish(self,lesson,platform='facebook'):
        self.ledger.record_publication(lesson['id'],platform,
            self.config['destinations'][platform][lesson['brand']],f"post-{lesson['id']}",
            'https://example.com/public-post',verified_public=True)
    def test_random_windows_are_stable_and_vary(self):
        times=[]
        for i in range(40):
            day=(datetime(2026,9,9)+timedelta(days=i)).date().isoformat()
            result=daily_schedule(day,self.config)
            self.assertEqual(result,daily_schedule(day,self.config))
            for slot,stamp in result.items():
                value=datetime.fromisoformat(stamp)
                low,high=(180,420) if slot=='morning' else (840,1080)
                self.assertTrue(low<=value.hour*60+value.minute<=high)
                self.assertEqual(value.utcoffset(),timedelta(hours=9))
            times.append(result['morning'][11:16])
        self.assertGreater(len(set(times)),1)
    def test_tenth_unique_word_produces_one_quiz(self):
        for i in range(10):
            lesson=self.prepare(i);self.publish(lesson)
            self.publish(lesson)  # retry must not increment progress
            self.publish(lesson,'youtube')  # cross-platform duplication must not count
            self.assertEqual(len(self.ledger.pending_quizzes()),1 if i==9 else 0)
        quiz=self.ledger.pending_quizzes()[0]
        self.assertEqual(len(quiz['questions']),10)
        self.assertEqual(quiz['questions'][0]['answer'],'word0')
        self.assertEqual(quiz['questions'][-1]['answer'],'word9')
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM learned').fetchone()[0],10)
    def test_unverified_or_wrong_account_cannot_count(self):
        lesson=self.prepare(0)
        for verified,target in [(False,'1128119143729384'),(True,'wrong')]:
            with self.assertRaises(ValueError):
                self.ledger.record_publication(lesson['id'],'facebook',target,'id','https://example.com',verified)
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM learned').fetchone()[0],0)
    def test_rotation_changes_only_after_publication(self):
        self.assertEqual(self.ledger.next_language(),'de')
        for i,lang in enumerate(['de','fr','vi','es','de']):
            lesson=self.prepare(i,'LANGUAGE');self.assertEqual(lesson['language'],lang)
            self.assertEqual(self.ledger.next_language(),lang)
            self.publish(lesson)
        self.assertEqual(self.ledger.next_language(),'fr')
    def test_prepared_lesson_survives_restart_and_blocks_race(self):
        original=self.prepare(0,'LANGUAGE')
        self.ledger.db.close();self.ledger=Ledger(self.path,self.config)
        self.assertEqual(self.prepare(0,'LANGUAGE'),original)
        with self.assertRaises(ValueError):self.prepare(1,'LANGUAGE')
    def test_platform_retries_remain_independent(self):
        lesson=self.prepare(0);self.publish(lesson)
        missing=self.ledger.missing_deliveries()
        self.assertEqual({x['platform'] for x in missing},{'youtube','tiktok','instagram','threads'})
    def test_quiz_mode_and_dashboard_are_truthful(self):
        self.assertEqual(self.config['quiz_mode'],'replace_language_card')
        self.assertFalse(self.config['enabled'])
        status=vocabulary_status(CONFIG)
        self.assertFalse(status['enabled'])
        self.assertIsNone(status['published_count'])
        self.assertIsNone(status['actual_cost'])
        self.assertEqual(len(status['accounts']),5)
        self.assertIn('SIS-Language Center',status['accounts'][0]['language'])

if __name__=='__main__':unittest.main()
