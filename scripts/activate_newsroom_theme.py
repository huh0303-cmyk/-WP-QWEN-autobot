#!/usr/bin/env python3
"""Guarded install/activation of Twenty Twenty-Five through the authenticated Code Snippets REST API."""
from __future__ import annotations
import argparse,json,os,time
from datetime import datetime,timezone
from pathlib import Path
import requests

USER=os.getenv("WP_USER","").strip() or "huh0303@gmail.com"
ENV={"koreanews365.com":"KOREANEWS365COM","theseouljournal.com":"THESEOULJOURNALCOM"}
CONFIRM="ACTIVATE-TWENTY-TWENTY-FIVE"
TARGET="twentytwentyfive"
PHP=r"""
add_action('init', function () {
    if (get_option('newsroom_theme_migration_v1') === 'done') { return; }
    $slug = 'twentytwentyfive';
    $theme = wp_get_theme($slug);
    if (!$theme->exists()) {
        require_once ABSPATH . 'wp-admin/includes/theme.php';
        require_once ABSPATH . 'wp-admin/includes/class-wp-upgrader.php';
        require_once ABSPATH . 'wp-admin/includes/theme-install.php';
        $info = themes_api('theme_information', array('slug' => $slug));
        if (is_wp_error($info) || empty($info->download_link)) {
            update_option('newsroom_theme_migration_v1', 'theme-api-error');
            return;
        }
        $upgrader = new Theme_Upgrader(new Automatic_Upgrader_Skin());
        $result = $upgrader->install($info->download_link);
        if (is_wp_error($result) || !$result) {
            update_option('newsroom_theme_migration_v1', 'install-error');
            return;
        }
    }
    switch_theme($slug);
    if (get_stylesheet() === $slug) {
        update_option('newsroom_theme_migration_v1', 'done');
    } else {
        update_option('newsroom_theme_migration_v1', 'activate-error');
    }
}, 1);
"""

def call(method,site,path,pw,data=None,params=None):
    r=requests.request(method,f"https://{site}/wp-json/{path}",auth=(USER,pw),json=data,params=params,
      headers={"User-Agent":"WP-Newsroom-Theme/1.0"},timeout=60)
    if r.status_code>=400: raise RuntimeError(f"{site} {method} {path}: {r.status_code} {r.text[:400]}")
    return r.json() if r.text else {}

def active_theme(site,pw):
    x=call("GET",site,"wp/v2/themes",pw,params={"status":"active"})
    return x[0].get("stylesheet") if x else None

def migrate(site):
    pw=os.getenv(ENV[site],"").strip()
    if not pw: raise RuntimeError(f"Missing secret {ENV[site]}")
    before=active_theme(site,pw)
    payload={"name":"Newsroom theme migration v1","desc":"One-time guarded TT5 activation; removed after verification.",
      "code":PHP,"scope":"global","active":True,"priority":1,"tags":["newsroom","migration"]}
    created=call("POST",site,"code-snippets/v1/snippets",pw,payload)
    sid=created.get("id") or created.get("snippet",{}).get("id")
    if not sid: raise RuntimeError(f"{site}: snippet id missing in {created}")
    try:
        requests.get(f"https://{site}/",headers={"User-Agent":"WP-Newsroom-Theme/1.0"},timeout=120).raise_for_status()
        time.sleep(2)
        after=active_theme(site,pw)
        if after!=TARGET: raise RuntimeError(f"{site}: theme is {after}, expected {TARGET}")
    finally:
        call("DELETE",site,f"code-snippets/v1/snippets/{sid}",pw)
    return {"site":site,"before":before,"after":after,"temporary_snippet_deleted":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--site",choices=["ALL",*ENV],default="ALL")
    ap.add_argument("--confirm",required=True)
    ap.add_argument("--receipt",default="newsroom_theme_receipt.json")
    a=ap.parse_args()
    if a.confirm!=CONFIRM: raise SystemExit(f"Refusing. Use --confirm {CONFIRM}")
    sites=list(ENV) if a.site=="ALL" else [a.site]
    result={"schema":1,"applied_at":datetime.now(timezone.utc).isoformat(),"results":[]}
    for site in sites:
        try: result["results"].append({"ok":True,**migrate(site)})
        except Exception as e: result["results"].append({"ok":False,"site":site,"error":str(e)})
    Path(a.receipt).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not all(x["ok"] for x in result["results"]): raise SystemExit(2)

if __name__=="__main__": main()
