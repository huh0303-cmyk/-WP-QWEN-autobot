import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import replicate_image_provider as provider


def test_blog_image_order_is_sdxl_then_flux_only():
    assert provider.ALLOWED_MODELS == (
        "bytedance/sdxl-lightning-4step",
        "black-forest-labs/flux-schnell",
    )


def test_both_image_failures_return_none_instead_of_blocking():
    provider._prompt_cache.clear()
    provider._attempted_prompts.clear()
    failed = {"status": "failed", "error": "test failure"}
    with patch.object(provider, "_token", return_value="test-token"), patch.object(
        provider, "_create_prediction", return_value=failed
    ) as create:
        assert provider.generate_image_url("test subject", theme="test") is None
    assert [call.args[0] for call in create.call_args_list] == list(provider.ALLOWED_MODELS)
