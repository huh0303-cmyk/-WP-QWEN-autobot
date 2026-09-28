#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build one hosted, per-article review page (with a working approve button)
for every DRAFT_READY Tistory job, plus a signed one-time approval token per
article and a root index linking all of them.

This never publishes anything. It writes static HTML under --output-dir
(served later by GitHub Pages) and a content snapshot per job under
--state-dir that tistory_approve_publish.py reads back independently, in a
later workflow run, once a reviewer clicks "승인하고 발행" on that job's page.

public_allowed stays false everywhere here — the only thing that can ever
flip a single article to published is a verified token consumed by
tistory-approve-publish.yml.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from tistory_approval_tokens import issue_token, load_state, save_state, token_fingerprint  # noqa: E402

SCRIPT_TAG_RE = re.compile(r"(?is)<script[^>]*>.*?</script>")
EVENT_ATTR_RE = re.compile(r'(?i)\son\w+\s*=\s*("[^"]*"|\'[^\']*\')')
IFRAME_RE = re.compile(r"(?is)<iframe[^>]*>.*?</iframe>")


def sanitize_body_html(raw: str) -> str:
    """Defense-in-depth only — the writer prompt already restricts output to
    h2/h3/p/ul/li, but nothing enforces that upstream, and this HTML is about
    to be embedded in a publicly reachable page."""
    text = str(raw or "")
    text = SCRIPT_TAG_RE.sub("", text)
    text = IFRAME_RE.sub("", text)
    text = EVENT_ATTR_RE.sub("", text)
    return text


def _blog_name_from_url(blog_url: str) -> str:
    host = urlparse(blog_url).netloc or blog_url
    return host.split(".")[0]


def _download_image(image_url: str, dest_dir: Path) -> str:
    """Downloads the generated cover image next to the review page so it
    survives after the source URL (Replicate) expires. Returns the filename,
    or "" if the download failed."""
    if not image_url or not image_url.startswith("http"):
        return ""
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        ext = "webp"
        if "jpeg" in content_type or "jpg" in content_type:
            ext = "jpg"
        elif "png" in content_type:
            ext = "png"
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"cover.{ext}"
        (dest_dir / filename).write_bytes(response.content)
        return filename
    except Exception as exc:
        print(f"  ⚠️ image download failed: {exc}")
        return ""


