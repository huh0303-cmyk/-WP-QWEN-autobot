#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import autopost_mega as ap

tests = [
    ("한국어 초급 회화, 실제로는 어떻게 진행될까", "Careers, Culture, Language"),
    ("전통시장 체험 프로그램, 정말 효과가 있을까? 솔직한 분석", "Careers, Culture, Language"),
    ("외국인 창업비자, 정말 효과가 있을까? 솔직한 분석", "Careers, Culture, Language"),
]

for title, cand_str in tests:
    gprompt = (f"다음 글 제목/키워드를 아래 카테고리 중 하나로 분류해줘. "
               f"카테고리 이름만 정확히 그대로 한 단어(구)로만 답해. 애매하면 가장 가까운 것.\n"
               f"카테고리 목록: {cand_str}\n"
               f"제목/키워드: {title}\n"
               f"답(카테고리 이름만):")
    try:
        resp = ap.gemini_client.models.generate_content(
            model=ap.GEMINI_MODEL_FALLBACK, contents=gprompt,
            config={"temperature":0.1,"max_output_tokens":300,"thinking_config":{"thinking_budget":0}})
        print(f"제목: {title}")
        print(f"  응답 repr: {repr(resp.text)}")
    except Exception as e:
        print(f"제목: {title}")
        print(f"  예외: {e}")
    print()
