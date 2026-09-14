import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("vps_deploy", Path(__file__).resolve().parents[1] / "deploy/vps/sync_main.py")
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.test")
        self.git("config", "user.name", "Test")
        self.put("scripts/app.py", "value = 1\n")
        self.put("data/live.json", "original")
        self.git("add", ".")
        self.git("commit", "-qm", "initial")
        self.old = self.git("rev-parse", "HEAD").strip()
        self.calls = []

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE).decode()

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def target(self, code="value = 2\n"):
        self.put("scripts/app.py", code)
        self.put("data/live.json", "upstream snapshot")
        self.git("add", ".")
        self.git("commit", "-qm", "update")
        new = self.git("rev-parse", "HEAD").strip()
        self.git("reset", "--hard", self.old)
        self.put("data/live.json", "production state")
        self.put(".env", "do not touch")
        return new

    def test_deploy_preserves_runtime_and_records_revision(self):
        new = self.target()
        deploy.deploy(self.root, new, self.calls.append, lambda: None)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), new)
        self.assertEqual((self.root / "scripts/app.py").read_text(), "value = 2\n")
        self.assertEqual((self.root / "data/live.json").read_text(), "production state")
        self.assertEqual((self.root / ".env").read_text(), "do not touch")
        self.assertEqual(self.calls, ["stop", "start"])

    def test_health_failure_rolls_back(self):
        new = self.target()
        attempts = []
        def health():
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("unhealthy")
        with self.assertRaisesRegex(RuntimeError, "unhealthy"):
            deploy.deploy(self.root, new, self.calls.append, health)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), self.old)
        self.assertEqual((self.root / "scripts/app.py").read_text(), "value = 1\n")
        self.assertEqual((self.root / "data/live.json").read_text(), "production state")
        self.assertEqual(json.loads((self.root / "data/deploy-status.json").read_text())["failed_commit"], new)

    def test_conflicting_hotfix_is_not_overwritten(self):
        new = self.target()
        self.put("scripts/app.py", "value = 999\n")
        with self.assertRaisesRegex(RuntimeError, "Unmerged server code"):
            deploy.deploy(self.root, new, self.calls.append, lambda: None)
        self.assertFalse(self.calls)

    def test_already_applied_hotfix_is_accepted(self):
        new = self.target()
        self.put("scripts/app.py", "value = 2\n")
        deploy.deploy(self.root, new, self.calls.append, lambda: None)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), new)

    def test_bad_python_never_stops_services(self):
        new = self.target("invalid python !")
        with self.assertRaises(SyntaxError):
            deploy.deploy(self.root, new, self.calls.append, lambda: None)
        self.assertFalse(self.calls)

    def test_untracked_code_collision_is_preserved(self):
        self.put("scripts/new.py", "value = 3\n")
        self.git("add", ".")
        self.git("commit", "-qm", "new code")
        new = self.git("rev-parse", "HEAD").strip()
        self.git("reset", "--hard", self.old)
        self.put("scripts/new.py", "value = 999\n")
        with self.assertRaisesRegex(RuntimeError, "Unmerged server code"):
            deploy.deploy(self.root, new, self.calls.append, lambda: None)

    def test_process_interruption_recovers_on_next_run(self):
        new = self.target()
        with self.assertRaises(KeyboardInterrupt):
            deploy.deploy(self.root, new, self.calls.append, lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), new)
        deploy.recover_interrupted(self.root, self.calls.append, lambda: None)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), self.old)
        self.assertEqual((self.root / "scripts/app.py").read_text(), "value = 1\n")


if __name__ == "__main__":
    unittest.main()
