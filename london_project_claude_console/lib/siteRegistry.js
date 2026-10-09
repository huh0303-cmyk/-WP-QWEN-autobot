"use strict";
/**
 * 통합 사이트 레지스트리 — WP27 + Blogspot33 + 뉴스2 + 티스토리5 + 네이버3
 *
 * 범위 결정(2026-09-27, Chairman 확인): "대시보드+트리거만" 방식.
 *   - naver / tistory: 이 콘솔이 직접 소유·발행(jobRunner.js/naverPublisher.js/tistoryPublisher.js).
 *   - wordpress / blogspot / news: 실제 발행 로직은 GPT/PM 트랙의 n8n·GitHub Actions 파이프라인이
 *     계속 소유한다. 이 레지스트리는 그 60+2개 사이트의 persona/tone/글자수 설정을 "읽기 전용"으로
 *     보여주고, 필요하면 scripts/n8n_gateway.py를 통해 기존 서비스를 트리거만 한다.
 *     (여기서 WP/Blogspot/뉴스용 발행 코드를 재구현하지 않는다 — GPT 트랙 OWNER LOCKED 범위와
 *     충돌 방지를 위한 의도적 설계.)
 *
 * 소스 데이터(원본 그대로 읽기만 함, 이 파일에서 수정하지 않음):
 *   - config/automation_hub_sites.json   (60: wordpress 27 + blogger 33 — persona/tone 원본)
 *   - config/content_engine_profiles.json (33 profile: wp+blogspot 쌍의 min/target/max_chars)
 *   - config/tistory_portfolio.json      (5)
 *   - config/newsrooms.json              (2, dict-keyed by domain)
 *
 * 오버라이드(이 콘솔에서 편집 가능한 값 — persona/tone/image_count/word_count):
 *   runtime/registry_overrides.json 에 site_id 별로 저장. 원본 리포 config 파일은 절대 덮어쓰지
 *   않는다 (그 파일들은 다른 AI 트랙의 파이프라인이 실제로 읽는 소스이므로, 이 콘솔에서 고친 값은
 *   오버레이로만 적용되고 원본은 그대로 둔다 — 다음 세션/트랙 충돌 방지).
 */

const fs = require("fs");
const path = require("path");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const CONFIG_DIR = path.join(REPO_ROOT, "config");

function readJsonSafe(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (err) {
    return fallback;
  }
}

function getOverridesPath(runtimeRoot) {
  return path.join(runtimeRoot, "registry_overrides.json");
}

function loadOverrides(runtimeRoot) {
  return readJsonSafe(getOverridesPath(runtimeRoot), {});
}

function saveOverrides(runtimeRoot, overrides) {
  const p = getOverridesPath(runtimeRoot);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(overrides, null, 2), "utf8");
}

// 글자수 목표 기반으로 합리적인 기본 이미지 수를 추정 (원본 config에 image_count 필드가 없어서).
// 700자당 이미지 1장, 최소 1장 / 최대 6장으로 clamp.
function defaultImageCount(targetChars) {
  if (!targetChars || targetChars <= 0) return 2;
  const n = Math.round(targetChars / 700);
  return Math.max(1, Math.min(6, n));
}

