"""Read-only vocabulary operating plan. Account labels are not OAuth proof."""
import json
from datetime import datetime
from pathlib import Path
from scripts.vocabulary_card_ledger import daily_schedule, KST

ROOT=Path(__file__).resolve().parents[1]

def vocabulary_status(config_path=None):
    try:
        config=json.loads(Path(config_path or ROOT/'config/vocabulary_cards.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return {'available':False,'enabled':False,'error':'단어 카드 운영 설정을 불러오지 못했습니다.'}
    today=datetime.now(KST).date().isoformat()
    accounts=[
      {'platform':'YouTube Shorts','topik':'서울국제대학SIS-TOPIK · @seoultopik (등록값)','english':'English Survival · @English_Survival','language':'SIS-Language Center · @sis_languagecenter','status':'채널 지정 · 업로드 인증 확인 대기'},
      {'platform':'TikTok','topik':'@sis_topik','english':'계정 확인 필요','language':'계정 확인 필요','status':'발행 인증 대기'},
      {'platform':'Facebook Reels','topik':'서울국제대학 SIS - TOPIK Center','english':'서울국제대학 Sis-ENGLISH Center','language':'서울국제대학교 SIS - Language Center','status':'페이지 확인 · 공개 발행 검증 대기'},
      {'platform':'Instagram Reels','topik':'@sis_topik1 / 등록값 @sis__topik 불일치','english':'@sis_english1','language':'@sis_language','status':'계정·발행 권한 확인 필요'},
      {'platform':'Threads','topik':'@sis__topik','english':'@sis_english1','language':'@sis_language','status':'발행 인증 대기'},
    ]
    return dict(available=True,enabled=config['enabled'],date=today,timezone=config['timezone'],
        schedule=daily_schedule(today,config),windows=config['windows'],accounts=accounts,
        rotation=['독일어','프랑스어','베트남어','스페인어'],cards_per_slot=3,cards_per_day=6,
        target_posts_per_day=6*len(config['platforms']),quiz_every=config['quiz_every_unique_words'],
        quiz_mode=config['quiz_mode'],word_repetitions=config['word_repetitions'],
        sentence_repetitions=config['sentence_repetitions'],published_count=None,
        paid_generation_enabled=config['paid_generation_enabled'],tts=config.get('tts'),actual_cost=None)
