import json
import sys

import pytest

from scripts import auto_write_and_draft as aw

KW = "생활금융 주거 부동산 안내"


def article(chars):
    sent = "외국인 유학생이 한국에서 집을 구할 때 확인할 계약 절차와 비용을 차분히 정리했습니다. "
    per = len(sent.replace(" ", ""))
    n = max(3, chars // per)
    heads = ["계약 전 확인", "비용 구조", "주의할 점"]
    body = ""
    for k in range(3):
        cnt = n // 3 + (1 if k < n % 3 else 0)
        body += f"<h2>{heads[k]}</h2><p>" + sent * cnt + "</p>"
    return {"title": "외국인 유학생을 위한 한국 주거 부동산 계약 체크리스트", "meta_description":
            "한국에서 집을 구하는 외국인 유학생이 계약 전 확인할 절차와 비용, 보증금, 주의할 점을 차근차근 정리한 실용 안내입니다.",
            "content_html": body, "image_queries": [], "labels": ["부동산", "유학생", "계약", "보증금", "월세", "주거", "비용", "체크리스트"]}


def test_short_body_is_rescued_by_expansion(monkeypatch):
    import economy_text as et
    short, full = article(700), article(1900)
    calls = []

    def gen(prompt, temperature=0.7):
        calls.append(prompt[:40])
        return json.dumps(full if "CURRENT JSON:" in prompt else short, ensure_ascii=False)

    monkeypatch.setattr(et, "generate_text", gen)
    monkeypatch.setattr(et, "begin_article", lambda: None)
    monkeypatch.setattr(et, "last_writer_model", "gemini-x", raising=False)
    monkeypatch.setattr(aw, "original_quality_score", aw.original_quality_score)
    art, score, failures, provider = aw._write_article(
        keyword=KW, site_theme="유학생 생활", language="ko", persona="p", tone="t",
        min_chars=1560, target_chars=2000, max_chars=2700)
    assert art is not None and score >= 70
    assert provider.endswith("+expanded")
    assert len(calls) == 3
