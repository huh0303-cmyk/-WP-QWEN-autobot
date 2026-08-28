# WordPress Site Count Reconciliation — 2026-08-27

## Evidence compared

- `config/automation_hub_sites.json`
- Google Sheet `자동화_사이트설정`
- Google Sheet historical `27개블로그`
- `scripts/daily_site_traffic.py`
- active WordPress workflow secret profiles

All operational sources describe the same 27 destinations: 25 ordinary WordPress blogs
plus `koreanews365.com` and `theseouljournal.com` as two newsroom properties.

No additional domain appears in the Sheet that is absent from the repository registry.
Therefore the planning phrase “WP 26 + newsrooms 2” cannot be reconciled to an exact
missing domain from current evidence. It is treated as a planning/counting discrepancy,
not authorization to invent or restore a site.

## Decision

Keep the canonical operational count at 25 ordinary + 2 newsroom until the owner names
the 26th ordinary property or confirms that one newsroom was included in the reported
26. No site/config/secret was added or removed during reconciliation.
