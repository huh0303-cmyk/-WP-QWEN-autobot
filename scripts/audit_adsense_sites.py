#!/usr/bin/env python3
"""Read-only infrastructure audit for the 26 production WordPress sites."""
from __future__ import annotations

import argparse
import csv
import json
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

PUBLISHER_ID = "pub-3456727916386941"
ADS_LINE = f"google.com, {PUBLISHER_ID}, DIRECT, f08c47fec0942fa0"
DOMAINS = [
    "k-trip365.com", "kworld365.com", "jobkorea365.com", "kstudy365.com",
    "koreainsurance365.com", "kfinance365.com", "koreamedicaltour.com",
    "k-visa365.com", "koreanews365.com", "koreainvest365.com",
    "oliveyoungkorea.com", "koreacrypto365.com", "jobinkorea365.com",
    "koreawedding365.com", "theseouljournal.com", "ktech365.com",
    "kieca-korea.org", "ki-korea.com", "ksa-korea.org", "koreataxnlaw.com",
    "jobkoreaglobal.com", "studyinkorea365.com", "korea365.org", "sis-korea.com",
    "krealestate365.com", "k-health365.com",
]
APPROVED_GROUP = {
    "koreataxnlaw.com", "jobkoreaglobal.com", "studyinkorea365.com",
    "korea365.org", "sis-korea.com", "krealestate365.com", "k-health365.com",
}
UA = "Mozilla/5.0 (compatible; AdsTxtReadOnlyAudit/1.0; +https://github.com/huh0303-cmyk/-WP-QWEN-autobot)"


def fetch(url: str, *, timeout: float = 25) -> dict:
    started = time.perf_counter()
    try:
        response = requests.get(url, headers={"User-Agent": UA}, timeout=timeout, allow_redirects=True)
        elapsed = round((time.perf_counter() - started) * 1000)
        return {
            "status": response.status_code, "final_url": response.url,
            "response_ms": elapsed, "content_type": response.headers.get("Content-Type", ""),
            "body": response.text, "bytes": len(response.content),
            "redirect_chain": [f"{item.status_code} {item.url}" for item in response.history],
            "error": "",
        }
    except requests.RequestException as exc:
        return {"status": None, "final_url": "", "response_ms": round((time.perf_counter()-started)*1000),
                "content_type": "", "body": "", "bytes": 0, "redirect_chain": [],
                "error": f"{type(exc).__name__}: {exc}"}


def dns_records(domain: str) -> dict:
    result = {"A": [], "AAAA": [], "CNAME": []}
    try:
        import dns.resolver
        for kind in result:
            try:
                result[kind] = sorted({str(x).rstrip(".") for x in dns.resolver.resolve(domain, kind)})
            except Exception:
                pass
    except ImportError:
        try:
            for family, _, _, _, sockaddr in socket.getaddrinfo(domain, 443):
                key = "AAAA" if family == socket.AF_INET6 else "A"
                result[key].append(sockaddr[0])
            result["A"] = sorted(set(result["A"])); result["AAAA"] = sorted(set(result["AAAA"]))
        except OSError:
            pass
    return result


def forced_ip_fetch(domain: str, ip: str, family: str, timeout: int = 25) -> dict:
    if not ip:
        return {"status": None, "response_ms": None, "body": "", "error": f"no_{family.lower()}_record"}
    resolve = f"{domain}:443:[{ip}]" if family == "IPv6" else f"{domain}:443:{ip}"
    marker = "\n__AUDIT_META__"
    cmd = ["curl", "-sS", "-L", "--max-time", str(timeout), "--resolve", resolve,
           "-A", UA, "-w", marker + "%{http_code}|%{time_total}|%{url_effective}",
           f"https://{domain}/ads.txt"]
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout+5)
        body, _, meta = proc.stdout.rpartition(marker)
        status, seconds, final_url = (meta.split("|", 2) + ["", "", ""])[:3]
        return {"status": int(status) if status.isdigit() and status != "000" else None,
                "response_ms": round(float(seconds)*1000) if seconds else round((time.perf_counter()-started)*1000),
                "final_url": final_url, "body": body, "error": proc.stderr.strip() if proc.returncode else ""}
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {"status": None, "response_ms": round((time.perf_counter()-started)*1000), "body": "",
                "error": f"{type(exc).__name__}: {exc}"}


def format_checks(body: str, content_type: str) -> dict:
    stripped = body.lstrip("\ufeff\r\n\t ")
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    return {
        "publisher_id_match": any(line == ADS_LINE for line in lines),
        "publisher_id_present": PUBLISHER_ID in body,
        "bom": body.startswith("\ufeff"),
        "looks_html": stripped.lower().startswith(("<!doctype html", "<html")) or "text/html" in content_type.lower(),
        "exact_lines": lines,
    }


