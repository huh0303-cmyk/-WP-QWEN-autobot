"""Regression: 110-120 character headlines were published (search results cut them at ~60)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from editorial_title_gate import require_editorial_approval


def approve(title):
    return require_editorial_approval(title=title, content="<p>Plain body.</p>", meta="m",
                                      keyword="k", gemini_generate=lambda p: "")


@pytest.fixture(autouse=True)
def deterministic_only(monkeypatch):
    monkeypatch.setenv("CHATGPT_SINGLE_MODEL_PIPELINE", "true")


def test_overlong_english_headline_is_rejected():
    with pytest.raises(ValueError, match="TITLE_QUALITY_FAIL"):
        approve("E-9 Visa Ceiling Adjustments Prompt Overhaul of Employer Application Procedures in Manufacturing and Logistics")


def test_normal_english_headline_passes():
    assert approve("E-9 Visa Quota 2026: What Employers Must File")["ok"] is True


def test_overlong_korean_headline_is_rejected():
    with pytest.raises(ValueError, match="TITLE_QUALITY_FAIL"):
        approve("외국인 근로자 고용허가제 쿼터 조정에 따라 제조업과 물류업 사업주가 준비해야 할 신청 절차와 서류 변경 사항")


def test_normal_korean_headline_passes():
    assert approve("E-9 고용허가제 쿼터 변경, 사업주 신청 절차 정리")["ok"] is True
