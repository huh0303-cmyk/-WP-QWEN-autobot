import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from news_source_registry import get_enabled_rss_source_records


def test_rights_audited_feeds_cover_user_required_desks():
    ko = {row["category"] for row in get_enabled_rss_source_records("ko")}
    en = {row["category"] for row in get_enabled_rss_source_records("en")}
    assert {"정치", "경제", "국방", "글로벌", "문화", "스포츠"} <= ko
    assert {"Politics", "Business", "Military", "World", "Culture", "Sports"} <= en
