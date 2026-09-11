"""Owner's English title/description requirements for private YouTube uploads."""
import re


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


def playlist_metadata(channel, topic, minutes):
    labels = {'healing': 'Nature Sounds', 'kpop': 'Korean Acoustic Pop',
              'globalmusic': 'Sweet Romantic Songs', 'mbb': 'Classical Music',
              'starbucks': 'Instrumental Cafe Music'}
    angles = {
        'healing': 'Let the sounds of nature become a gentle backdrop to your day. Listen to the textures in the recording, from quieter moments to fuller layers of sound, and choose a comfortable volume for the space around you.',
        'kpop': 'Make room for Korean pop with an acoustic, unplugged spirit. Listen for the connection between the vocals and the accompaniment, and enjoy the different moods that a song can bring to a quiet evening or a familiar daily routine.',
        'globalmusic': 'Settle into a romantic listening session with a soft, welcoming mood. Let the voices and melodies accompany a quiet evening, a cup of coffee, or a little time together. Enjoy the feeling of each song without needing to rush to the next.',
        'mbb': 'Spend some time with classical music and the details that reward an unhurried listen. Follow the melodies, notice the changes in expression, and let the music accompany reading, a quiet afternoon, or a comfortable moment away from a busy day.',
        'starbucks': 'Bring a relaxed cafe mood to your desk with instrumental music. Keep it nearby while you read, write, organize your day, or take a coffee break. With no lyrics to follow, you can choose how closely to listen and how softly the music sits in your space.',
    }
    topic = ' '.join(topic.split()).strip(' |')
    if re.search(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', topic):
        raise ValueError('Playlist topic must be translated into English')
    suffix = f' | {labels[channel]} for Your Quiet Moments'
    room = 100 - len(suffix)
    short = topic if len(topic) <= room else topic[:room].rsplit(' ', 1)[0]
    title = short + suffix
    description = (
        f'{topic}. {angles[channel]}\n\n'
        f'This session runs for approximately {round(minutes)} minutes, giving you time to settle in without choosing something new every few minutes. '
        'Start at the beginning for the full listening experience, or return whenever you would like a familiar background for your day.\n\n'
        'Adjust the volume to suit your surroundings and take a break whenever you need one. You can listen through headphones or speakers, on your own or with someone you enjoy spending time with. '
        'There is no need to finish in one sitting; simply make the session part of a routine that feels comfortable to you.\n\n'
        'If this selection suits your mood, save it for another day and tell us which moments you enjoyed. Subscribe for more thoughtfully chosen listening sessions and discover something to accompany your next quiet moment.'
    )
    validate_metadata(title, description)
    return title, description, [labels[channel], topic], False