def robots_blocks(body: str) -> bool:
    active = False
    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip().lower()
        if line.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            active = agent in {"*", "googlebot", "google-adstxt", "mediapartners-google"}
        elif active and line.startswith("disallow:") and line.split(":", 1)[1].strip() in {"/", "/ads.txt"}:
            return True
    return False


def audit_domain(domain: str) -> dict:
    root = fetch(f"https://{domain}/")
    www = fetch(f"https://www.{domain}/")
    http = fetch(f"http://{domain}/")
    ads = fetch(f"https://{domain}/ads.txt")
    robots = fetch(f"https://{domain}/robots.txt")
    rest = fetch(f"https://{domain}/wp-json/wp/v2/posts?per_page=1")
    dns = dns_records(domain)
    checks = format_checks(ads["body"], ads["content_type"])
    ipv4 = forced_ip_fetch(domain, dns["A"][0] if dns["A"] else "", "IPv4")
    ipv6 = forced_ip_fetch(domain, dns["AAAA"][0] if dns["AAAA"] else "", "IPv6")
    issues = []
    if ads["status"] != 200: issues.append("ads_status")
    if not checks["publisher_id_match"]: issues.append("publisher_line_mismatch")
    if checks["bom"] or checks["looks_html"]: issues.append("ads_format")
    if robots_blocks(robots["body"]): issues.append("robots_blocks_google")
    if not root["status"] or not rest["status"]: issues.append("site_or_rest_unreachable")
    if ads["response_ms"] and ads["response_ms"] > 5000: issues.append("slow_ads_response")
    if dns["AAAA"] and ipv6["status"] != 200: issues.append("ipv6_probe_failed_from_runner")
    severity = "FAIL" if any(x in issues for x in ("ads_status", "publisher_line_mismatch", "ads_format", "robots_blocks_google")) else ("WARN" if issues else "OK")
    return {
        "domain": domain, "reported_adsense_group": "approved" if domain in APPROVED_GROUP else "not_found",
        "severity": severity, "issues": issues,
        "root_status": root["status"], "root_final_url": root["final_url"],
        "www_status": www["status"], "www_final_url": www["final_url"],
        "http_status": http["status"], "http_final_url": http["final_url"],
        "ads_txt_status": ads["status"], "ads_txt_final_url": ads["final_url"],
        "ads_txt_body": ads["body"], "ads_txt_bytes": ads["bytes"],
        "ads_txt_response_ms": ads["response_ms"], "content_type": ads["content_type"],
        **checks, "robots_status": robots["status"], "robots_google_block": robots_blocks(robots["body"]),
        "A": dns["A"], "AAAA": dns["AAAA"], "CNAME": dns["CNAME"],
        "ipv4_ads_status": ipv4["status"], "ipv4_ads_response_ms": ipv4["response_ms"],
        "ipv4_body_match": ADS_LINE in ipv4["body"], "ipv4_error": ipv4["error"],
        "ipv6_ads_status": ipv6["status"], "ipv6_ads_response_ms": ipv6["response_ms"],
        "ipv6_body_match": ADS_LINE in ipv6["body"], "ipv6_error": ipv6["error"],
        "redirect_chain": ads["redirect_chain"], "wordpress_rest_status": rest["status"],
        "canonical_host": urlparse(root["final_url"]).hostname or "", "error": ads["error"] or root["error"],
    }


def write_outputs(rows: list[dict], output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"adsense_audit_{stamp}.json"
    csv_path = output_dir / f"adsense_audit_{stamp}.csv"
    md_path = output_dir / f"adsense_audit_{stamp}.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    flat = [{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()} for row in rows]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)
    counts = {s: sum(row["severity"] == s for row in rows) for s in ("OK", "WARN", "FAIL")}
    lines = ["# AdSense / ads.txt 26-site read-only audit", "", f"- Generated UTC: {stamp}",
             f"- Total: {len(rows)} / OK: {counts['OK']} / WARN: {counts['WARN']} / FAIL: {counts['FAIL']}", "",
             "| Domain | Group | Result | ads.txt | ms | Bytes | A | AAAA | Canonical | Issues |", "|---|---|---:|---:|---:|---:|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['domain']} | {row['reported_adsense_group']} | {row['severity']} | {row['ads_txt_status']} | {row['ads_txt_response_ms']} | {row['ads_txt_bytes']} | {', '.join(row['A']) or '-'} | {', '.join(row['AAAA']) or '-'} | {row['canonical_host']} | {', '.join(row['issues']) or '-'} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path), "counts": counts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domains", nargs="*", default=DOMAINS)
    parser.add_argument("--output-dir", default="artifacts/adsense-audit")
    args = parser.parse_args()
    domains = [domain.strip().lower() for domain in args.domains]
    with ThreadPoolExecutor(max_workers=min(6, len(domains))) as pool:
        rows = list(pool.map(audit_domain, domains))
    print(json.dumps(write_outputs(rows, Path(args.output_dir)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
