import importlib.util
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("recovery",ROOT/"scripts/koreanews_daily_recovery.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_full_day_does_not_start_writer():
    with tempfile.TemporaryDirectory() as temp:
        previous=os.getcwd()
        try:
            os.chdir(temp)
            Path("artifacts").mkdir()
            with patch.dict(os.environ,{"TARGET_SITE_URL":module.SITE,"KOREANEWS_RECOVERY_BATCH":"5"}), patch.object(module,"inventory",return_value=[{"id":i} for i in range(5)]), patch.object(module.subprocess,"run") as run:
                module.main()
                run.assert_not_called()
        finally: os.chdir(previous)

def test_attempts_stop_at_quota():
    with tempfile.TemporaryDirectory() as temp:
        previous=os.getcwd()
        try:
            os.chdir(temp)
            Path("artifacts").mkdir()
            with patch.dict(os.environ,{"TARGET_SITE_URL":module.SITE,"KOREANEWS_RECOVERY_BATCH":"5"}), patch.object(module,"inventory",side_effect=[[],[],[{}]*5,[{}]*5]), patch.object(module.subprocess,"run") as run:
                run.return_value.returncode=0
                module.main()
                assert run.call_count==1
        finally: os.chdir(previous)