function domainFromUrl(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

// WP: daily_site_traffic_result.json (리포 루트, daily-site-traffic.yml 워크플로우 산출물)의
// yesterday_visitors 필드를 domain 기준으로 매칭.
function loadWpTrafficByDomain() {
  const data = readJsonSafe(path.join(REPO_ROOT, "daily_site_traffic_result.json"), null);
  const map = {};
  if (data && Array.isArray(data.records)) {
    for (const r of data.records) {
      if (r.domain) map[r.domain] = r.yesterday_visitors ?? null;
    }
  }
  return { map, checkedAt: data?.checked_at || null };
}

// Blogspot: data/blogger_traffic_latest.json의 "yesterday" 필드를 URL 기준으로 매칭.
function loadBlogspotTrafficByUrl() {
  const data = readJsonSafe(path.join(REPO_ROOT, "data", "blogger_traffic_latest.json"), null);
  const map = {};
  if (data && data.sites && typeof data.sites === "object") {
    for (const [url, stats] of Object.entries(data.sites)) {
      map[url.replace(/\/$/, "")] = stats?.yesterday ?? null;
    }
  }
  return { map, generatedAt: data?.generated_at || null };
}

function buildBaseRegistry() {
  const entries = [];
  const wpTraffic = loadWpTrafficByDomain();
  const blogspotTraffic = loadBlogspotTrafficByUrl();

  // --- WordPress 27 + Blogspot 33 (content_engine_profiles.json이 가장 완전한 소스) ---
  const profiles = readJsonSafe(
    path.join(CONFIG_DIR, "content_engine_profiles.json"),
    { profiles: [] }
  ).profiles || [];

  for (const p of profiles) {
    if (p.wordpress) {
      const w = p.wordpress;
      entries.push({
        site_id: `wp_${p.site_key}`,
        source_site_id: p.source_site_id || null,
        platform: "wordpress",
        owner_track: "gpt_n8n", // 대시보드+트리거만
        language: p.language || w.language || null,
        url: w.url,
        persona: w.persona || "",
        tone: w.tone || "",
        theme: w.theme || "",
        min_chars: w.min_chars ?? null,
        target_chars: w.target_chars ?? null,
        max_chars: w.max_chars ?? null,
        image_count: defaultImageCount(w.target_chars),
        n8n_action: "wp25_tick",
        yesterday_visitors: wpTraffic.map[domainFromUrl(w.url)] ?? null,
        traffic_checked_at: wpTraffic.checkedAt,
      });
    }
    if (p.blogspot) {
      const b = p.blogspot;
      entries.push({
        site_id: `blogspot_${p.site_key}`,
        source_site_id: p.source_site_id || null,
        platform: "blogspot",
        owner_track: "gpt_n8n",
        language: p.language || null,
        url: b.url,
        yesterday_visitors: blogspotTraffic.map[(b.url || "").replace(/\/$/, "")] ?? null,
        traffic_checked_at: blogspotTraffic.generatedAt,
        persona: b.persona || "",
        tone: b.tone || "",
        min_chars: b.min_chars ?? null,
        target_chars: b.target_chars ?? null,
        max_chars: b.max_chars ?? null,
        image_count: defaultImageCount(b.target_chars),
        n8n_action: "blogger33_daily",
      });
    }
  }

  // --- 뉴스룸 2 ---
  const newsrooms = readJsonSafe(path.join(CONFIG_DIR, "newsrooms.json"), {});
  const newsSites = newsrooms.sites || newsrooms.newsrooms || null;
  if (newsSites && typeof newsSites === "object") {
    for (const [domain, cfg] of Object.entries(newsSites)) {
      if (!cfg || typeof cfg !== "object") continue;
      entries.push({
        site_id: `news_${domain.replace(/[^a-z0-9]/gi, "_")}`,
        platform: "news",
        owner_track: "gpt_n8n",
        url: cfg.url || `https://${domain}`,
        persona: cfg.persona || "",
        tone: cfg.tone || "",
        min_chars: cfg.min_chars ?? 700,
        target_chars: cfg.target_chars ?? 1100,
        max_chars: cfg.max_chars ?? 1500,
        image_count: defaultImageCount(cfg.target_chars ?? 1100),
        n8n_action: "news2",
      });
    }
  } else {
    // newsrooms.json이 2개 도메인 딕셔너리가 아닌 형태일 수 있어, 최소한 알려진 2곳을 폴백으로 고정.
    for (const [domain, url] of [
      ["koreanews365.com", "https://koreanews365.com"],
      ["theseouljournal.com", "https://theseouljournal.com"],
    ]) {
      entries.push({
        site_id: `news_${domain.replace(/[^a-z0-9]/gi, "_")}`,
        platform: "news",
        owner_track: "gpt_n8n",
        url,
        persona: "",
        tone: "",
        min_chars: 700,
        target_chars: 1100,
        max_chars: 1500,
        image_count: 2,
        n8n_action: "news2",
      });
    }
  }

  // --- 티스토리 5 (이 콘솔이 직접 발행 소유) ---
  const tistory = readJsonSafe(
    path.join(CONFIG_DIR, "tistory_portfolio.json"),
    { sites: [] }
  ).sites || [];
  for (const s of tistory) {
    const slug = (s.url || "").match(/https?:\/\/([^./]+)\.tistory\.com/);
    entries.push({
      site_id: s.site_id,
      platform: "tistory",
      owner_track: "claude_console",
      blog_slug: slug ? slug[1] : null,
      url: s.url,
      label: s.current_label,
      title: s.title,
      persona: s.description || "",
      tone: "",
      theme: (s.categories || []).join(", "),
      min_chars: null,
      target_chars: null,
      max_chars: null,
      image_count: 3,
    });
  }

  // --- 네이버 3 (이 콘솔이 직접 발행 소유) ---
  // 2026-10-09 Chairman 확정 (Blogauto 확장 Chrome 세션 페어링 완료, 비밀번호는 앱/저장소에 저장하지 않음):
  //   huh0303 = 부의정석 (이전에 "돈의정석"/"생활의정석"으로 잘못 기재되었던 것을 수정)
  //   huh3    = 헬스의정석
  //   huh4    = 생활의정석
  // 카테고리는 Blogauto 앱의 계정별 카테고리 설정과 Naver 블로그 자체 카테고리 메뉴에 동일하게 등록되어야 함.
  const naverAccounts = [
    { blogId: "huh0303", label: "부의정석", categories: ["부의흐름-국가정책", "기타핫이슈"], confirmed: true },
    { blogId: "huh3", label: "헬스의정석", categories: ["건강의학정보", "기타핫이슈"], confirmed: true },
    { blogId: "huh4", label: "생활의정석", categories: ["생활정보", "기타핫이슈"], confirmed: true },
  ];
  for (const acc of naverAccounts) {
    entries.push({
      site_id: `naver_${acc.blogId}`,
      platform: "naver",
      owner_track: "claude_console",
      blog_slug: acc.blogId,
      url: `https://blog.naver.com/${acc.blogId}`,
      label: acc.label,
      persona: "",
      tone: "",
      theme: acc.categories.join(", "),
      categories: acc.categories,
      min_chars: null,
      target_chars: null,
      max_chars: null,
      image_count: 3,
      needs_confirmation: !acc.confirmed,
      note: !acc.confirmed
        ? "Blog ID를 추정으로 등록함 — Chairman 확인 필요"
        : undefined,
    });
  }

  return entries;
}

function applyOverrides(entries, overrides) {
  const EDITABLE_FIELDS = ["persona", "tone", "image_count", "min_chars", "target_chars", "max_chars", "label"];
  return entries.map((e) => {
    const o = overrides[e.site_id];
    if (!o) return e;
    const merged = { ...e };
    for (const f of EDITABLE_FIELDS) {
      if (o[f] !== undefined) merged[f] = o[f];
    }
    merged._overridden = true;
    return merged;
  });
}

function listSites(runtimeRoot) {
  const base = buildBaseRegistry();
  const overrides = loadOverrides(runtimeRoot);
  return applyOverrides(base, overrides);
}

function updateSite(runtimeRoot, siteId, patch) {
  const ALLOWED = ["persona", "tone", "image_count", "min_chars", "target_chars", "max_chars", "label"];
  const overrides = loadOverrides(runtimeRoot);
  const current = overrides[siteId] || {};
  const next = { ...current };
  for (const key of ALLOWED) {
    if (patch[key] !== undefined) next[key] = patch[key];
  }
  overrides[siteId] = next;
  saveOverrides(runtimeRoot, overrides);
  return listSites(runtimeRoot).find((s) => s.site_id === siteId) || null;
}

function summary(runtimeRoot) {
  const sites = listSites(runtimeRoot);
  const byPlatform = {};
  for (const s of sites) {
    byPlatform[s.platform] = (byPlatform[s.platform] || 0) + 1;
  }
  return {
    total: sites.length,
    byPlatform,
    claudeConsoleOwned: sites.filter((s) => s.owner_track === "claude_console").length,
    gptN8nDashboardOnly: sites.filter((s) => s.owner_track === "gpt_n8n").length,
    needsConfirmation: sites.filter((s) => s.needs_confirmation).map((s) => s.site_id),
  };
}

module.exports = { listSites, updateSite, summary };
