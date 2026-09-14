#!/usr/bin/env python3
"""Pull main on the VPS; preserve runtime files and roll back failed code releases."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

CODE_ROOTS = {".github", "automation_hub", "control_center", "scripts", "config", "deploy", "tests", "tools", "multilang_quiz"}
SERVICES = ["korea365-control.service", "korea365-operations.service", "korea365-youtube-worker.service"]


def managed(name):
    p = Path(name)
    return p.parts[0] in CODE_ROOTS or (len(p.parts) == 1 and (p.suffix == ".py" or name.startswith("requirements")))


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE, timeout=90)


def blob(root, revision, name):
    try:
        return git(root, "show", f"{revision}:{name}")
    except subprocess.CalledProcessError:
        return None


def write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        path.unlink(missing_ok=True)
        return
    fd, tmp = tempfile.mkstemp(prefix=".deploy-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def state(root, status, **extra):
    path = root / "data/deploy-status.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    previous.update(status=status, checked_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **extra)
    write(path, json.dumps(previous, ensure_ascii=False, indent=2).encode(), 0o600)
    print(json.dumps({"status": status, **extra}), flush=True)


def service(action):
    subprocess.run(["systemctl", action, *SERVICES], check=True, timeout=90, capture_output=True)


def healthy():
    for _ in range(15):
        try:
            subprocess.run(["systemctl", "is-active", "--quiet", *SERVICES], check=True, timeout=10)
            with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=5) as response:
                if response.status == 200 and json.load(response).get("status") == "ok":
                    time.sleep(2)
                    subprocess.run(["systemctl", "is-active", "--quiet", *SERVICES], check=True, timeout=10)
                    return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Service health checks failed")


def recover_interrupted(root, control=service, check=healthy):
    status_path = root / "data/deploy-status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    if not status.get("recovery_pending"):
        return
    backup = Path(status["backup"]).resolve()
    if not backup.is_relative_to((root / "data/deployment-backups").resolve()):
        raise RuntimeError("Invalid deployment recovery path")
    manifest = json.loads((backup / "manifest.json").read_text())
    control("stop")
    for entry in manifest["files"]:
        name = entry["path"]
        if not managed(name) or not (root / name).resolve().is_relative_to(root):
            raise RuntimeError("Invalid deployment recovery file")
        write(root / name, (backup / name).read_bytes() if entry["existed"] else None, entry["mode"])
    git(root, "reset", "--mixed", manifest["previous"])
    control("start")
    check()
    state(root, "rolled_back", deployed_commit=manifest["previous"], failed_commit=manifest["target"], recovery_pending=False)


def deploy(root, target, control=service, check=healthy):
    old = git(root, "rev-parse", "HEAD").decode().strip()
    names = git(root, "diff", "--name-only", "-z", old, target).decode().split("\0")
    dirty = git(root, "diff", "--name-only", "-z", "HEAD").decode().split("\0")
    names = sorted({n for n in names + dirty if n and managed(n)})
    changes = []
    for name in names:
        path = root / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root and root in p.parents):
            raise RuntimeError(f"Refusing symlink code path: {name}")
        current = path.read_bytes() if path.exists() else None
        before, after = blob(root, old, name), blob(root, target, name)
        if current not in (before, after):
            raise RuntimeError(f"Unmerged server code must be reviewed: {name}")
        if current == after:
            continue
        if Path(name).name.startswith("requirements"):
            raise RuntimeError(f"Dependency change requires a tested environment update: {name}")
        if after is not None and name.endswith(".py"):
            compile(after, name, "exec")
        changes.append((name, current, after, path.stat().st_mode & 0o777 if path.exists() else 0o644))
    if old == target and not changes:
        state(root, "current", deployed_commit=old)
        return
    backup = root / "data/deployment-backups" / (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + target[:12])
    backup.mkdir(parents=True, exist_ok=False)
    os.chmod(backup, 0o700)
    manifest = []
    for name, before, after, mode in changes:
        if before is not None:
            write(backup / name, before, mode)
        manifest.append({"path": name, "existed": before is not None, "mode": mode})
    write(backup / "manifest.json", json.dumps({"previous": old, "target": target, "files": manifest}).encode(), 0o600)
    state(root, "deploying", target_commit=target, previous_commit=old, backup=str(backup), recovery_pending=True)
    try:
        if changes:
            control("stop")
        for name, before, after, mode in changes:
            write(root / name, after, mode)
        # Update the revision/index only. Runtime data are NEVER checked out or cleaned.
        git(root, "reset", "--mixed", target)
        if changes:
            control("start")
        check()
    except Exception:
        if changes:
            control("stop")
        for name, before, after, mode in changes:
            write(root / name, before, mode)
        git(root, "reset", "--mixed", old)
        if changes:
            control("start")
        state(root, "rolled_back", deployed_commit=old, failed_commit=target, recovery_pending=False)
        check()
        raise
    state(root, "deployed", deployed_commit=target, changed_files=[c[0] for c in changes], failed_commit=None, reason=None, recovery_pending=False)


def main():
    root = Path(os.environ.get("KOREA365_ROOT", "/opt/korea365")).resolve()
    queue = root / "data/youtube_vps_queue"
    queue.mkdir(parents=True, exist_ok=True)
    with (root / "data/deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            git(root, "fetch", "origin", "main")
            target = git(root, "rev-parse", "refs/remotes/origin/main").decode().strip()
            with (queue / "worker.lock").open("a") as video_lock:
                try:
                    fcntl.flock(video_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    state(root, "waiting_for_video", target_commit=target)
                    return
                if list((queue / "running").glob("*.json")):
                    state(root, "waiting_for_video", target_commit=target)
                    return
                recover_interrupted(root)
                previous = json.loads((root / "data/deploy-status.json").read_text()) if (root / "data/deploy-status.json").exists() else {}
                if previous.get("failed_commit") == target:
                    state(root, "waiting_for_fix", target_commit=target)
                    return
                deploy(root, target)
        except Exception as exc:
            # No subprocess stderr: remote URLs might contain credentials.
            state(root, "error", reason=str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
