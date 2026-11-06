#!/usr/bin/env python3
"""Publish Meta privacy and data-deletion pages to korea365.org.

Credentials are read only from GitHub Actions environment variables and are
never printed or persisted. The script updates the existing privacy page and
creates/updates one data-deletion instruction page.
"""
import os
import sys
import requests
from requests.auth import HTTPBasicAuth

BASE = "https://korea365.org/wp-json/wp/v2"
USER = os.getenv("WP_USER", "huh0303@gmail.com").strip()
PASSWORD = os.getenv("KOREA365ORG", "").strip()
TIMEOUT = 30

PRIVACY_HTML = """<h2>Privacy Policy</h2>
<p><strong>Korea365</strong> respects your privacy. This policy explains the information processed when you visit korea365.org and when you choose to connect an Instagram or Threads account to the SIS Center Publisher application operated by SeoulTopik Center.</p>
<p><strong>Effective date:</strong> 6 November 2026. This policy may be updated when the service or applicable requirements change.</p>
<h2>1. Information collected</h2>
<ul>
<li>Website information: contact details you voluntarily submit, and technical information such as IP address, browser/device information, cookies, access times and page activity.</li>
<li>Connected social account information: public profile name/username, platform account identifier and information returned by Meta during account authorization.</li>
<li>Publishing information: text, captions, images or videos selected for publication, publication status, media identifiers and public post/permalink URLs.</li>
<li>Authentication information: access tokens and related authorization data required to publish to the specific account you connect. These credentials are stored as restricted encrypted secrets in the project’s GitHub Actions environment and are not intentionally included in source code, logs or public records.</li>
</ul>
<h2>2. Purposes of processing</h2>
<ul>
<li>Authenticate the social account you expressly connect.</li>
<li>Create and publish content that has been prepared for the selected Instagram or Threads account.</li>
<li>Confirm publication results, prevent duplicate submissions and maintain an operational audit record.</li>
<li>Respond to privacy, support and account-disconnection requests.</li>
<li>Operate, secure and improve korea365.org.</li>
</ul>
<h2>3. Scope and user control</h2>
<p>The social publishing integration is limited to account identity and content-publishing functions authorized by the connected platform. It is not designed to read private messages, collect passwords, or access unrelated personal account content. Connecting an account is voluntary. You may revoke the application’s access in the relevant Meta account settings and request deletion of associated data using the instructions at <a href="https://korea365.org/data-deletion/">Data Deletion Instructions</a>.</p>
<h2>4. Sharing and service providers</h2>
<p>Content is transmitted to Meta (Instagram or Threads) only to perform the publication you have authorized. GitHub Actions is used to run the publishing workflow and protect its encrypted configuration. Website hosting, security, analytics and advertising providers may process limited technical information under their respective terms. Personal information is not sold.</p>
<h2>5. Retention and deletion</h2>
<p>Account authorization data is retained only while needed to provide the connected publishing service. Publication receipts may retain platform identifiers, timestamps and public URLs for operational audit and duplicate prevention. When an account is disconnected or a valid deletion request is received, associated credentials are revoked or deleted and related personal data is deleted unless retention is required for security, dispute resolution or applicable law.</p>
<h2>6. Cookies and advertising</h2>
<p>korea365.org may use essential cookies and, where enabled, analytics or advertising services such as Google AdSense. You can manage cookies through your browser settings and manage Google advertising preferences through Google’s ad settings.</p>
<h2>7. Your choices and requests</h2>
<p>You may request access, correction or deletion of personal information, or ask to disconnect a social account. Please use the <a href="https://korea365.org/data-deletion/">Data Deletion Instructions</a> page or contact <a href="mailto:koreacenter24@gmail.com">koreacenter24@gmail.com</a>. Do not email passwords, access tokens, verification codes or government identification numbers.</p>
<h2>8. Contact</h2>
<p>Privacy and data requests: <a href="mailto:koreacenter24@gmail.com">koreacenter24@gmail.com</a>.</p>
<h2>9. Policy changes</h2>
<p>Material changes will be reflected on this page with an updated effective date.</p>"""