PAGE_TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>[검토] {title}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #f4f5f7; color: #1a1a1a; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", Arial, sans-serif; line-height: 1.7; }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 0 0 48px; }}
  .topbar {{ background: #14213d; color: #fff; padding: 14px 20px; font-size: 14px; letter-spacing: .02em; }}
  .topbar b {{ color: #ffd166; }}
  .meta {{ background: #fff; padding: 20px; border-bottom: 1px solid #e6e8eb; font-size: 13px; color: #555; }}
  .meta div {{ margin: 3px 0; }}
  article {{ background: #fff; padding: 24px 20px 8px; }}
  article h1 {{ font-size: 26px; line-height: 1.35; margin: 0 0 14px; word-break: keep-all; }}
  article h2 {{ font-size: 20px; margin: 30px 0 12px; border-left: 5px solid #14213d; padding-left: 10px; }}
  article h3 {{ font-size: 17px; margin: 22px 0 10px; color: #14213d; }}
  article p {{ font-size: 16px; margin: 0 0 16px; word-break: keep-all; }}
  article ul, article ol {{ font-size: 16px; margin: 0 0 16px; padding-left: 22px; }}
  article li {{ margin: 6px 0; }}
  .cover {{ width: 100%; height: auto; display: block; border-radius: 10px; margin: 4px 0 22px; background: #eee; }}
  .cover-missing {{ padding: 40px 16px; text-align: center; background: #fff3f0; border: 1px dashed #e08; border-radius: 10px; margin: 4px 0 22px; color: #a33; font-size: 14px; }}
  .approve-box {{ background: #fff; margin: 16px 20px 0; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }}
  #approve-btn {{ display: block; width: 100%; padding: 16px; font-size: 17px; font-weight: 700; border: none; border-radius: 10px; background: #14213d; color: #fff; cursor: pointer; }}
  #approve-btn:disabled {{ background: #9aa2b1; cursor: not-allowed; }}
  #approve-note {{ font-size: 13px; color: #666; margin-top: 10px; white-space: pre-wrap; word-break: break-word; }}
  .status-banner {{ margin: 16px 20px 0; padding: 14px 16px; border-radius: 10px; font-size: 14px; font-weight: 700; }}
  .status-pending {{ background: #fff8e1; color: #8a6d00; border: 1px solid #f0d98a; }}
  .status-published {{ background: #e6f6ea; color: #146c2e; border: 1px solid #9adaa8; }}
  .status-failed {{ background: #fdeaea; color: #a3231b; border: 1px solid #f0a6a0; }}
  .status-blocked {{ background: #eef0f4; color: #444; border: 1px solid #cfd4dd; }}
  footer {{ padding: 20px; font-size: 12px; color: #999; }}
</style>
</head>
<body>
<div class="topbar">Tistory 검토 페이지 · <b>승인 전에는 공개되지 않습니다</b></div>
<div class="wrap">
  <div class="meta">
    <div><b>사이트</b>: {site_label} ({blog_url})</div>
    <div><b>언어</b>: {language}</div>
    <div><b>카테고리</b>: {category}</div>
    <div><b>라벨</b>: {labels}</div>
    <div><b>메타 설명</b>: {meta_description}</div>
    <div><b>job_id</b>: {job_id}</div>
  </div>
  <!--STATUS_BANNER_START--><div class="status-banner status-pending">PENDING — 승인 대기 중</div><!--STATUS_BANNER_END-->
  <article>
    <h1>{title}</h1>
    {cover_html}
    {body_html}
  </article>
  <div class="approve-box">
    <button id="approve-btn" {approve_disabled} onclick="approveAndPublish()">승인하고 발행</button>
    <div id="approve-note">{approve_note}</div>
  </div>
  <footer>이 페이지는 검색엔진에 노출되지 않도록 설정되어 있으나(noindex), 이 URL을 아는 사람은 누구나 열람할 수 있습니다. 실제 공개(발행)는 승인 버튼을 눌러야만 일어납니다.</footer>
</div>
<script>
const OWNER_REPO = "{owner_repo}";
const REF = "{ref}";
const WORKFLOW_FILE = "{workflow_file}";
const JOB_ID = "{job_id_js}";
const APPROVAL_TOKEN = "{approval_token_js}";

async function approveAndPublish() {{
  const btn = document.getElementById('approve-btn');
  const note = document.getElementById('approve-note');
  let pat = localStorage.getItem('tistory_approve_pat');
  if (!pat) {{
    pat = prompt('GitHub Personal Access Token을 입력하세요 (fine-grained, 이 저장소 한정, Actions: Read and write 권한만). 이 브라우저에만 저장되며 어디에도 전송되지 않습니다(깃허브 API 호출 제외).');
    if (!pat) return;
    localStorage.setItem('tistory_approve_pat', pat);
  }}
  btn.disabled = true;
  btn.textContent = '발행 요청 전송 중...';
  note.textContent = '';
  try {{
    const res = await fetch(`https://api.github.com/repos/${{OWNER_REPO}}/actions/workflows/${{WORKFLOW_FILE}}/dispatches`, {{
      method: 'POST',
      headers: {{
        'Authorization': 'Bearer ' + pat,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28'
      }},
      body: JSON.stringify({{ ref: REF, inputs: {{ token: APPROVAL_TOKEN, job_id: JOB_ID }} }})
    }});
    if (res.status === 204) {{
      btn.textContent = '발행 요청 완료';
      note.textContent = 'GitHub Actions가 이 글 하나만 발행을 시도합니다 (1~2분 소요). 완료 후 이 페이지가 다시 배포되면 상태가 PUBLISHED 또는 FAILED로 바뀝니다. 진행 상황: https://github.com/' + OWNER_REPO + '/actions/workflows/' + WORKFLOW_FILE;
    }} else {{
      const text = await res.text();
      btn.disabled = false;
      btn.textContent = '승인하고 발행';
      note.textContent = '요청 실패 (HTTP ' + res.status + '): ' + text + ' — 토큰 권한(이 저장소, Actions 읽기/쓰기)을 확인하세요.';
      localStorage.removeItem('tistory_approve_pat');
    }}
  }} catch (e) {{
    btn.disabled = false;
    btn.textContent = '승인하고 발행';
    note.textContent = '네트워크 오류: ' + e.message;
  }}
}}
</script>
</body>
</html>
"""


def _js_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def build_review_page(*, job: dict, draft: dict, owner_repo: str, ref: str, workflow_file: str,
                       image_filename: str, image_alt: str, approval_token: str, approve_disabled: bool,
                       approve_note: str) -> str:
    lang = "en" if job.get("language") == "en" else "ko"
    if image_filename:
        cover_html = f'<img class="cover" src="{html.escape(image_filename)}" alt="{html.escape(image_alt)}" loading="lazy">'
    else:
        cover_html = '<div class="cover-missing">이미지 생성 실패 — 발행 전 재생성이 필요합니다.</div>'

    return PAGE_TEMPLATE.format(
        lang=lang,
        title=html.escape(draft.get("title", "")),
        site_label=html.escape(job.get("title", job.get("site_id", ""))),
        blog_url=html.escape(job.get("url", "")),
        language="English" if lang == "en" else "한국어",
        category=html.escape(draft.get("category", "")),
        labels=html.escape(", ".join(draft.get("labels") or job.get("intent", [])[:8])),
        meta_description=html.escape(draft.get("meta_description", "")),
        job_id=html.escape(job["job_id"]),
        cover_html=cover_html,
        body_html=sanitize_body_html(draft.get("body_html", "")),
        approve_disabled="disabled" if approve_disabled else "",
        approve_note=html.escape(approve_note),
        owner_repo=owner_repo,
        ref=ref,
        workflow_file=workflow_file,
        job_id_js=_js_escape(job["job_id"]),
        approval_token_js=_js_escape(approval_token),
    )


INDEX_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Tistory 검토 목록 — {date}</title>
<style>
  body {{ margin:0; background:#f4f5f7; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",Arial,sans-serif; }}
  .wrap {{ max-width:640px; margin:0 auto; padding:24px 16px; }}
  h1 {{ font-size:20px; }}
  a.card {{ display:block; background:#fff; border-radius:12px; padding:16px; margin-bottom:12px; text-decoration:none; color:#14213d; box-shadow:0 2px 8px rgba(0,0,0,.06); }}
  a.card b {{ display:block; font-size:16px; margin-bottom:4px; }}
  a.card span {{ font-size:13px; color:#666; }}
</style>
</head>
<body><div class="wrap">
<h1>Tistory 5채널 검토 목록 — {date}</h1>
{cards}
</div></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--drafts", required=True)
    parser.add_argument("--output-dir", required=True, help="e.g. public/tistory-review/2026-08-30")
    parser.add_argument("--state-dir", default="state/tistory_approvals")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--ref", required=True, help="branch the approve workflow will run on")
    parser.add_argument("--workflow-file", default="tistory-approve-publish.yml")
    parser.add_argument("--pages-base-url", required=True, help="e.g. https://owner.github.io/repo")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    drafts_payload = json.loads(Path(args.drafts).read_text(encoding="utf-8"))
    drafts_by_job = {d["job_id"]: d for d in drafts_payload.get("drafts", [])}

    date = plan["date"]
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    state = load_state(args.state_dir, date)
    cards = []
    manifest = {"date": date, "jobs": []}

    for job in plan["jobs"]:
        draft = drafts_by_job.get(job["job_id"])
        site_dir = out_root / job["site_id"]
        site_dir.mkdir(parents=True, exist_ok=True)
        review_url = f"{args.pages_base_url}/tistory-review/{date}/{job['site_id']}/"

        if not draft or draft.get("status") != "DRAFT_READY":
            status_note = (draft or {}).get("status", "NO_DRAFT")
            error_note = (draft or {}).get("error", "")
            page = build_review_page(
                job=job,
                draft={"title": f"[생성 실패: {status_note}] {job['title']}", "body_html": f"<p>{html.escape(error_note)}</p>", "category": "", "meta_description": ""},
                owner_repo=args.repo, ref=args.ref, workflow_file=args.workflow_file,
                image_filename="", image_alt="", approval_token="", approve_disabled=True,
                approve_note=f"이 글은 초안 생성/검수 단계에서 통과하지 못했습니다 ({status_note}). 재생성 후 다시 검토해야 합니다.",
            )
            (site_dir / "index.html").write_text(page, encoding="utf-8")
            cards.append(f'<a class="card" href="./{job["site_id"]}/"><b>[미생성] {html.escape(job["title"])}</b><span>{html.escape(status_note)}</span></a>')
            manifest["jobs"].append({"job_id": job["job_id"], "site_id": job["site_id"], "status": status_note, "review_url": review_url})
            continue

        image_filename = _download_image(draft.get("image_url", ""), site_dir)
        image_alt = draft.get("image_prompt") or draft.get("title") or job["title"]
        blog_url = job.get("url", "")

        existing = state.get("jobs", {}).get(job["job_id"], {})

        if not image_filename:
            approve_disabled = True
            approve_note = "이미지 생성/다운로드에 실패해 이 글은 승인 버튼이 비활성화되어 있습니다. 이미지가 있어야 검토 요건(관련 이미지+ALT)을 충족합니다."
            approval_token = ""
        elif existing.get("status") == "PUBLISHED":
            approve_disabled = True
            approve_note = f"이미 발행되었습니다: {existing.get('public_url', '')}"
            approval_token = ""
        else:
            approval_token = issue_token(job["job_id"])
            approve_disabled = False
            approve_note = "승인 시 GitHub Actions가 이 글 하나만 해당 Tistory 블로그에 발행합니다."

        content_html = sanitize_body_html(draft.get("body_html", ""))
        image_public_url = f"{args.pages_base_url}/tistory-review/{date}/{job['site_id']}/{image_filename}" if image_filename else ""

        page = build_review_page(
            job=job, draft=draft, owner_repo=args.repo, ref=args.ref, workflow_file=args.workflow_file,
            image_filename=image_filename, image_alt=image_alt, approval_token=approval_token,
            approve_disabled=approve_disabled, approve_note=approve_note,
        )
        (site_dir / "index.html").write_text(page, encoding="utf-8")

        if approval_token:
            state.setdefault("jobs", {})[job["job_id"]] = {
                "status": "PENDING",
                "site_id": job["site_id"],
                "blog_url": blog_url,
                "title": draft.get("title", ""),
                "category": draft.get("category", ""),
                "labels": draft.get("labels") or job.get("intent", [])[:8],
                "content_html": content_html,
                "image_public_url": image_public_url,
                "image_alt": image_alt,
                "review_url": review_url,
                "token_fingerprint": token_fingerprint(approval_token),
            }
        display_status = "PUBLISHED" if existing.get("status") == "PUBLISHED" else ("IMAGE_MISSING" if not image_filename else "PENDING")
        cards.append(
            f'<a class="card" href="./{job["site_id"]}/"><b>{html.escape(draft.get("title",""))}</b>'
            f'<span>{html.escape(job["title"])} · {html.escape(display_status)}</span></a>'
        )
        manifest["jobs"].append({
            "job_id": job["job_id"], "site_id": job["site_id"], "title": draft.get("title", ""),
            "status": display_status, "review_url": review_url,
        })

    save_state(args.state_dir, date, state)
    (out_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_root / "index.html").write_text(INDEX_TEMPLATE.format(date=date, cards="\n".join(cards)), encoding="utf-8")

    print(json.dumps({"date": date, "jobs": len(manifest["jobs"]), "output_dir": str(out_root)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
