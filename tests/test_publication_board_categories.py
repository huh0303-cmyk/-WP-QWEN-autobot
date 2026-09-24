import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publication_board.py"
spec = importlib.util.spec_from_file_location("publication_board", MODULE_PATH)
publication_board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication_board)

def test_placeholder_categories_are_hidden():
    assert publication_board.clean_category_labels(["Etc"], "K-Beauty Reviews") == ["K-Beauty Reviews"]
    assert publication_board.clean_category_labels(["기타", "Uncategorized"], "Travel") == ["Travel"]

def test_code_like_categories_are_hidden():
    labels = ["{{ broken_code }}", "<script>alert(1)</script>", "Skincare"]
    assert publication_board.clean_category_labels(labels, "K-Beauty Reviews") == ["Skincare"]

def test_real_categories_are_preserved_without_duplicates():
    assert publication_board.clean_category_labels(["Skincare", "Skincare", "Wellness"], "K-Beauty Reviews") == ["Skincare", "Wellness"]
