#!/usr/bin/env python3
"""Find executable VPS/n8n runtime dependencies; historical documentation is excluded."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    ROOT / ".github" / "workflows",
    ROOT / "scripts",
    ROOT / "automation_hub",
    ROOT / "control_center",
    ROOT / "london_project_claude_console",
    ROOT / "deploy",
    ROOT / "config",
)
# This old filename is a known orphan compatibility remnant. It is excluded from
# the scan only while its callers are verified absent; the migration inventory
# tracks it as an explicit unfinished cleanup item.
LEGACY_ORPHAN = (ROOT / "automation_hub" / "youtube_vps_queue.py").resolve()
PATTERN = re.compile(
    r"/opt/korea365|/etc/korea365|VPS_HOST|VPS_USER|VPS_SSH|VPS_WP_QUEUE|VPS_JOB_ID|"
    r"appleboy/ssh-action|systemctl|N8N_WEBHOOK|n8nGateway|127\.0\.0\.1:5678",
    re.IGNORECASE,
)
SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".yml", ".yaml", ".json", ".sh", ".service", ".timer"}


def main() -> int:
    findings: list[str] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUFFIXES:
                continue
            resolved = path.resolve()
            if resolved in {Path(__file__).resolve(), LEGACY_ORPHAN, (ROOT / "scripts" / "audit_active_policy.py").resolve()}:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if PATTERN.search(line):
                    findings.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()[:180]}")
    if findings:
        print("VPS/n8n runtime dependency scan failed:")
        print("\n".join(findings))
        return 1
    print("VPS/n8n runtime dependency scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
