"""
1단계: 공감대 + 후킹 질문 + 대화체(2인)로 몰입도 높은 9~11분 대본 생성 (Gemini 2.5 Flash Lite).
결과를 Google Drive의 01_scripts 폴더에 업로드합니다.
"""
import os
import random
import re
import time
from datetime import datetime

import requests

from config import AUDIENCE_PROFILE, LANGUAGES, DRIVE_FOLDER_ID, DRIVE_SUBFOLDERS
from src.drive_utils import get_drive_service, get_or_create_folder, upload_file

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SYSTEM_PROMPT_TEMPLATE = """당신은 유튜브 건강 채널 'Health Clinic'의 전문 대본 작가입니다.
채널 타겟 시청자: {audience}

대본 작성 원칙 (반드시 지킬 것):
1. 도입 15초 안에 시청자가 "어? 내 얘기잖아" 하고 공감할 강력한 후킹 질문으로 시작한다.
   예: "혹시 요즘 계단 오를 때 무릎에서 뚝 소리 나지 않으세요?"
2. 전체를 진행자 2인의 대화체로 쓴다 (내레이션 나열식 금지). 감탄사, 되묻기, 자연스러운 말버릇을 섞어 실제 대화처럼 만든다.
   화자 구분은 반드시 줄 맨 앞에 "[A] " 또는 "[B] " 태그로 표시한다 (언어와 무관하게 항상 이 영문 태그를 쓸 것).
   예:
   [A] 여러분, 오늘 정말 중요한 얘기 하려고 해요.
   [B] 저도 궁금했던 주제인데, 뭔가요?
   두 화자가 비슷한 비중으로 번갈아 말하게 하고, 한쪽이 5줄 이상 독백하지 않게 한다.
3. 중간중간 "여러분은 어떠세요?", "저도 그랬거든요" 같은 시청자와의 심리적 연결 문장을 넣는다.
4. 정보는 정확하고 검증 가능한 내용만 다루고, 과장된 효능/치료 주장은 절대 하지 않는다.
5. 의학적 조언이 아니라는 점을 자연스럽게 대본 안에서 한 번 언급한다.
6. 영상 총 길이 14~16분 분량(내레이션 기준 영어 약 2100~2400단어, 한국어/일본어는 약 3900~4800자)으로 작성한다.
7. 마지막은 구독/좋아요 유도 + 다음 편 예고로 자연스럽게 마무리한다.
8. **전문성과 흥미를 동시에 잡는다 — 이게 가장 중요하다.**
   - 딱딱한 정보 나열이 아니라, "왜 이게 놀라운지" 스토리텔링으로 풀어낸다 (반전, 의외의 사실, 흔한 오해 깨기 등).
   - 실제 연구/통계를 언급할 땐 출처를 일반화해서 표현한다 (예: "한 연구에 따르면" — 없는 연구를 지어내거나 가짜 수치를 만들지 않는다).
   - 전문 용어를 쓰되 바로 쉬운 말로 풀어준다 ("이걸 인슐린 저항성이라고 하는데, 쉽게 말하면...").
   - **영어(EN) 채널의 경우 특히 신경 쓸 것**: 미국/영어권 시청자는 정보 전달 속도가 빠르고 위트 있는 진행을 선호한다.
     지루한 나열식 톤을 피하고, 가벼운 유머·비유·리듬감 있는 문장으로 몰입감을 유지한다.
     (예: "Your pancreas is basically working a double shift it never signed up for.")
9. 출력은 아래 형식을 반드시 지킨다:

[TITLE]
(영상 제목, 후킹성, 40자 이내)

[HOOK]
(도입 15초 대사)

[SCRIPT]
(본문 전체 대사. 모든 줄 맨 앞에 "[A] " 또는 "[B] " 태그를 붙여 화자를 구분한다.)

[SCENE_KEYWORDS]
(영상/이미지 매칭용 키워드를 **최소 45개, 최대 60개** 쉼표로 구분해서 나열한다. 대본 전체 흐름을 따라
 문장/문단이 바뀔 때마다 새 키워드를 하나씩 배정한다는 느낌으로 촘촘하게 뽑는다 — 한 키워드가
 영상에서 너무 오래 반복되지 않고 자주 바뀌도록 하기 위함이다. 같은 키워드를 반복하지 말고
 구체적인 장면으로 뽑는다 (예: senior stretching, knee pain closeup, morning walk, doctor consultation,
 healthy breakfast plate, blood pressure monitor, senior couple laughing, stairs climbing, yoga mat, ...)
"""

