#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kworld365.com에 Privacy Policy 페이지 생성 (AdSense 필수 요건)"""
import os, requests

WP_USER = "huh0303@gmail.com"
SITE_URL = "https://kworld365.com"
WP_PASS = os.getenv("KWORLD365COM", "")

PRIVACY_HTML = """
<p>Last updated: 2026</p>

<p>Kworld365.com ("we", "our", "us") respects your privacy. This Privacy Policy explains how we
collect, use, and protect information when you visit our website.</p>

<h2>Information We Collect</h2>
<p>We may collect non-personal information such as browser type, device information, pages visited,
and time spent on our site through cookies and similar technologies, primarily via Google Analytics.</p>

<h2>Google AdSense and Cookies</h2>
<p>This site uses Google AdSense, a third-party advertising service. Google, as a third-party vendor,
uses cookies (such as the DoubleClick cookie) to serve ads based on your prior visits to this and
other websites. Google's use of advertising cookies enables it and its partners to serve ads based
on your visit to our site and/or other sites on the Internet.</p>
<p>You may opt out of personalized advertising by visiting
<a href="https://adssettings.google.com" target="_blank" rel="noopener">Google Ads Settings</a>.</p>

<h2>Google Analytics</h2>
<p>We use Google Analytics to understand how visitors interact with our site. Google Analytics
collects information anonymously and reports website trends without identifying individual visitors.</p>

<h2>Third-Party Links</h2>
<p>Our site may contain links to third-party websites. We are not responsible for the privacy
practices or content of those external sites.</p>

<h2>Children's Privacy</h2>
<p>Our site is not directed at children under 13, and we do not knowingly collect personal
information from children.</p>

<h2>Your Consent</h2>
<p>By using our website, you consent to our Privacy Policy.</p>

<h2>Changes to This Policy</h2>
<p>We may update this Privacy Policy from time to time. Changes will be posted on this page.</p>

<h2>Contact Us</h2>
<p>If you have any questions about this Privacy Policy, please contact us via our
<a href="https://kworld365.com/contact/">Contact page</a>.</p>
"""


def main():
    if not WP_PASS:
        print("❌ KWORLD365COM 비밀번호 없음")
        return

    payload = {
        "title": "Privacy Policy",
        "slug": "privacy-policy",
        "content": PRIVACY_HTML,
        "status": "publish",
    }
    r = requests.post(f"{SITE_URL}/wp-json/wp/v2/pages",
                      auth=(WP_USER, WP_PASS), json=payload, timeout=20)
    print(f"HTTP {r.status_code}")
    if r.status_code in (200, 201):
        print(f"✅ Privacy Policy 페이지 생성 완료: {r.json().get('link')}")
    else:
        print(f"❌ 생성 실패: {r.text[:300]}")


if __name__ == "__main__":
    main()