DELETION_HTML = """<h2>Data Deletion Instructions</h2>
<p>This page explains how to request deletion of information associated with an Instagram or Threads account connected to the SIS Center Publisher social publishing service operated by SeoulTopik Center.</p>
<h2>1. Revoke access first (recommended)</h2>
<ol>
<li>Open the Instagram or Threads settings for the account you connected.</li>
<li>Find the Apps and Websites / Website permissions or authorized applications section.</li>
<li>Select SIS Center Publisher and remove or revoke its access, if it is listed.</li>
<li>If you cannot find the setting, contact us and we will guide you through disconnecting the account.</li>
</ol>
<h2>2. Request deletion by email</h2>
<p>Email <a href="mailto:koreacenter24@gmail.com?subject=Korea365%20Meta%20Data%20Deletion%20Request">koreacenter24@gmail.com</a> with the subject <strong>Korea365 Meta Data Deletion Request</strong>.</p>
<p>Please include:</p>
<ul>
<li>The platform: Instagram or Threads (or both).</li>
<li>The username/handle of the account to disconnect and delete.</li>
<li>A contact email address for the response.</li>
<li>A short statement confirming that you are the account holder or are authorized to make the request.</li>
</ul>
<p>Do not include your password, access token, login code, full government ID number or other unnecessary sensitive information. We may request proportionate information to verify control of the account before processing the request.</p>
<h2>3. What will be deleted</h2>
<ul>
<li>Stored access tokens and account-specific authentication details held for the publishing service.</li>
<li>Account identifiers and profile metadata held by the service, where no longer required.</li>
<li>Unpublished drafts and queued content associated with the account, where applicable.</li>
<li>Operational records that identify the account, except limited records that must be retained for security, legal compliance or dispute handling.</li>
</ul>
<p>Posts already published to Instagram or Threads are hosted by Meta and are not deleted automatically by deleting data held by Korea365. You can remove those posts directly in the relevant platform. This service will not attempt to delete your platform posts unless you separately request and authorize that action.</p>
<h2>4. Processing time and confirmation</h2>
<p>We will acknowledge the request, verify it where reasonably necessary, and complete deletion or explain any lawful retention exception within 30 days. If additional time is needed, we will notify you. A confirmation will be sent to the reply email address.</p>
<h2>5. Contact</h2>
<p>Data deletion contact: <a href="mailto:koreacenter24@gmail.com">koreacenter24@gmail.com</a>.</p>
<p>For more information, read the <a href="https://korea365.org/privacy-policy/">Privacy Policy</a>.</p>"""

TERMS_HTML = """<h2>Terms of Service</h2>
<p>SIS Center Publisher is an internal publishing tool operated by <strong>SeoulTopik Center</strong> for authorized operators who manage the Center's Instagram and Threads accounts.</p>
<p><strong>Effective date:</strong> 6 November 2026.</p>
<h2>1. Authorized use</h2><p>Only authorized operators may use the app. Users must connect only accounts they own or are authorized to manage and must complete Meta's own authorization process.</p>
<h2>2. Content and publishing</h2><p>Operators are responsible for ensuring that captions, images, videos, disclosures and other materials comply with applicable law, intellectual-property rights, privacy rights and Meta policies. Publishing depends on Meta API permissions and availability; a post is not considered published until its resulting post ID or URL is verified.</p>
<h2>3. Data and account disconnection</h2><p>The app processes only the account and publishing information needed for its functions. Account owners may revoke access through Meta settings and request deletion of app-held data using the <a href="https://korea365.org/data-deletion/">Data Deletion Instructions</a>.</p>
<h2>4. Prohibited use</h2><p>Unauthorized account access, spam, deceptive content, unlawful content, rights infringement, and attempts to bypass platform safeguards are prohibited.</p>
<h2>5. Changes and availability</h2><p>Features may change or become unavailable due to Meta API changes, permission limits, security requirements or maintenance.</p>
<h2>6. Contact</h2><p>SeoulTopik Center: <a href="mailto:koreacenter24@gmail.com">koreacenter24@gmail.com</a>.</p>
""" 

def request(method, path, **kwargs):
    response = requests.request(
        method, BASE + path, auth=HTTPBasicAuth(USER, PASSWORD),
        timeout=TIMEOUT, **kwargs
    )
    if not response.ok:
        raise RuntimeError(f"WordPress API failed: HTTP {response.status_code}")
    return response.json() if response.content else {}

def page_by_slug(slug):
    rows = request("GET", "/pages", params={"slug": slug, "context": "edit"})
    return rows[0] if rows else None

def upsert(slug, title, html):
    existing = page_by_slug(slug)
    payload = {"title": title, "content": html, "status": "publish"}
    if existing:
        result = request("POST", f"/pages/{existing['id']}", json=payload)
    else:
        result = request("POST", "/pages", json={**payload, "slug": slug})
    return result

def main():
    if not USER or not PASSWORD:
        raise SystemExit("Missing WordPress publishing credentials in Actions environment.")
    me = request("GET", "/users/me", params={"context": "edit"})
    if not me.get("id"):
        raise SystemExit("WordPress authentication was not verified.")
    privacy = upsert("privacy-policy", "Privacy Policy", PRIVACY_HTML)
    deletion = upsert("data-deletion", "Data Deletion Instructions", DELETION_HTML)
    terms = upsert("terms-of-service", "Terms of Service", TERMS_HTML)
    # Public read-back: require published pages and exact canonical links.
    checks = []
    for slug, expected in (
        ("privacy-policy", "https://korea365.org/privacy-policy/"),
        ("data-deletion", "https://korea365.org/data-deletion/"),
        ("terms-of-service", "https://korea365.org/terms-of-service/"),
    ):
        rows = requests.get(BASE + "/pages", params={"slug": slug, "_fields": "id,slug,status,link"}, timeout=TIMEOUT)
        if not rows.ok or not rows.json():
            raise RuntimeError(f"Public verification failed for {slug}.")
        row = rows.json()[0]
        if row.get("status") != "publish" or row.get("link") != expected:
            raise RuntimeError(f"Public page verification mismatch for {slug}.")
        checks.append(row["link"])
    print("WORDPRESS_AUTH=verified")
    print("PAGES_PUBLISHED_AND_PUBLICLY_VERIFIED=3")
    for link in checks:
        print(link)

if __name__ == "__main__":
    main()
