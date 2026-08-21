#!/usr/bin/env python3
"""Deterministic editorial gate for the rebuilt WordPress network.

The gate does not claim to detect AI authorship.  It blocks observable quality
problems: templated filler, unsupported claims, weak structure, and images whose
alt text is missing or unrelated to the nearby section.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from urllib.parse import urlparse


FILLER_PATTERNS = (
    r"\b(?:in conclusion|in today's fast-paced world|it is important to note|"
    r"delve into|comprehensive guide|unlock the secrets)\b",
    r"(?:결론적으로|오늘날 빠르게 변화하는|알아보도록 하겠습니다|"
    r"도움이 되셨기를 바랍니다|완벽 가이드|총정리해보겠습니다)",
)
MODEL_LEAK_PATTERNS = (
    r"\b(?:as an ai|language model|training data|knowledge cutoff|generated response)\b",
    r"(?:AI 언어 모델|학습 데이터|지식 기준일|생성된 답변)",
)
FAKE_EXPERIENCE_PATTERNS = (
    r"\b(?:i personally tested|my patient|in my clinic|when i visited)\b",
    r"(?:제가 직접 써봤|제 환자|제 진료실|제가 방문했을 때)",
)
WORD_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.headings: list[str] = []
        self.links: list[str] = []
        self.images: list[dict[str, str]] = []
        self._heading: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        data = dict(attrs)
        if tag in {"h2", "h3"}:
            self._heading = []
        elif tag == "a" and data.get("href"):
            self.links.append(data["href"])
        elif tag == "img":
            self.images.append({
                "src": data.get("src", "").strip(),
                "alt": data.get("alt", "").strip(),
                "title": data.get("title", "").strip(),
            })

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h2", "h3"} and self._heading is not None:
            self.headings.append(" ".join(self._heading).strip())
            self._heading = None

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.text_parts.append(cleaned)
            if self._heading is not None:
                self._heading.append(cleaned)


@dataclass
class GateResult:
    passed: bool
    score: int
    blockers: list[str]
    warnings: list[str]
    metrics: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _tokens(value: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "하는", "있는", "에서", "으로", "대한"}
    return {w.lower() for w in WORD_RE.findall(value) if w.lower() not in stop}


def evaluate_article(title: str, content: str, site_url: str = "") -> GateResult:
    parser = ArticleParser()
    parser.feed(content or "")
    plain = html.unescape(" ".join(parser.text_parts))
    words = WORD_RE.findall(plain)
    blockers: list[str] = []
    warnings: list[str] = []
    deductions = 0

    if len(words) < 900:
        blockers.append("본문이 900단어/어절 미만")
        deductions += 30
    if len(parser.headings) < 4:
        blockers.append("의미 있는 H2/H3 소제목이 4개 미만")
        deductions += 18

    leak_hits = sum(len(re.findall(p, plain, re.I)) for p in MODEL_LEAK_PATTERNS)
    filler_hits = sum(len(re.findall(p, plain, re.I)) for p in FILLER_PATTERNS)
    fake_hits = sum(len(re.findall(p, plain, re.I)) for p in FAKE_EXPERIENCE_PATTERNS)
    if leak_hits:
        blockers.append("모델/프롬프트 흔적 발견")
        deductions += 40
    if fake_hits:
        blockers.append("검증할 수 없는 1인칭 경험·전문가 행세 문구 발견")
        deductions += 35
    if filler_hits > 1:
        blockers.append("상투적 자동생성 문구 반복")
        deductions += 20

    external_links = []
    site_host = urlparse(site_url).netloc.lower()
    for link in parser.links:
        host = urlparse(link).netloc.lower()
        if host and host != site_host:
            external_links.append(link)
    if len(set(external_links)) < 2:
        blockers.append("독자가 확인할 외부 근거 링크가 2개 미만")
        deductions += 20

    article_tokens = _tokens(title + " " + " ".join(parser.headings))
    missing_alt = 0
    unrelated_alt = 0
    decorative_alt = 0
    for image in parser.images:
        alt = image["alt"]
        if not alt:
            missing_alt += 1
            continue
        alt_tokens = _tokens(alt)
        if alt.lower() in {"image", "photo", "thumbnail", "이미지", "사진", title.lower()}:
            decorative_alt += 1
        if article_tokens and not (alt_tokens & article_tokens):
            unrelated_alt += 1
    if len(parser.images) < 2:
        blockers.append("본문 연관 이미지가 2개 미만")
        deductions += 20
    if missing_alt:
        blockers.append(f"ALT 누락 이미지 {missing_alt}개")
        deductions += min(30, missing_alt * 10)
    if unrelated_alt:
        blockers.append(f"제목·소제목과 연결되지 않는 ALT {unrelated_alt}개")
        deductions += min(24, unrelated_alt * 8)
    if decorative_alt:
        warnings.append(f"설명력이 낮은 ALT {decorative_alt}개")
        deductions += min(12, decorative_alt * 4)

    if re.search(r"(?:의학|건강|질병|치료|약물|보험|세금|법률|투자)", title + plain, re.I):
        if not re.search(r"(?:최종 확인|전문가와 상담|공식 자료|의료진과 상담|법률 자문|투자 자문)", plain):
            blockers.append("YMYL 주제의 한계·확인 경로 안내 누락")
            deductions += 15

    score = max(0, 100 - deductions)
    return GateResult(
        passed=not blockers and score >= 90,
        score=score,
        blockers=blockers,
        warnings=warnings,
        metrics={
            "word_count": len(words),
            "heading_count": len(parser.headings),
            "image_count": len(parser.images),
            "external_source_count": len(set(external_links)),
            "missing_alt_count": missing_alt,
            "unrelated_alt_count": unrelated_alt,
            "filler_hits": filler_hits,
            "model_leak_hits": leak_hits,
            "fake_experience_hits": fake_hits,
        },
    )


