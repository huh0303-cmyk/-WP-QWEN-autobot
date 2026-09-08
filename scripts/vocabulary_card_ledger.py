"""Offline vocabulary schedule and receipt ledger. No external publication calls.

One durable SQLite database is required for the entire series. Never reconstruct
counts from ephemeral Actions caches. Adapters must verify public visibility and
target identity before recording a receipt. Partial fanout retries keep lesson_id.
"""
import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'vocabulary_cards.json'


def daily_schedule(day, config):
    """Stable random minute in each inclusive window; retries never redraw."""
    date = datetime.strptime(day, '%Y-%m-%d').replace(tzinfo=KST)
    result = {}
    for slot, (start, end) in config['windows'].items():
        def minutes(value):
            h, m = map(int, value.split(':'))
            return h * 60 + m
        low, high = minutes(start), minutes(end)
        if not 0 <= low <= high < 1440:
            raise ValueError('Invalid same-day posting window')
        digest = hashlib.sha256(f"{config['schedule_seed']}:{day}:{slot}".encode()).digest()
        minute = low + int.from_bytes(digest, 'big') % (high - low + 1)
        result[slot] = (date + timedelta(minutes=minute)).isoformat()
    return result


class Ledger:
    def __init__(self, path, config):
        self.config = config
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS lessons (
            id TEXT PRIMARY KEY, slot_id TEXT NOT NULL, brand TEXT NOT NULL,
            language TEXT NOT NULL, word_id TEXT NOT NULL, payload TEXT NOT NULL,
            UNIQUE(slot_id, brand));
          CREATE TABLE IF NOT EXISTS receipts (
            lesson_id TEXT NOT NULL REFERENCES lessons(id), platform TEXT NOT NULL,
            destination TEXT NOT NULL, remote_id TEXT NOT NULL, url TEXT NOT NULL,
            PRIMARY KEY(lesson_id,platform));
          CREATE TABLE IF NOT EXISTS learned (
            ordinal INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL,
            word_id TEXT NOT NULL, lesson_id TEXT NOT NULL, UNIQUE(language,word_id));
          CREATE TABLE IF NOT EXISTS quizzes (
            id TEXT PRIMARY KEY, language TEXT NOT NULL, batch INTEGER NOT NULL,
            lesson_ids TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            UNIQUE(language,batch));
        ''')

    def next_language(self):
        rotation = self.config['brands']['LANGUAGE']
        count = self.db.execute('''SELECT COUNT(*) FROM lessons l WHERE brand='LANGUAGE'
            AND EXISTS(SELECT 1 FROM receipts r WHERE r.lesson_id=l.id)''').fetchone()[0]
        return rotation[count % len(rotation)]

    def prepare(self, day, slot, brand, word_id, word, sentence, meaning,
                sentence_meaning, image_path):
        if slot not in self.config['windows'] or brand not in self.config['brands']:
            raise ValueError('Unknown slot or brand')
        if not all([word_id, word, sentence, meaning, sentence_meaning, image_path]):
            raise ValueError('Word, sentence, explanations and matching image are required')
        # One unresolved first publication per brand prevents rotation races.
        slot_id = f'{day}:{slot}'
        lesson_id = f'{slot_id}:{brand}'
        existing = self.db.execute('SELECT payload FROM lessons WHERE id=?', (lesson_id,)).fetchone()
        if existing:
            old = json.loads(existing[0])
            if (old['word_id'],old['word'],old['sentence'],old['meaning'],old['sentence_meaning'],old['image_path']) != (word_id,word,sentence,meaning,sentence_meaning,image_path):
                raise ValueError('A prepared lesson is immutable; reconcile instead of replacing it')
            return old
        pending = self.db.execute('''SELECT id FROM lessons l WHERE brand=?
            AND NOT EXISTS(SELECT 1 FROM receipts r WHERE r.lesson_id=l.id)''', (brand,)).fetchone()
        if pending:
            raise ValueError('An earlier lesson still needs publication or reconciliation')
        language = self.next_language() if brand == 'LANGUAGE' else self.config['brands'][brand]
        if self.db.execute('SELECT 1 FROM learned WHERE language=? AND word_id=?',(language,word_id)).fetchone():
            raise ValueError('Choose a new word; reviews belong to the quiz queue')
        payload = dict(id=lesson_id,brand=brand,language=language,word_id=word_id,
            word=word,sentence=sentence,meaning=meaning,sentence_meaning=sentence_meaning,
            image_path=image_path,explanation_language=self.config['explanation_languages'][language],
            scheduled_at=daily_schedule(day,self.config)[slot],word_repetitions=5,sentence_repetitions=5,
            platforms=self.config['platforms'],highlight_word=True,bounce=True)
        with self.db:
            self.db.execute('INSERT INTO lessons VALUES(?,?,?,?,?,?)',
                (lesson_id,slot_id,brand,language,word_id,json.dumps(payload,ensure_ascii=False)))
        return payload

    def record_publication(self, lesson_id, platform, destination, remote_id, url,
                           verified_public=False):
        if not verified_public or not remote_id or not url.startswith('https://'):
            raise ValueError('Only verified public posts with receipts can count')
        if platform not in self.config['platforms']:
            raise ValueError('Unknown platform')
        lesson = self.db.execute('SELECT * FROM lessons WHERE id=?',(lesson_id,)).fetchone()
        if not lesson:
            raise ValueError('Unknown lesson')
        expected = self.config['destinations'].get(platform,{}).get(lesson['brand'])
        if not expected or destination != expected:
            raise ValueError('Unconfigured or mismatched destination')
        with self.db:
            prior = self.db.execute('SELECT * FROM receipts WHERE lesson_id=? AND platform=?',
                (lesson_id,platform)).fetchone()
            if prior:
                if (prior['destination'],prior['remote_id']) != (destination,remote_id):
                    raise ValueError('Conflicting receipt; possible duplicate post')
                return
            self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?)',
                (lesson_id,platform,destination,remote_id,url))
            self.db.execute('INSERT OR IGNORE INTO learned(language,word_id,lesson_id) VALUES(?,?,?)',
                (lesson['language'],lesson['word_id'],lesson_id))
            rows = self.db.execute('SELECT lesson_id FROM learned WHERE language=? ORDER BY ordinal',
                (lesson['language'],)).fetchall()
            size = self.config['quiz_every_unique_words']
            for batch in range(1,len(rows)//size+1):
                ids = [row[0] for row in rows[(batch-1)*size:batch*size]]
                self.db.execute('INSERT OR IGNORE INTO quizzes(id,language,batch,lesson_ids) VALUES(?,?,?,?)',
                    (f"quiz:{lesson['language']}:{batch:04d}",lesson['language'],batch,json.dumps(ids)))

    def pending_quizzes(self):
        quizzes=[]
        for row in self.db.execute("SELECT * FROM quizzes WHERE status='pending' ORDER BY id"):
            questions=[]
            for i, lesson_id in enumerate(json.loads(row['lesson_ids']),1):
                payload=json.loads(self.db.execute('SELECT payload FROM lessons WHERE id=?',(lesson_id,)).fetchone()[0])
                questions.append(dict(number=i,image_path=payload['image_path'],meaning=payload['meaning'],
                    answer=payload['word'],sentence=payload['sentence'],sentence_meaning=payload['sentence_meaning'],
                    reveal_after_seconds=3,answer_repetitions=1))
            quizzes.append(dict(id=row['id'],language=row['language'],questions=questions,
                explanation_language=self.config['explanation_languages'][row['language']],
                platforms=self.config['platforms'],status='pending_render'))
        return quizzes

    def missing_deliveries(self):
        result=[]
        for row in self.db.execute('SELECT * FROM lessons ORDER BY id'):
            done={r[0] for r in self.db.execute('SELECT platform FROM receipts WHERE lesson_id=?',(row['id'],))}
            for platform in self.config['platforms']:
                if platform not in done:
                    target=self.config['destinations'].get(platform,{}).get(row['brand'])
                    result.append(dict(lesson_id=row['id'],platform=platform,destination=target,
                        status='needs_publication' if target else 'needs_account_mapping'))
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',required=True)
    parser.add_argument('--config',type=Path,default=CONFIG)
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    print(json.dumps({'date':args.date,'timezone':'Asia/Seoul','schedule':daily_schedule(args.date,config),
        'cards_per_slot':3,'platforms':config['platforms'],'publishing_enabled':config['enabled']},indent=2))

if __name__=='__main__':main()
