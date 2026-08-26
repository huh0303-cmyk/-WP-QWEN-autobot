import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import openai_text


class PaidImageBlockTests(unittest.TestCase):
    def test_text_enabled_does_not_enable_images(self):
        with patch.object(openai_text, "OPENAI_API_KEY", "test"), \
             patch.object(openai_text, "OPENAI_ENABLED", True), \
             patch.object(openai_text, "OPENAI_IMAGE_ENABLED", False), \
             patch("openai_text.requests.post") as post:
            output = Path(tempfile.gettempdir()) / "must-not-exist-paid-image.png"
            self.assertFalse(openai_text.openai_generate_image("test", str(output)))
            post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
