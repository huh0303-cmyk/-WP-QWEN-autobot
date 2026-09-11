import sys
from pathlib import Path
from unittest.mock import patch
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import editorial_brief as planner

def test_planning_failure_does_not_block_or_repeat(monkeypatch):
    monkeypatch.setenv('GEMINI_EDITOR_ENABLED','true')
    monkeypatch.setenv('GEMINI_API_KEY','test')
    planner.CACHE.clear()
    with patch.object(planner.requests,'post',side_effect=requests.Timeout) as post:
        assert planner.editorial_brief('specific topic') == ''
        assert planner.editorial_brief('specific topic') == ''
        assert post.call_count == 1
        settings=post.call_args.kwargs['json']['generationConfig']
        assert settings['maxOutputTokens'] == 512
        assert settings['thinkingConfig']['thinkingBudget'] == 0

def test_planning_disabled_means_no_api(monkeypatch):
    monkeypatch.delenv('GEMINI_EDITOR_ENABLED',raising=False)
    with patch.object(planner.requests,'post') as post:
        assert planner.editorial_brief('topic') == ''
        post.assert_not_called()
