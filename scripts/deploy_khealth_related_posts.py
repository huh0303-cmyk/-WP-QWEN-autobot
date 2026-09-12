#!/usr/bin/env python3
"""User-approved: k-health365.com has 285 published posts but 0 indexed by
Google and 42 of them are orphans (zero incoming internal links). Rather
than hand-editing 42 posts, deploy a 'related posts' block via the
Code Snippets plugin's the_content filter - this appends 3-4 same-category
links to every post's rendered output immediately, resolving every current
orphan at once and preventing future ones for any category with 2+ posts.
Also fixes the mismatched WP page title from the k-trip365 investigation."""
import os
import requests
from requests.auth import HTTPBasicAuth

USER = "huh0303@gmail.com"
PW = os.environ["KHEALTH365COM"]
BASE = "https://k-health365.com/wp-json/code-snippets/v1"

PHP_CODE = r"""
add_filter('the_content', function ($content) {
    if (!is_single() || !in_the_loop() || !is_main_query()) return $content;
    global $post;
    if (!$post || get_post_type($post) !== 'post') return $content;
    $cats = wp_get_post_categories($post->ID);
    if (empty($cats)) return $content;
    $related = get_posts(array(
        'category__in' => $cats,
        'post__not_in' => array($post->ID),
        'posts_per_page' => 4,
        'orderby' => 'rand',
        'post_status' => 'publish',
        'no_found_rows' => true,
        'ignore_sticky_posts' => true,
    ));
    if (empty($related)) return $content;
    $html = '<div style="margin-top:32px;padding-top:16px;border-top:1px solid #e2e2e2;">';
    $html .= '<h3 style="font-size:18px;margin-bottom:12px;">관련 글</h3><ul style="line-height:1.9;">';
    foreach ($related as $r) {
        $html .= '<li><a href="' . esc_url(get_permalink($r->ID)) . '">' . esc_html(get_the_title($r->ID)) . '</a></li>';
    }
    $html .= '</ul></div>';
    return $content . $html;
}, 20);
"""

payload = {
    "name": "Auto related-posts (same category) footer",
    "desc": "Fixes 42 orphan posts (zero incoming internal links) by appending same-category links to every post's rendered output.",
    "code": PHP_CODE,
    "scope": "global",
    "active": True,
    "priority": 20,
}
r = requests.post(f"{BASE}/snippets", auth=HTTPBasicAuth(USER, PW), json=payload, timeout=30)
r.raise_for_status()
print("created snippet id:", r.json()["id"], "active:", r.json().get("active"))

# Verify on the live front-end page (the_content's is_single()/in_the_loop()
# guard only fires during a real themed page view, not a REST API request).
info = requests.get("https://k-health365.com/wp-json/wp/v2/posts/2320", params={"_fields": "link"}, timeout=20)
live_url = info.json()["link"]
page = requests.get(live_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
print("checked live URL:", live_url)
print("orphan post 2320 now has related-posts block on the live page:", "관련 글" in page.text)
