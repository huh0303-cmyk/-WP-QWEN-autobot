import unittest
from history_episode_contract import choose_voice, validate_episode, APPROVED_VOICES


class ContractTests(unittest.TestCase):
    def plan(self):
        return dict(channel_key='history', episode_date='2026-09-06', language='en',
                    voice_name='Brian', date_label='SEPTEMBER 6', date_is_primary=True,
                    rights_review_passed=True, audio_file_verified=True,
                    caption_sync_checked=True, visual_alignment_checked=True,
                    upload_visibility='private', events=[dict(date='1901-09-06',
                    fact_sources=['https://www.loc.gov/'], narration='Reviewed narration',
                    scenes=[dict(kind='archival_video', source='https://www.loc.gov/',
                    rights_basis='Reviewed item', visible_content='Public appearance',
                    narration_excerpt='Public appearance, not the attack')])])

    def test_valid(self):
        self.assertEqual(validate_episode(self.plan()), [])

    def test_no_immediate_repeat(self):
        for previous in APPROVED_VOICES:
            for _ in range(20):
                self.assertNotEqual(previous, choose_voice(previous))

    def test_missing_audio_blocks(self):
        p = self.plan(); p['audio_file_verified'] = False
        self.assertTrue(validate_episode(p))

    def test_wrong_day_blocks(self):
        p = self.plan(); p['events'][0]['date'] = '1901-09-14'
        self.assertTrue(validate_episode(p))

    def test_ascending_blocks(self):
        p = self.plan(); old = dict(p['events'][0], date='1757-09-06')
        p['events'].insert(0, old)
        self.assertTrue(validate_episode(p))

    def test_unapproved_voice_blocks(self):
        p = self.plan(); p['voice_name'] = 'Other'
        self.assertTrue(validate_episode(p))


if __name__ == '__main__':
    unittest.main()
