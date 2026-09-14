import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import three_model_consensus as review

@pytest.mark.parametrize('response,approved', [
    ('{"ok":true,"issues":["Incorrect attribution"]}', False),
    ('{"ok":true,"issues":[],"suggestions":["Shorter title optional"]}', True),
    ('{"ok":true}', False),
    ('{"ok":false,"issues":[]}', False),
])
def test_approval_cannot_override_reported_errors(monkeypatch,response,approved):
    monkeypatch.setattr(review,'openai_available',lambda:True)
    monkeypatch.setattr(review,'openai_generate_text',Mock(return_value=response))
    assert review._gpt_check('first','Review source evidence')['ok'] is approved
