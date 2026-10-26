"""Owner's English title/description requirements for private YouTube uploads."""
import re
import random


def validate_metadata(title, description):
    if not 1 <= len(title.strip()) <= 100:
        raise ValueError('English YouTube title must contain 1–100 characters')
    if not 800 <= len(description.strip()) <= 1200:
        raise ValueError('English description must contain 800–1200 characters; target 1000')
    if re.search(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', title + description):
        raise ValueError('Translate title and description into English before upload')
    words = set(re.findall(r'[a-z]+', description.lower()))
    if len(words & {'the','and','your','you','with','this','for','from','in','of','a','to','is','as'}) < 6:
        raise ValueError('Description needs natural English prose')


_TITLE_FORMS = {
    'globalmusic': [
        'A Little More in Love ☕ {topic}',
        'For Two, With Love — {topic}',
        'When the Cafe Feels Like a Date | {topic}',
        'Soft Kisses & Acoustic Strings — {topic}',
        'Stay a Little Longer 💗 {topic}',
        'A Sweet Evening Together | {topic}',
        'Love Sounds Better Here — {topic}',
        'Your Table for Two: {topic}',
        'The Kind of Love That Feels Like Home | {topic}',
        'Just Us and These Songs — {topic}',
        'A Warm Cup, a Soft Song, and You | {topic}',
        'Little Moments, Big Feelings — {topic}',
    ],
    'kpop': [
        'Korean Acoustic Pop for a Quiet Night | {topic}',
        'A Softer Side of K-Pop — {topic}',
        'Unplugged Hearts: {topic}',
        'Korean Love Songs After Sunset | {topic}',
    ],
    'healing': [
        'Rain on the Leaves | {topic}', 'A Forest Pause — {topic}',
        'Let the River Slow the Day | {topic}', 'Quiet Nature, Clear Mind: {topic}',
    ],
    'starbucks': [
        'The Cafe Is Open ☕ {topic}', 'A Window Seat and Warm Coffee | {topic}',
        'Easy Instrumentals for Slow Mornings — {topic}', 'Coffee, Light, and a Little Calm | {topic}',
    ],
    'mbb': [
        'An Unhurried Hour with the Classics | {topic}', 'Piano, Strings, and Stillness — {topic}',
        'A Quiet Room for Classical Music | {topic}', 'Timeless Pieces for a Gentle Evening — {topic}',
    ],
}


def _unique_title(channel, topic):
    """Create varied, topic-led titles instead of appending the same generic suffix."""
    topic = ' '.join(topic.split()).strip(' |')
    forms = _TITLE_FORMS.get(channel, ['{topic} | A Playlist for the Moment'])
    candidates = [form.format(topic=topic) for form in forms]
    random.shuffle(candidates)
    for title in candidates:
        if len(title) <= 100:
            return title
    # Keep the human-written hook intact and trim only the topic tail if needed.
    form = random.choice(forms)
    room = 100 - len(form.format(topic=''))
    short_topic = topic[:max(1, room)].rsplit(' ', 1)[0]
    return form.format(topic=short_topic).strip(' |—-')[:100]


def playlist_metadata(channel, topic, minutes):
    labels = {'healing': 'Nature Sounds', 'kpop': 'Korean Acoustic Pop',
              'globalmusic': 'Sweet Romantic Songs', 'mbb': 'Classical Music',
              'starbucks': 'Instrumental Cafe Music'}
    angles = {
        'healing': 'Let the sounds of nature become a gentle backdrop to your day. Listen for the small changes in the rain, leaves, and water, and choose a comfortable volume for the space around you.',
        'kpop': 'Make room for Korean pop with an acoustic, unplugged spirit. Listen for the connection between the vocals and the accompaniment, and enjoy the different moods a song can bring to a quiet evening or a familiar daily routine.',
        'globalmusic': 'This playlist is for the lovely little moments shared by two people: lingering over coffee, walking home together, or smiling at a message from someone special. Gentle romantic vocals and acoustic textures keep the mood sweet without making it overly dramatic. Let the songs play while you cook, talk, read, or enjoy a slow evening together.',
        'mbb': 'Spend some time with classical music and the details that reward an unhurried listen. Follow the melodies, notice the changes in expression, and let the music accompany reading, a quiet afternoon, or a comfortable moment away from a busy day.',
        'starbucks': 'Bring a relaxed cafe mood to your desk with instrumental music. Keep it nearby while you read, write, organize your day, or take a coffee break. With no lyrics to follow, you can choose how closely to listen and how softly the music sits in your space.',
    }
    topic = ' '.join(topic.split()).strip(' |')
    if re.search(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', topic):
        raise ValueError('Playlist topic must be translated into English')
    title = _unique_title(channel, topic)
    description = (
        f'{topic}. {angles[channel]}\n\n'
        f'This listening session lasts about {round(minutes)} minutes, so you can settle in and enjoy the music without needing to choose another playlist every few minutes. The songs are arranged for an easy flow, whether you are spending time with someone you love or simply want a warmer atmosphere around you.\n\n'
        'Try it during a coffee date at home, a relaxed dinner, a late drive, or a quiet evening when a little tenderness feels just right. Keep the volume comfortable for your surroundings, and use headphones or speakers according to the moment. You do not have to listen from beginning to end; return whenever you want to bring back the same feeling.\n\n'
        'Which mood should the next playlist capture: a shy first crush, a long-lasting love, a rainy window, or a sunset walk? Share your favorite moment in the comments. Subscribe for more carefully shaped music sessions, with a different setting and feeling each time.'
    )
    validate_metadata(title, description)
    return title, description, [labels[channel], topic], False
