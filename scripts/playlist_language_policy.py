"""Four-track blocks preserve the owner-approved 50/25/25 language split."""
import random

def romantic_languages(count, rng=None):
    rng = rng or random
    result = []
    while len(result) < count:
        block = ['french', 'japanese', 'spanish', 'italian']
        rng.shuffle(block)
        result.extend(block)
    return result[:count]

LANGUAGE_TAGS = {'french': ('[fr]', 'french', '불어', '프랑스어'),
                 'japanese': ('[ja]', 'japanese', '일본어'),
                 'spanish': ('[es]', 'spanish', '스페인어'),
                 'italian': ('[it]', 'italian', '이탈리아어'),
                 'korean': ('[ko]', 'korean', '한국어')}

def select_bank_tracks(tracks, channel):
    tracks = list({track['id']: track for track in tracks}.values())
    random.shuffle(tracks)
    if channel == 'globalmusic':
        groups = {language: [t for t in tracks if any(tag in t['name'].lower() for tag in LANGUAGE_TAGS[language])]
                  for language in ('french','japanese','spanish','italian')}
        count = min(5, *(len(group) for group in groups.values()))
        if not count:
            missing = [language for language, group in groups.items() if not group]
            raise RuntimeError('WAITING_ASSETS: approved vocal tracks missing for ' + ', '.join(missing))
        return [groups[language].pop() for language in romantic_languages(count * 4)]
    if channel == 'kpop':
        tracks = [t for t in tracks if any(tag in t['name'].lower() for tag in LANGUAGE_TAGS['korean'])]
    if not tracks:
        raise RuntimeError('WAITING_ASSETS: no approved matching audio for ' + channel)
    return tracks[:20]
