#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classic_reads_100.py
─────────────────────────────────────────────────────────────
CLASSIC_READS_JOURNAL 채널용 "고전 100선" 리스트(동서양 망라).
실행하면 scripts/data/classic_reads_100.json으로 저장된다.

주의: "하버드대학 추천"은 채널 브랜딩/후킹 문구일 뿐, 실제 하버드의 공식
100선 목록이 존재하는 게 아니다(실제 "Harvard Classics"는 1909년 51권
전집으로 서양 위주). 여기 목록은 동서양을 아우르는 자체 큐레이션이며,
영상 나레이션에서 "하버드 추천"을 사실인 것처럼 구체적으로 진술하지
않도록 주의할 것 — 채널 소개/썸네일 톤 정도로만 사용.
"""
import json
import os

BOOKS = [
    ("The Epic of Gilgamesh", "Unknown (Mesopotamian)", "c. 2100 BC", "Middle East"),
    ("The Iliad", "Homer", "c. 8th century BC", "West"),
    ("The Odyssey", "Homer", "c. 8th century BC", "West"),
    ("The Book of Songs (Shijing)", "Various", "c. 11th–7th century BC", "East Asia"),
    ("The Analects", "Confucius", "c. 475 BC", "East Asia"),
    ("Tao Te Ching", "Laozi", "c. 4th century BC", "East Asia"),
    ("The Art of War", "Sun Tzu", "c. 5th century BC", "East Asia"),
    ("Zhuangzi", "Zhuangzi", "c. 4th century BC", "East Asia"),
    ("Mencius", "Mencius", "c. 3rd century BC", "East Asia"),
    ("The Upanishads (selections)", "Unknown", "c. 800 BC", "South Asia"),
    ("The Bhagavad Gita", "Attrib. Vyasa", "c. 2nd century BC", "South Asia"),
    ("The Ramayana", "Valmiki", "c. 5th century BC", "South Asia"),
    ("The Mahabharata", "Vyasa", "c. 4th century BC", "South Asia"),
    ("The Dhammapada", "Attrib. Buddha", "c. 3rd century BC", "South Asia"),
    ("Panchatantra", "Vishnu Sharma", "c. 3rd century BC", "South Asia"),
    ("Oedipus Rex", "Sophocles", "c. 429 BC", "West"),
    ("The Republic", "Plato", "c. 375 BC", "West"),
    ("Nicomachean Ethics", "Aristotle", "c. 340 BC", "West"),
    ("Metamorphoses", "Ovid", "8 AD", "West"),
    ("The Egyptian Book of the Dead", "Unknown", "c. 1550 BC", "Africa/Middle East"),
    ("Confessions", "Augustine of Hippo", "397 AD", "West"),
    ("The Shahnameh", "Ferdowsi", "c. 1010", "Middle East"),
    ("The Tale of Genji", "Murasaki Shikibu", "c. 1010", "East Asia"),
    ("The Pillow Book", "Sei Shōnagon", "c. 1002", "East Asia"),
    ("The Rubáiyát of Omar Khayyám", "Omar Khayyám", "c. 1100", "Middle East"),
    ("The Conference of the Birds", "Attar of Nishapur", "c. 1177", "Middle East"),
    ("The Divine Comedy", "Dante Alighieri", "1320", "West"),
    ("The Tale of the Heike", "Unknown", "c. 1330", "East Asia"),
    ("The Canterbury Tales", "Geoffrey Chaucer", "1400", "West"),
    ("One Thousand and One Nights", "Various", "8th–14th century", "Middle East"),
    ("Popol Vuh", "Maya oral tradition", "pre-Columbian", "Americas"),
    ("Sundiata: An Epic of Old Mali", "Oral tradition", "c. 13th century", "Africa"),
    ("Romance of the Three Kingdoms", "Luo Guanzhong", "14th century", "East Asia"),
    ("Water Margin", "Shi Nai'an", "14th century", "East Asia"),
    ("The Masnavi", "Rumi", "13th century", "Middle East"),
    ("The Prince", "Niccolò Machiavelli", "1532", "West"),
    ("Journey to the West", "Wu Cheng'en", "1592", "East Asia"),
    ("Don Quixote", "Miguel de Cervantes", "1605", "West"),
    ("Hamlet", "William Shakespeare", "1603", "West"),
    ("Macbeth", "William Shakespeare", "1606", "West"),
    ("The Book of Five Rings", "Miyamoto Musashi", "1645", "East Asia"),
    ("Hong Gildong jeon", "Heo Gyun", "17th century", "East Asia"),
    ("The Cloud Dream of the Nine", "Kim Man-jung", "1687", "East Asia"),
    ("Paradise Lost", "John Milton", "1667", "West"),
    ("Robinson Crusoe", "Daniel Defoe", "1719", "West"),
    ("Gulliver's Travels", "Jonathan Swift", "1726", "West"),
    ("Candide", "Voltaire", "1759", "West"),
    ("The Sorrows of Young Werther", "Johann Wolfgang von Goethe", "1774", "West"),
    ("Tale of Chunhyang", "Unknown (Korean folk classic)", "18th century", "East Asia"),
    ("Pride and Prejudice", "Jane Austen", "1813", "West"),
    ("Frankenstein", "Mary Shelley", "1818", "West"),
    ("Faust", "Johann Wolfgang von Goethe", "1832", "West"),
    ("Le Père Goriot", "Honoré de Balzac", "1835", "West"),
    ("Oliver Twist", "Charles Dickens", "1838", "West"),
    ("A Christmas Carol", "Charles Dickens", "1843", "West"),
    ("The Count of Monte Cristo", "Alexandre Dumas", "1844", "West"),
    ("Wuthering Heights", "Emily Brontë", "1847", "West"),
    ("Jane Eyre", "Charlotte Brontë", "1847", "West"),
    ("Vanity Fair", "William Makepeace Thackeray", "1848", "West"),
    ("Moby-Dick", "Herman Melville", "1851", "West"),
    ("Walden", "Henry David Thoreau", "1854", "West"),
    ("Madame Bovary", "Gustave Flaubert", "1857", "West"),
    ("Les Misérables", "Victor Hugo", "1862", "West"),
    ("Crime and Punishment", "Fyodor Dostoevsky", "1866", "West"),
    ("War and Peace", "Leo Tolstoy", "1869", "West"),
    ("Twenty Thousand Leagues Under the Sea", "Jules Verne", "1870", "West"),
    ("Middlemarch", "George Eliot", "1871", "West"),
    ("Anna Karenina", "Leo Tolstoy", "1877", "West"),
    ("The Brothers Karamazov", "Fyodor Dostoevsky", "1880", "West"),
    ("Treasure Island", "Robert Louis Stevenson", "1883", "West"),
    ("The Adventures of Huckleberry Finn", "Mark Twain", "1884", "West"),
    ("The Strange Case of Dr Jekyll and Mr Hyde", "Robert Louis Stevenson", "1886", "West"),
    ("The Picture of Dorian Gray", "Oscar Wilde", "1890", "West"),
    ("The Adventures of Sherlock Holmes", "Arthur Conan Doyle", "1892", "West"),
    ("The Time Machine", "H. G. Wells", "1895", "West"),
    ("Dracula", "Bram Stoker", "1897", "West"),
    ("The War of the Worlds", "H. G. Wells", "1898", "West"),
    ("Heart of Darkness", "Joseph Conrad", "1899", "West"),
    ("I Am a Cat", "Natsume Sōseki", "1905", "East Asia"),
    ("The Wonderful Wizard of Oz", "L. Frank Baum", "1900", "West"),
    ("The Hound of the Baskervilles", "Arthur Conan Doyle", "1902", "West"),
    ("Kokoro", "Natsume Sōseki", "1914", "East Asia"),
    ("Gitanjali", "Rabindranath Tagore", "1910", "South Asia"),
    ("Anne of Green Gables", "L. M. Montgomery", "1908", "West"),
    ("In Search of Lost Time", "Marcel Proust", "1913", "West"),
    ("The Metamorphosis", "Franz Kafka", "1915", "West"),
    ("Ulysses", "James Joyce", "1922", "West"),
    ("The Trial", "Franz Kafka", "1925", "West"),
    ("The Great Gatsby", "F. Scott Fitzgerald", "1925", "West"),
    ("Mrs Dalloway", "Virginia Woolf", "1925", "West"),
    ("To the Lighthouse", "Virginia Woolf", "1927", "West"),
    ("All Quiet on the Western Front", "Erich Maria Remarque", "1929", "West"),
    ("A Farewell to Arms", "Ernest Hemingway", "1929", "West"),
    ("In Praise of Shadows", "Jun'ichirō Tanizaki", "1933", "East Asia"),
    ("Brave New World", "Aldous Huxley", "1932", "West"),
    ("The Travels of Marco Polo", "Marco Polo", "1300", "West/East Asia"),
    ("The Kama Sutra", "Vātsyāyana", "c. 3rd century", "South Asia"),
    ("Dream of the Red Chamber", "Cao Xueqin", "1791", "East Asia"),
    ("Beowulf", "Unknown (Anglo-Saxon)", "c. 8th–11th century", "West"),
    ("The Secret History of the Mongols", "Unknown", "c. 1240", "East Asia/Central Asia"),
]


def main():
    assert len(BOOKS) == 100, f"책 목록이 100개가 아님: {len(BOOKS)}개"
    titles = [b[0] for b in BOOKS]
    assert len(titles) == len(set(titles)), "중복된 책 제목이 있음"

    out = [
        {"rank": i + 1, "title": t, "author": a, "year": y, "region": r}
        for i, (t, a, y, r) in enumerate(BOOKS)
    ]
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "classic_reads_100.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    west = sum(1 for b in BOOKS if b[3] in ("West",))
    east = len(BOOKS) - west
    print(f"✅ {len(BOOKS)}권 저장 완료: {out_path}")
    print(f"   서양 계열 {west}권 / 동양+기타 {east}권")


if __name__ == "__main__":
    main()
