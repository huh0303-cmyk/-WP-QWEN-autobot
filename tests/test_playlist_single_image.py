import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import youtube_playlist_maker as maker


class PlaylistSingleImageTests(unittest.TestCase):
    @patch.object(maker, "download_drive_file")
    @patch.object(maker, "list_folder_files")
    def test_selects_and_downloads_exactly_one_existing_image(self, listing, download):
        listing.return_value = [
            {"id": "one", "name": "one.jpg"},
            {"id": "two", "name": "two.png"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = maker.select_single_bank_image(directory, object())
        self.assertEqual(1, download.call_count)
        self.assertTrue(result.endswith((".jpg", ".png")))


if __name__ == "__main__":
    unittest.main()
