#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current blog publisher entrypoint.

Keeps the mature autopost_mega engine while applying current operational metadata that
must not regress to legacy labels retained in the large historical module.
"""
import autopost_mega as base

# kskin365.com was restored to the active 25-blog network. The legacy module still carried
# a stale 'Retired Site' author label, which must never reach newly published content.
kskin_author = {
    "name": "Korean Skincare Editorial Desk",
    "email": "editor@kskin365.com",
    "slug": "kskin365-com-desk",
    "bio": (
        "Korean Skincare Editorial Desk. Source-checked ingredient, routine and skin-safety "
        "guidance within this site's editorial scope."
    ),
}
base.AUTHOR_BY_SITE_DEF["kskin365.com"] = kskin_author
base.AUTHOR_BY_SITE["kskin365.com"] = kskin_author

if __name__ == "__main__":
    base.main()
