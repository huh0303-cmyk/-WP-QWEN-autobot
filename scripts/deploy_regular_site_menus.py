#!/usr/bin/env python3
"""Keep category navigation and show four required information pages in a top bar on all 25 WP blogs."""
from __future__ import annotations

import os
import sys
import json
from urllib.parse import urlparse

import requests

try:
    from .site_registry import SITES
except ImportError:  # Direct execution: python scripts/deploy_regular_site_menus.py
    from site_registry import SITES

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
REGULAR_SITES = SITES[:-2]
UTILITY = (
    ("about", "About Us"),
    ("contact", "Contact Us"),
    ("disclaimer", "Disclaimer"),
    ("privacy-policy", "Privacy Policy"),
)
SNIPPET_NAME = "Network utility footer and one-line category menu"


def is_utility_footer_snippet(item: dict) -> bool:
    """Match only the managed footer renderer, never a comment/reference.

    The visitor counter intentionally mentions ``network-utility-topbar`` in
    a comment to explain ordering. A loose substring check therefore disabled
    the real counter as if it were a duplicate footer.
    """
    code = str(item.get("code", ""))
    return item.get("name") == SNIPPET_NAME or '<nav class="network-utility-topbar"' in code


def api(site, password, method, path, **kwargs):
    response = requests.request(
        method,
        f"{site.rstrip('/')}/wp-json/{path.lstrip('/')}",
        auth=(WP_USER, password),
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def snippet_api(site, password, method, path, **kwargs):
    response = requests.request(
        method,
        f"{site.rstrip('/')}/wp-json/code-snippets/v1/{path.lstrip('/')}",
        auth=(WP_USER, password),
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def deploy_footer_fallback(site, password, pages):
    """Make the four utility links visible even when a theme has no footer menu slot."""
    links = []
    for slug, english_title in UTILITY:
        page = pages[slug]
        title = page.get("title", {}).get("rendered") or english_title
        links.append((title, page["link"]))
    php_links = ",\n        ".join(
        f"array({json.dumps(title, ensure_ascii=False)}, {json.dumps(url, ensure_ascii=False)})"
        for title, url in links
    )
    code = f'''// Managed by deploy_regular_site_menus.py. Do not remove.
add_action('init', function () {{
    $category_menu = get_term_by('slug', 'network-categories', 'nav_menu');
    $utility_menu = get_term_by('slug', 'network-utility', 'nav_menu');
    if (!$category_menu || !$utility_menu) return;
    $registered = get_registered_nav_menus();
    $locations = get_theme_mod('nav_menu_locations', array());
    foreach (array('primary', 'menu-1', 'main', 'header') as $candidate) {{
        if (array_key_exists($candidate, $registered)) {{ $locations[$candidate] = $category_menu->term_id; break; }}
    }}
    // The four information pages are rendered in a dedicated top row, not in the footer menu.
    foreach ($registered as $location => $label) {{
        $key = strtolower($location . ' ' . $label);
        if (strpos($key, 'footer') !== false) unset($locations[$location]);
    }}
    set_theme_mod('nav_menu_locations', $locations);
}}, 99);
// Keep the four information pages out of the category menu; the managed top bar links to them directly.
add_filter('wp_nav_menu_objects', function ($items, $args) {{
    $location = strtolower(isset($args->theme_location) ? $args->theme_location : '');
    if (strpos($location, 'footer') !== false) return $items;
    $blocked = array('about', 'about-us', 'contact', 'contact-us', 'disclaimer', 'privacy', 'privacy-policy');
    return array_values(array_filter($items, function ($item) use ($blocked) {{
        $path = trim((string) parse_url($item->url, PHP_URL_PATH), '/');
        return !in_array(strtolower($path), $blocked, true);
    }}));
}}, 999, 2);
$render_topbar = function () {{
    static $rendered = false;
    if ($rendered || is_admin()) return;
    $rendered = true;
    $links = array(
        {php_links}
    );
    echo '<nav class="network-utility-topbar" aria-label="Site information">';
    foreach ($links as $link) {{
        echo '<a href="' . esc_url($link[1]) . '">' . esc_html($link[0]) . '</a>';
    }}
    echo '</nav>';
    // If a theme calls wp_body_open late or lacks it, move the row directly before the site header.
    echo '<script>(function(){{var n=document.querySelector(".network-utility-topbar");var h=document.querySelector("header.site-header,#masthead,.site-header,header");if(n&&h&&h.parentNode){{h.parentNode.insertBefore(n,h);}}}})();</script>';
}};
add_action('wp_body_open', $render_topbar, 5);
// Theme fallback: if the theme omits wp_body_open, still render the links.
add_action('wp_footer', $render_topbar, 1);
add_action('wp_head', function () {{
    echo '<style id="network-menu-layout-css">
    header .site-logo,header .custom-logo-link,header .custom-logo,
    .site-header .site-logo,.site-header .custom-logo-link,.site-header .custom-logo,
    .header-image,.site-branding img{{display:none!important}}
    .network-utility-topbar{{display:flex;justify-content:center;gap:24px;flex-wrap:wrap;padding:18px 12px;border-top:1px solid rgba(127,127,127,.25);font-size:14px}}
    .network-utility-topbar a{{text-decoration:none}}
    #site-navigation>div>ul,.main-navigation>div>ul,.primary-menu,.main-header-menu{{display:flex;flex-wrap:nowrap;white-space:nowrap;overflow-x:auto;scrollbar-width:thin}}
    @media(max-width:640px){{.network-utility-topbar{{gap:12px;font-size:12px}}}}
    </style>';
}}, 99);'''
    response = snippet_api(site, password, "GET", "snippets", params={"per_page": 100})
    snippets = response if isinstance(response, list) else response.get("data", response.get("items", []))
    candidates = [
        item for item in snippets
        if is_utility_footer_snippet(item)
    ]
    # Older deployments created a second active copy under a legacy name. Keep
    # one canonical snippet and deactivate every extra copy so the footer row
    # can never be printed twice.
    match = next((item for item in candidates if item.get("name") == SNIPPET_NAME), None)
    if match is None and candidates:
        match = candidates[0]
    payload = {
        "name": SNIPPET_NAME,
        "desc": "Four required information pages in a top row; category navigation stays separate.",
        "code": code,
        "scope": "global",
        "active": True,
        "priority": 10,
        "tags": ["navigation", "footer", "managed"],
    }
    path = f"snippets/{match['id']}" if match else "snippets"
    saved = snippet_api(site, password, "POST", path, json=payload)
    if not saved.get("active", False):
        raise RuntimeError("footer fallback snippet is not active")
    canonical_id = str(saved.get("id") or (match or {}).get("id") or "")
    disabled = 0
    for duplicate in candidates:
        if str(duplicate.get("id", "")) == canonical_id:
            continue
        inactive_payload = {
            "name": duplicate.get("name") or "Legacy duplicate utility footer",
            "desc": duplicate.get("desc") or duplicate.get("description") or "Disabled duplicate footer snippet.",
            "code": duplicate.get("code") or "// Disabled duplicate footer snippet.",
            "scope": duplicate.get("scope") or "global",
            "active": False,
            "priority": int(duplicate.get("priority") or 10),
            "tags": duplicate.get("tags") or ["footer", "duplicate", "disabled"],
        }
        stopped = snippet_api(site, password, "POST", f"snippets/{duplicate['id']}", json=inactive_payload)
        if stopped.get("active", True):
            raise RuntimeError(f"duplicate footer snippet {duplicate['id']} stayed active")
        disabled += 1
    return disabled


def ensure_menu(site, password, menus, *, name, slug):
    for menu in menus:
        if menu.get("slug") == slug or menu.get("name") == name:
            return int(menu.get("id") or menu.get("term_id"))
    created = api(site, password, "POST", "wp/v2/menus", json={"name": name, "slug": slug})
    return int(created.get("id") or created.get("term_id"))


def clear_menu(site, password, menu_id):
    items = api(site, password, "GET", "wp/v2/menu-items", params={"menus": menu_id, "per_page": 100})
    for item in items:
        api(site, password, "DELETE", f"wp/v2/menu-items/{item['id']}", params={"force": "true"})


def add_item(site, password, menu_id, *, object_id, object_type, title, order):
    payload = {
        "menus": menu_id,
        "object_id": int(object_id),
        "object": object_type,
        "type": "taxonomy" if object_type == "category" else "post_type",
        "title": title,
        "menu_order": order,
        "status": "publish",
    }
    api(site, password, "POST", "wp/v2/menu-items", json=payload)


def find_required_pages(site, password):
    pages = api(site, password, "GET", "wp/v2/pages", params={"per_page": 100, "status": "publish"})
    by_slug = {page.get("slug", ""): page for page in pages}
    aliases = {
        "privacy-policy": ("privacy-policy", "privacy"),
        "disclaimer": ("disclaimer",),
        "contact": ("contact", "contact-us"),
        "about": ("about", "about-us"),
    }
    found = {}
    for wanted, candidates in aliases.items():
        for slug in candidates:
            if slug in by_slug:
                found[wanted] = by_slug[slug]
                break
    templates = {
        "privacy-policy": "This Privacy Policy explains how this site handles basic technical, analytics, advertising, and contact information. We do not sell personal information. Contact us with privacy questions.",
        "disclaimer": "Information on this site is provided for general informational purposes. Verify time-sensitive requirements with the relevant official authority before making decisions.",
        "contact": "Use the site's published contact channel for corrections, questions, partnership inquiries, or requests concerning your information.",
        "about": "This independent editorial site publishes practical, source-led information for readers. We prioritize clarity, current official references, and transparent corrections.",
    }
    for slug, title in UTILITY:
        if slug in found:
            continue
        found[slug] = api(site, password, "POST", "wp/v2/pages", json={
            "slug": slug, "title": title, "content": f"<p>{templates[slug]}</p>", "status": "publish"
        })
    return found


def configure(site, secret_name):
    password = os.getenv(secret_name, "").strip()
    if not password:
        raise RuntimeError(f"missing secret {secret_name}")
    try:
        menus = api(site, password, "GET", "wp/v2/menus", params={"per_page": 100})
    except requests.HTTPError as exc:
        # Some hosts/WAF rules forbid the menu REST endpoints while allowing pages and Code Snippets.
        # In that case, still publish the four top-row links through the managed snippet.
        if exc.response is None or exc.response.status_code != 403:
            raise
        pages = find_required_pages(site, password)
        disabled_duplicates = deploy_footer_fallback(site, password, pages)
        return {
            "site": urlparse(site).netloc,
            "categories": [],
            "utility_pages": [
                pages[slug].get("title", {}).get("rendered") or title
                for slug, title in UTILITY
            ],
            "disabled_duplicate_footer_snippets": disabled_duplicates,
            "locations": "top-row fallback; menu REST API returned 403",
        }
    category_menu = ensure_menu(site, password, menus, name="Network Categories", slug="network-categories")
    utility_menu = ensure_menu(site, password, menus, name="Network Utility", slug="network-utility")
    clear_menu(site, password, category_menu)
    clear_menu(site, password, utility_menu)

    categories = api(site, password, "GET", "wp/v2/categories", params={
        "per_page": 100, "hide_empty": "false", "orderby": "count", "order": "desc"
    })
    categories = [c for c in categories if c.get("slug") != "uncategorized"][:4]
    if not categories:
        raise RuntimeError("no usable categories")
    for order, category in enumerate(categories, 1):
        add_item(site, password, category_menu, object_id=category["id"], object_type="category", title=category["name"], order=order)

    pages = find_required_pages(site, password)
    for order, (slug, english_title) in enumerate(UTILITY, 1):
        page = pages[slug]
        title = page.get("title", {}).get("rendered") or english_title
        add_item(site, password, utility_menu, object_id=page["id"], object_type="page", title=title, order=order)

    disabled_duplicates = deploy_footer_fallback(site, password, pages)

    category_items = api(site, password, "GET", "wp/v2/menu-items", params={"menus": category_menu, "per_page": 100})
    utility_items = api(site, password, "GET", "wp/v2/menu-items", params={"menus": utility_menu, "per_page": 100})
    if len(category_items) != len(categories) or len(utility_items) != 4:
        raise RuntimeError("menu re-read verification failed")
    return {
        "site": urlparse(site).netloc,
        "categories": [item.get("title", {}).get("rendered", "") for item in category_items],
        "utility_pages": [item.get("title", {}).get("rendered", "") for item in utility_items],
        "disabled_duplicate_footer_snippets": disabled_duplicates,
        "locations": "assigned by managed WordPress snippet",
    }


def main():
    if len(REGULAR_SITES) != 25:
        raise SystemExit("scope guard failed: expected exactly 25 regular sites")
    requested = os.getenv("TARGET_SITE_URL", "").strip().rstrip("/")
    targets = [row for row in REGULAR_SITES if not requested or row[0].rstrip("/") == requested]
    if requested and len(targets) != 1:
        raise SystemExit(f"unknown or non-regular TARGET_SITE_URL: {requested}")
    failed = []
    for index, (site, secret_name, _) in enumerate(targets, 1):
        try:
            result = configure(site, secret_name)
            print(f"[{index:02d}/{len(targets)}] OK {result}", flush=True)
        except Exception as exc:
            failed.append(f"{site}: {exc}")
            print(f"[{index:02d}/{len(targets)}] FAIL {site}: {exc}", flush=True)
    if failed:
        raise SystemExit("menu deployment incomplete:\n" + "\n".join(failed))


if __name__ == "__main__":
    main()
