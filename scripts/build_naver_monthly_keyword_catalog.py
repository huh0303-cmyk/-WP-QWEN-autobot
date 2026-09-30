#!/usr/bin/env python3
"""Build 100 research-gated Naver keyword candidates for every calendar month."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALENDAR_PATH = ROOT / "config" / "naver_monthly_keyword_calendar.json"
DEFAULT_OUTPUT = ROOT / "config" / "naver_monthly_keyword_100.json"

SUPPORT_TERMS = [
    "정부지원금 신청", "보조금24 혜택 확인", "지자체 지원금", "청년 지원금",
    "소상공인 지원사업", "주거급여 신청", "청년 월세 지원", "에너지바우처",
    "전기요금 복지할인", "도시가스 요금 지원", "근로장려금", "자녀장려금",
    "실업급여 신청", "국민취업지원제도", "내일배움카드", "아이돌봄 지원",
    "한부모가족 지원", "노인 교통비 지원", "장애인 복지 혜택", "기초연금 신청",
    "전입신고 준비물", "확정일자 신청", "전세 계약 체크리스트", "신용점수 무료조회",
    "주택담보대출 비교", "자동차세 납부", "재산세 조회", "건강보험료 환급금",
    "통신비 감면 신청", "문화누리카드 사용처",
]

HEALTH_TERMS = [
    "국가건강검진 대상자", "건강검진 금식시간", "건강검진 결과 조회",
    "독감 무료접종 대상", "예방접종 일정", "고혈압 건강수칙", "당뇨 건강수칙",
    "미세먼지 건강수칙", "식중독 예방수칙", "온열질환 예방", "한랭질환 예방",
    "감염병 예방수칙", "응급실 이용 안내", "야간 진료 병원 찾기", "건강보험 본인부담상한제",
]

STATIONS = ["서울역", "용산역", "광명역", "수서역", "대전역", "동대구역", "부산역", "광주송정역", "목포역", "강릉역"]
AIRPORT_AREAS = ["서울역", "강남", "잠실", "수원", "용인", "성남", "고양", "파주", "부천", "대전"]
BUS_TERMS = ["고속버스 시간표", "시외버스 시간표", "고속버스 예매", "시외버스 예매", "고속버스 취소수수료"]

GENERIC_CURRENT_EVENTS = [
    ("오늘 정치 주요 일정", ["https://www.assembly.go.kr", "https://www.korea.kr"], ["naver_n1", "naver_n3"]),
    ("정부 정책 오늘 발표", ["https://www.korea.kr"], ["naver_n1", "naver_n3"]),
    ("국회 본회의 주요 안건", ["https://www.assembly.go.kr"], ["naver_n1", "naver_n3"]),
    ("오늘 영화 박스오피스", ["https://www.kobis.or.kr"], ["naver_n3"]),
    ("이번달 개봉 영화", ["https://www.kobis.or.kr"], ["naver_n3"]),
    ("오늘 스포츠 경기 일정", ["https://www.sports.or.kr"], ["naver_n3"]),
    ("국가대표 경기 일정", ["https://www.sports.or.kr"], ["naver_n3"]),
    ("국방부 공식 발표", ["https://www.mnd.go.kr"], ["naver_n3"]),
    ("지뢰 사고 안전수칙", ["https://www.mnd.go.kr", "https://www.safetyreport.go.kr"], ["naver_n3"]),
    ("군사훈련 교통통제", ["https://www.mnd.go.kr", "https://www.korea.kr"], ["naver_n3"]),
]

OCTOBER_2026_EVENTS = [
    ("아시안게임 오늘 경기 일정", ["https://www.aichi-nagoya2026.org/en/", "https://www.sports.or.kr"], ["naver_n3"]),
    ("아시안게임 메달 순위", ["https://www.aichi-nagoya2026.org/en/"], ["naver_n3"]),
    ("아시안게임 한국 경기 결과", ["https://www.aichi-nagoya2026.org/en/", "https://www.sports.or.kr"], ["naver_n3"]),
    ("오늘 정치 주요 일정", ["https://www.assembly.go.kr", "https://www.korea.kr"], ["naver_n1", "naver_n3"]),
    ("정부 정책 오늘 발표", ["https://www.korea.kr"], ["naver_n1", "naver_n3"]),
    ("암살자들 영화 상영 정보", ["https://www.kobis.or.kr"], ["naver_n3"]),
    ("오늘 영화 박스오피스", ["https://www.kobis.or.kr"], ["naver_n3"]),
    ("국방부 공식 발표", ["https://www.mnd.go.kr"], ["naver_n3"]),
    ("지뢰 사고 안전수칙", ["https://www.mnd.go.kr", "https://www.safetyreport.go.kr"], ["naver_n3"]),
    ("지역별 군사훈련 교통통제", ["https://www.mnd.go.kr", "https://www.korea.kr"], ["naver_n3"]),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _entry(query: str, cluster: str, sites: list[str], sources: list[str]) -> dict:
    return {
        "query": query,
        "cluster": cluster,
        "site_ids": sites,
        "official_sources": sources,
        "requires_same_day_validation": True,
        "measured_search_volume": None,
    }


def build_month(calendar: dict, month: int, year: int) -> list[dict]:
    links = calendar["research_links"]
    items: list[dict] = []

    for term in SUPPORT_TERMS:
        items.append(_entry(f"{month}월 {term}", "지원·금융", ["naver_n1", "naver_n3"], [links["government24"], links["bokjiro"]]))
    for term in HEALTH_TERMS:
        items.append(_entry(f"{month}월 {term}", "건강·검진", ["naver_n2"], [links["kdca"], links["nhis"], links["national_health"]]))
    for station in STATIONS:
        items.append(_entry(f"{station} KTX 시간표", "철도·예매", ["naver_n3"], [links["korail"]]))
        items.append(_entry(f"{station} 기차표 예매", "철도·예매", ["naver_n3"], [links["korail"]]))
    for area in AIRPORT_AREAS:
        items.append(_entry(f"{area} 인천공항버스 시간표", "공항버스", ["naver_n3"], [links["airport_transport"]]))
    for term in BUS_TERMS:
        items.append(_entry(term, "고속·시외버스", ["naver_n3"], [links["kobus"], links["bustago"]]))

    event_terms = OCTOBER_2026_EVENTS if year == 2026 and month == 10 else GENERIC_CURRENT_EVENTS
    for query, sources, sites in event_terms:
        items.append(_entry(query.replace("이번달", f"{month}월"), "당일 인기·시사", sites, sources))

    existing = {item["query"] for item in items}
    seasonal: list[dict] = []
    suffixes = ["대상", "기간", "신청방법", "일정", "공식 확인"]
    for cluster in calendar["months"][str(month)]:
        sources = [links[key] for key in cluster["official_sources"]]
        for query in cluster["queries"]:
            for suffix in suffixes:
                candidate = f"{year}년 {query} {suffix}"
                if candidate in existing:
                    continue
                seasonal.append(_entry(candidate, cluster["cluster"], cluster["site_ids"], sources))
                existing.add(candidate)
                if len(seasonal) == 10:
                    break
            if len(seasonal) == 10:
                break
        if len(seasonal) == 10:
            break
    if len(seasonal) != 10:
        raise RuntimeError(f"month {month}: expected 10 seasonal candidates, got {len(seasonal)}")
    items.extend(seasonal)

    if len(items) != 100 or len({item["query"] for item in items}) != 100:
        raise RuntimeError(f"month {month}: catalog must contain exactly 100 unique candidates")
    for index, item in enumerate(items, start=1):
        item["keyword_id"] = f"{year}-{month:02d}-{index:03d}"
    return items


def build_catalog(year: int) -> dict:
    calendar = load_json(CALENDAR_PATH)
    return {
        "version": 1,
        "year": year,
        "timezone": "Asia/Seoul",
        "purpose": "Exactly 100 monthly Naver candidates; every candidate must be re-ranked with same-day evidence before use.",
        "absolute_search_volume_verified": False,
        "months": {str(month): build_month(calendar, month, year) for month in range(1, 13)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog(args.year)
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"year": args.year, "months": 12, "keywords_per_month": 100}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
