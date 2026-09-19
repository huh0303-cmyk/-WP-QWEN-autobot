# GSC Indexed Master Snapshot

`gsc_indexed_master_60.csv` is a point-in-time export of the Google Drive
spreadsheet **`gsc_indexed_master_60`** (owner: huh0303@gmail.com), which is
the single source of truth for "which URLs Google has actually indexed" per
site, per the CEO's [[business_model_overview]] / GSC-first policy.

- Exported: 2026-09-19
- Columns: `platform,site,indexed_count,url,last_crawled`
- Covers all 27 network sites (regular WP + news + blogspot mirrors)

`scripts/wp_category_consolidation_audit.py` reads this file and filters by
`site == <target domain>` to build the protected-post list. It never calls
the WordPress REST API to *guess* what's indexed — this snapshot is the only
accepted source, per explicit instruction.

**To refresh:** re-export the Drive sheet as CSV and overwrite this file.
The audit script only trusts rows present here; if a site is missing from
this file the script aborts for that site rather than assuming zero index.
