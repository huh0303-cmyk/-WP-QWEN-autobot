#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""여러 업로드 스크립트가 공유하는 언어별 메타데이터/파일 목록 헬퍼."""
import os, glob

OUTPUT_DIR = "outputs"

def get_secret(*names):
    """여러 후보 환경변수 이름 중 먼저 값이 있는 것을 반환.
    예: get_secret('ML_FB_PAGE_ID', 'FB_PAGE_ID') -> ML_ 접두사가 없어도
    기존(Claude Code 등으로 이미 등록된) 시크릿을 자동으로 재사용."""
    import os
    for name in names:
        val = os.environ.get(name)
        if val:
            return val
    return None

# 소셜 채널(유튜브/틱톡/페북/인스타/스레드)에 올릴 언어. 한국어(TOPIK)는 기존 별도
# 자동화 파이프라인에서 이미 같은 채널에 발행 중이라 중복 게시를 막기 위해 기본 제외.
SOCIAL_LANGS = ["en", "ja", "es", "vi", "fr", "de", "zh", "ar", "ru"]

META = {
    "en": {
        "title": "5-Second English Word Quiz | Beginner Vocabulary",
        "desc": "Test your English vocabulary in 5 seconds! Beginner-level words with pictures.\n#EnglishQuiz #LearnEnglish #Vocabulary #SurvivalEnglish",
    },
    "ja": {
        "title": "5秒で答える日本語単語クイズ | 初級ボキャブラリー",
        "desc": "5秒以内に答えてみよう！写真で覚える初級日本語単語。\n#日本語クイズ #日本語勉強 #JLPT #SurvivalJapanese",
    },
    "es": {
        "title": "Quiz de Vocabulario en Español en 5 Segundos | Nivel Básico",
        "desc": "¡Responde en 5 segundos! Vocabulario básico en español con imágenes.\n#EspañolQuiz #AprenderEspañol #Vocabulario #SurvivalSpanish",
    },
    "vi": {
        "title": "Đố Từ Vựng Tiếng Việt Trong 5 Giây | Trình Độ Cơ Bản",
        "desc": "Trả lời trong 5 giây! Từ vựng tiếng Việt cơ bản kèm hình ảnh.\n#TiengVietQuiz #HocTiengViet #TuVung #SurvivalVietnamese",
    },
    "ko": {
        "title": "5초 안에 맞히는 TOPIK 초급 단어 퀴즈",
        "desc": "5초 안에 답해보세요! 사진으로 배우는 TOPIK 초급 어휘.\n#TOPIK퀴즈 #한국어공부 #TOPIK어휘 #서울국제대학교",
    },
    "fr": {
        "title": "Quiz de Vocabulaire Français en 5 Secondes | Niveau Débutant",
        "desc": "Répondez en 5 secondes ! Vocabulaire français de base avec images.\n#FrenchQuiz #ApprendreLeFrancais #Vocabulaire #SurvivalFrench",
    },
    "de": {
        "title": "5-Sekunden Deutsch-Vokabel-Quiz | Für Anfänger",
        "desc": "Antworte in 5 Sekunden! Deutscher Grundwortschatz mit Bildern.\n#GermanQuiz #DeutschLernen #Wortschatz #SurvivalGerman",
    },
    "zh": {
        "title": "5秒中文词汇小测验 | 初级词汇",
        "desc": "5秒内作答！配图学习初级中文词汇。\n#中文测验 #学中文 #词汇 #SurvivalChinese",
    },
    "ar": {
        "title": "اختبار مفردات عربية في 5 ثوانٍ | مستوى مبتدئ",
        "desc": "أجب خلال 5 ثوانٍ! مفردات عربية أساسية مع صور.\n#ArabicQuiz #تعلم_العربية #مفردات #SurvivalArabic",
    },
    "ru": {
        "title": "Тест на знание русской лексики за 5 секунд | Начальный уровень",
        "desc": "Ответь за 5 секунд! Базовая русская лексика с картинками.\n#RussianQuiz #УчимРусский #Лексика #SurvivalRussian",
    },
}

def list_videos(langs=None):
    """outputs/quiz_{lang}_beginner.mp4 파일들을 (lang, path, title, desc) 튜플로 반환.
    langs를 지정하면 그 언어들만 필터링 (예: 소셜 업로드는 한국어 제외)."""
    results = []
    for path in sorted(glob.glob(os.path.join(OUTPUT_DIR, "quiz_*_beginner.mp4"))):
        base = os.path.basename(path)
        lang = base.replace("quiz_", "").replace("_beginner.mp4", "")
        if lang in META and (langs is None or lang in langs):
            results.append((lang, path, META[lang]["title"], META[lang]["desc"]))
    return results
