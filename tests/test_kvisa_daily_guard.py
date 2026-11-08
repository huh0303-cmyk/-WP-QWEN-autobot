import importlib.util
from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("kvisa_guard", Path(__file__).resolve().parents[1] / "scripts/kvisa_daily_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def reply(body, status=200, text="", pages="1"):
    response = Mock(status_code=status, text=text, headers={"X-WP-TotalPages": pages})
    response.json.return_value = body
    return response


class DailyGateTests(unittest.TestCase):
    now = datetime(2026, 11, 9, 9, 17, tzinfo=guard.KST)
    user = {"capabilities": {"publish_posts": True}}

    def check(self, published=(), future=()):
        session = Mock()
        session.get.side_effect = [reply(self.user), reply(list(published)), reply(list(future))]
        return guard.check(session, self.now)

    def test_empty_day_allows_one_publication(self):
        self.assertTrue(self.check()["should_publish"])

    def test_kst_day_boundary_blocks_duplicate(self):
        post = {"id": 1, "status": "publish", "date_gmt": "2026-11-08T15:00:00"}
        self.assertFalse(self.check([post])["should_publish"])

    def test_previous_day_does_not_block(self):
        post = {"id": 1, "status": "publish", "date_gmt": "2026-11-08T14:59:59"}
        self.assertTrue(self.check([post])["should_publish"])

    def test_future_post_today_blocks_duplicate(self):
        post = {"id": 2, "status": "future", "date_gmt": "2026-11-09T12:00:00"}
        self.assertFalse(self.check(future=[post])["should_publish"])

    def test_challenge_fails_closed(self):
        session = Mock()
        session.get.return_value = reply(None, 403, "Checking your browser before accessing")
        with self.assertRaisesRegex(RuntimeError, "HOSTINGER_BROWSER_CHALLENGE"):
            guard.check(session, self.now)

    def test_auth_failure_fails_closed(self):
        session = Mock()
        session.get.return_value = reply(None, 401)
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            guard.check(session, self.now)

    def test_permission_required(self):
        session = Mock()
        session.get.return_value = reply({"capabilities": {"edit_posts": True}})
        with self.assertRaisesRegex(RuntimeError, "publish_posts"):
            guard.check(session, self.now)

    def test_verification_needs_public_post_not_future(self):
        session = Mock()
        session.get.side_effect = [reply(self.user), reply([]), reply([])]
        with self.assertRaisesRegex(RuntimeError, "NO_PUBLICATION_RECEIPT"):
            guard.check(session, self.now, verify=True)


if __name__ == "__main__":
    unittest.main()