USER_PROMPT_TEMPLATE = """주제: {topic}
언어: {lang_label}로 작성.

위 원칙을 지켜서 대본을 작성해주세요.
"""


def _parse_script(raw_text: str) -> dict:
    def _extract(tag):
        m = re.search(rf"\[{tag}\](.*?)(?=\n\[[A-Z_]+\]|\Z)", raw_text, re.S)
        return m.group(1).strip() if m else ""

    return {
        "title": _extract("TITLE"),
        "hook": _extract("HOOK"),
        "script": _extract("SCRIPT"),
        "scene_keywords": _extract("SCENE_KEYWORDS"),
        "raw": raw_text,
    }


def _gemini_post_with_retry(payload: dict, max_retries: int = 5) -> dict:
    """429(rate limit)/5xx 응답 시 지수 백오프(+지터)로 재시도. 그 외 오류는 즉시 올림."""
    for attempt in range(max_retries + 1):
        resp = requests.post(GEMINI_URL, params={"key": GEMINI_API_KEY}, json=payload, timeout=120)
        if resp.status_code not in (429, 500, 502, 503, 504):
            resp.raise_for_status()
            return resp.json()

        if attempt == max_retries:
            resp.raise_for_status()  # 마지막 시도까지 실패하면 그대로 예외 발생

        wait = min(90, (2 ** attempt) * 5) + random.uniform(0, 3)
        print(f"[Script] Gemini {resp.status_code} 응답 — {wait:.1f}초 대기 후 재시도 "
              f"({attempt + 1}/{max_retries})...")
        time.sleep(wait)


def generate_script(topic: str, lang: str) -> dict:
    lang_cfg = LANGUAGES[lang]
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(audience=AUDIENCE_PROFILE[lang])
    user_prompt = USER_PROMPT_TEMPLATE.format(topic=topic, lang_label=lang_cfg["label"])

    print(f"[Script] Gemini 2.5 Flash Lite로 대본 생성 중... (lang={lang}, topic={topic})")
    data = _gemini_post_with_retry({
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"maxOutputTokens": 6000, "temperature": 0.9},
    })
    raw_text = "".join(
        part.get("text", "")
        for cand in data.get("candidates", [])
        for part in cand.get("content", {}).get("parts", [])
    )
    if not raw_text:
        raise RuntimeError(f"Gemini 응답에서 텍스트를 찾지 못했습니다: {data}")

    parsed = _parse_script(raw_text)
    return parsed


def save_script_to_drive(parsed: dict, lang: str, topic_slug: str) -> str:
    service = get_drive_service()
    lang_root = get_or_create_folder(service, f"HealthClinic_{lang}", DRIVE_FOLDER_ID)
    scripts_folder = get_or_create_folder(service, DRIVE_SUBFOLDERS["scripts"], lang_root)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{timestamp}_{topic_slug}.txt"
    local_path = f"/tmp/{filename}"

    with open(local_path, "w", encoding="utf-8") as f:
        f.write(parsed["raw"])

    file_id = upload_file(local_path, scripts_folder, filename)
    print(f"[Script] Drive 업로드 완료: {filename}")
    return file_id


def run(topic: str, lang: str) -> dict:
    parsed = generate_script(topic, lang)
    topic_slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "_", topic)[:40]
    file_id = save_script_to_drive(parsed, lang, topic_slug)
    parsed["drive_file_id"] = file_id
    parsed["topic_slug"] = topic_slug
    return parsed


if __name__ == "__main__":
    result = run("무릎 통증 완화 스트레칭", "kr")
    print(result["title"])
