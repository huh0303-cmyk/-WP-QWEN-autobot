import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scripts.audit_gsc_post_index import posts


def _response(status, payload=None, text=""):
    response = Mock(status_code=status, text=text)
    response.json.return_value = payload or []
    if status >= 400:
        response.raise_for_status.side_effect = RuntimeError(status)
    return response


def test_inventory_reduces_page_size_after_server_error():
    responses = [_response(500), _response(200, [{"id": 1}])]
    with patch("scripts.audit_gsc_post_index.requests.get", side_effect=responses) as get, patch("scripts.audit_gsc_post_index.time.sleep"):
        assert posts("https://example.com") == [{"id": 1}]
    assert get.call_args_list[0].kwargs["params"]["per_page"] == 100
    assert get.call_args_list[1].kwargs["params"]["per_page"] == 20
