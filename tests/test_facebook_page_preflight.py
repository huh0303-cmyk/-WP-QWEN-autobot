import unittest
from unittest.mock import Mock

from scripts.facebook_page_preflight import inspect_page

class FacebookPreflightTests(unittest.TestCase):
    def test_missing_credentials_fail_closed(self):
        session = Mock()
        result = inspect_page("english", "", "", session=session)
        self.assertEqual(result["status"], "MISSING_PAGE_ID_OR_ACCESS_TOKEN")
        session.get.assert_not_called()
        self.assertFalse(result["publication_performed"])

    def test_page_identity_is_verified_but_write_task_remains_unconfirmed(self):
        response = Mock(status_code=200, content=b"{}")
        response.json.return_value = {"id": "123", "name": "English Page"}
        session = Mock()
        session.get.return_value = response
        result = inspect_page("english", "123", "not-printed", session=session)
        self.assertEqual(result["status"], "PAGE_IDENTITY_VERIFIED_WRITE_TASK_UNCONFIRMED")
        self.assertFalse(result["publication_performed"])
        self.assertNotIn("not-printed", repr(result))

    def test_identity_without_create_task_is_not_write_verified(self):
        response = Mock(status_code=200, content=b"{}")
        response.json.return_value = {"id": "123", "name": "English Page"}
        session = Mock()
        session.get.return_value = response
        result = inspect_page("english", "123", "token", session=session)
        self.assertEqual(result["status"], "PAGE_IDENTITY_VERIFIED_WRITE_TASK_UNCONFIRMED")

    def test_wrong_page_id_is_rejected(self):
        response = Mock(status_code=200, content=b"{}")
        response.json.return_value = {"id": "999", "name": "Other Page"}
        session = Mock()
        session.get.return_value = response
        result = inspect_page("english", "123", "token", session=session)
        self.assertEqual(result["status"], "INVALID_OR_UNAUTHORIZED_PAGE_TOKEN")

if __name__ == "__main__":
    unittest.main()
