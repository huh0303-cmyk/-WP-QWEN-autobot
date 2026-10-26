"""Fail fast if network-wide editorial gates stop rejecting known AI title templates."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation_hub.editorial_language_policy import body_cliches, title_cliches

BAD_TITLES = (
    "Understanding Korea Rental Deposits",
    "Navigating Health Insurance Options",
    "Managing Tax Obligations",
    "Preparing for University Applications",
)
for title in BAD_TITLES:
    issues = title_cliches(title)
    if not issues:
        raise SystemExit(f"editorial title gate failed to reject: {title}")
if title_cliches("Korea Rental Deposits: What Tenants Pay"):
    raise SystemExit("editorial title gate incorrectly rejected a subject-led title")
if not body_cliches("In today's fast-paced world, readers need answers."):
    raise SystemExit("editorial body gate failed to reject a known filler phrase")
print("Editorial gate preflight passed")
