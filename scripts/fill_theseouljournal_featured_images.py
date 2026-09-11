"""Fill missing The Seoul Journal featured images using the licensed image desk."""
from __future__ import annotations
import os
import fill_koreanews_featured_images as desk

desk.SITE = "https://theseouljournal.com"
desk.PASSWORD = os.getenv("THESEOULJOURNALCOM", "").strip()
desk.SESSION.headers["User-Agent"] = "TheSeoulJournal-ImageDesk/1.0"
desk.ALT_SUFFIX = "— editorial news image"
desk.KEYWORDS = [
    (("Korea", "Seoul", "Busan"), "Seoul South Korea city editorial"),
    (("rail", "KTX", "train"), "South Korea high speed train"),
    (("export", "chip", "semiconductor"), "semiconductor factory technology"),
    (("OpenAI", "AI", "technology"), "artificial intelligence technology newsroom"),
    (("G-Dragon", "BTS", "K-pop"), "Korean music concert stage"),
    (("coach", "football", "sports"), "football stadium coach"),
    (("border", "migrant", "Spain"), "Mediterranean border coast Spain"),
    (("shooting", "crime", "safety"), "police emergency city street"),
    (("park", "flower", "garden"), "Seoul park flowers garden"),
    (("economy", "finance", "market"), "Asian financial market business"),
]

if __name__ == "__main__":
    desk.main()
