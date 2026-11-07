"""Site-specific headline guardrails for Korea Invest 365."""
from __future__ import annotations

import re


_KINVEST_GENERIC_OPENER = re.compile(r"^\s*(?:south\s+korean|korean)\b", re.IGNORECASE)


def kinvest_title_issues(title: str) -> list[str]:
    """Reject generic country-adjective openers; keep the real subject first."""
    if _KINVEST_GENERIC_OPENER.search(title or ""):
        return ["generic Korea-adjective opener (South Korean/Korean)"]
    return []
