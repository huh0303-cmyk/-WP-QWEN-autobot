// 통합 사이트 설정 탭 (WP+블로그스팟+뉴스+네이버+티스토리) — 신규 독립 스크립트.
// app.js/bridge.js(원본 Electron 렌더러 로직)는 전혀 건드리지 않음. fetch()로 직접
// /api/registry/*, /api/n8n/* 호출. .workspace 그리드 밖에 별도 <section>으로 배치되어
// 기존 패널들과 레이아웃 충돌(겹침) 없음.
//
// Chairman 요청(2026-09-27): "WP 순위별(전날방문자수 내림차순) 따로.. 블팟따로,
// 네이버 따로, 티스토리따로" -> 플랫폼별로 완전히 분리된 표를 그린다. WP는 기본적으로
// yesterday_visitors 내림차순 정렬(daily_site_traffic_result.json 기반), 블로그스팟도
// 같은 기준(blogger_traffic_latest.json)으로 정렬. 네이버/티스토리는 이 파이프라인에
// 방문자 데이터가 없어 등록 순서 그대로 표시.
(function () {
  const summaryText = document.getElementById("registrySummaryText");
  const groupsRoot = document.getElementById("registryGroups");
  const reloadBtn = document.getElementById("registryReloadButton");
  const n8nBtn = document.getElementById("n8nHealthButton");
  const n8nText = document.getElementById("n8nHealthText");
  if (!groupsRoot) return;

  const GROUPS = [
    { platform: "wordpress", title: "WordPress (전날 방문자수 내림차순)", sortByTraffic: true },
    { platform: "blogspot", title: "Blogspot (전날 방문자수 내림차순)", sortByTraffic: true },
    { platform: "naver", title: "Naver (등록 순)", sortByTraffic: false },
    { platform: "tistory", title: "Tistory (등록 순)", sortByTraffic: false },
    { platform: "news", title: "뉴스 (등록 순)", sortByTraffic: false },
  ];

  const OWNER_LABEL = {
    gpt_n8n: "GPT트랙(n8n) — 대시보드+트리거만",
    claude_console: "이 콘솔이 직접 발행",
  };

  let allSites = [];

  async function api(path, opts) {
    const res = await fetch(path, {
      method: opts?.method || "GET",
      headers: opts?.body ? { "Content-Type": "application/json" } : undefined,
      body: opts?.body ? JSON.stringify(opts.body) : undefined,
    });
    if (res.status === 401) {
      window.location.href = "/login";
      throw new Error("unauthenticated");
    }
    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
    return json;
  }

  function scrollToJobForm() {
    const form = document.getElementById("jobForm");
    if (form) form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function actionCell(site) {
    if (site.platform === "naver") {
      const btn = document.createElement("button");
      btn.className = "ghost small";
      btn.type = "button";
      btn.textContent = "이 계정으로 글쓰기";
      btn.addEventListener("click", () => {
        const blogIdInput = document.getElementById("blogId");
        const labelInput = document.getElementById("accountLabel");
        if (blogIdInput) blogIdInput.value = site.blog_slug || "";
        if (labelInput) labelInput.value = site.label || "";
        scrollToJobForm();
      });
      return btn;
    }
    if (site.platform === "tistory") {
      const btn = document.createElement("button");
      btn.className = "ghost small";
      btn.type = "button";
      btn.textContent = "이 계정으로 글쓰기";
      btn.addEventListener("click", () => {
        const tistoryInput = document.getElementById("tistoryBlogId");
        const checkbox = document.getElementById("publishToTistoryAfterNaver");
        if (tistoryInput) tistoryInput.value = site.blog_slug || "";
        if (checkbox) checkbox.checked = true;
        scrollToJobForm();
      });
      return btn;
    }
    const span = document.createElement("span");
    span.className = "hint";
    span.style.fontSize = "11px";
    span.textContent = "상단 배치 트리거 버튼 사용";
    return span;
  }

  function saveHandler(tr, site) {
    return async () => {
      const patch = {};
      tr.querySelectorAll("[data-field]").forEach((el) => {
        const key = el.getAttribute("data-field");
        const val = el.value;
        patch[key] = el.type === "number" ? (val === "" ? null : Number(val)) : val;
      });
      const btn = tr.querySelector('[data-action="save"]');
      btn.disabled = true;
      btn.textContent = "저장중...";
      try {
        await api(`/api/registry/sites/${encodeURIComponent(site.site_id)}`, { method: "POST", body: patch });
        btn.textContent = "저장됨 ✓";
        setTimeout(() => (btn.textContent = "저장"), 1500);
      } catch (err) {
        btn.textContent = "실패";
        alert("저장 실패: " + err.message);
      } finally {
        btn.disabled = false;
      }
    };
  }

  function row(site, showTraffic) {
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid #333";
    const label = site.label || site.title || site.url || site.site_id;
    const needsConfirm = site.needs_confirmation
      ? ` <span style="color:#e0a020;">⚠ 확인필요</span>`
      : "";
    const trafficCell = showTraffic
      ? `<td style="padding:4px; text-align:right; font-variant-numeric:tabular-nums;">${
          site.yesterday_visitors == null ? "-" : site.yesterday_visitors.toLocaleString()
        }</td>`
      : "";

    tr.innerHTML = `
      ${trafficCell}
      <td style="padding:4px;">
        <div>${label}${needsConfirm}</div>
        <div class="hint" style="font-size:11px;">${site.url || ""}</div>
      </td>
      <td style="padding:4px; font-size:11px;">${OWNER_LABEL[site.owner_track] || site.owner_track || "-"}</td>
      <td style="padding:4px;"><textarea data-field="persona" rows="2" style="width:220px; font-size:12px;">${site.persona || ""}</textarea></td>
      <td style="padding:4px;"><textarea data-field="tone" rows="2" style="width:180px; font-size:12px;">${site.tone || ""}</textarea></td>
      <td style="padding:4px; white-space:nowrap;">
        <input data-field="min_chars" type="number" style="width:60px;" value="${site.min_chars ?? ""}" />
        <input data-field="target_chars" type="number" style="width:60px;" value="${site.target_chars ?? ""}" />
        <input data-field="max_chars" type="number" style="width:60px;" value="${site.max_chars ?? ""}" />
      </td>
      <td style="padding:4px;"><input data-field="image_count" type="number" min="0" max="10" style="width:50px;" value="${site.image_count ?? ""}" /></td>
      <td style="padding:4px;"><button class="ghost small" type="button" data-action="save">저장</button></td>
      <td style="padding:4px;" data-action-cell></td>
    `;

    tr.querySelector('[data-action="save"]').addEventListener("click", saveHandler(tr, site));
    tr.querySelector("[data-action-cell]").appendChild(actionCell(site));
    return tr;
  }

  function buildGroupTable(group, sites) {
    const wrap = document.createElement("div");
    wrap.style.marginBottom = "24px";

    const heading = document.createElement("h3");
    heading.style.margin = "0 0 6px";
    heading.style.fontSize = "14px";
    heading.textContent = `${group.title} — ${sites.length}개`;
    wrap.appendChild(heading);

    if (!sites.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "등록된 사이트가 없습니다.";
      wrap.appendChild(empty);
      return wrap;
    }

    const scroller = document.createElement("div");
    scroller.style.overflowX = "auto";
    const table = document.createElement("table");
    table.style.width = "100%";
    table.style.borderCollapse = "collapse";
    table.style.fontSize = "13px";

    const trafficHeader = group.sortByTraffic
      ? '<th style="text-align:right; padding:4px;">전날 방문자</th>'
      : "";
    table.innerHTML = `
      <thead>
        <tr>
          ${trafficHeader}
          <th style="text-align:left; padding:4px;">사이트/계정</th>
          <th style="text-align:left; padding:4px;">소유 트랙</th>
          <th style="text-align:left; padding:4px;">페르소나</th>
          <th style="text-align:left; padding:4px;">톤앤매너</th>
          <th style="text-align:left; padding:4px;">글자수(최소/목표/최대)</th>
          <th style="text-align:left; padding:4px;">이미지수</th>
          <th style="text-align:left; padding:4px;">저장</th>
          <th style="text-align:left; padding:4px;">글쓰기/발행</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector("tbody");
    for (const s of sites) tbody.appendChild(row(s, group.sortByTraffic));
    scroller.appendChild(table);
    wrap.appendChild(scroller);
    return wrap;
  }

  function render() {
    groupsRoot.innerHTML = "";
    for (const group of GROUPS) {
      let list = allSites.filter((s) => s.platform === group.platform);
      if (group.sortByTraffic) {
        list = list.slice().sort((a, b) => (b.yesterday_visitors ?? -1) - (a.yesterday_visitors ?? -1));
      }
      groupsRoot.appendChild(buildGroupTable(group, list));
    }
  }

  async function loadSummaryAndSites() {
    summaryText.textContent = "불러오는 중...";
    try {
      const [{ sites }, summary] = await Promise.all([
        api("/api/registry/sites"),
        api("/api/registry/summary"),
      ]);
      allSites = sites;
      const PLATFORM_LABEL = { wordpress: "WordPress", blogspot: "Blogspot", news: "뉴스", tistory: "Tistory", naver: "Naver" };
      const byPlat = Object.entries(summary.byPlatform)
        .map(([k, v]) => `${PLATFORM_LABEL[k] || k} ${v}`)
        .join(" · ");
      const warn = summary.needsConfirmation.length
        ? ` — ⚠ 확인 필요: ${summary.needsConfirmation.join(", ")}`
        : "";
      summaryText.textContent = `총 ${summary.total}개 (${byPlat}) · 이 콘솔 직접 발행 ${summary.claudeConsoleOwned} / GPT트랙(n8n) 대시보드+트리거만 ${summary.gptN8nDashboardOnly}${warn}`;
      render();
    } catch (err) {
      summaryText.textContent = "불러오기 실패: " + err.message;
    }
  }

  async function runBatch(action, btn) {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "실행 요청 중...";
    try {
      const result = await api(`/api/n8n/run/${encodeURIComponent(action)}`, { method: "POST", body: {} });
      btn.textContent = result.ok ? "실행됨 ✓" : "실행 실패";
    } catch (err) {
      btn.textContent = "실패";
      alert(`${action} 실행 실패: ${err.message}`);
    } finally {
      setTimeout(() => (btn.textContent = original), 2000);
      btn.disabled = false;
    }
  }

  reloadBtn.addEventListener("click", loadSummaryAndSites);
  n8nBtn.addEventListener("click", async () => {
    n8nText.textContent = "확인 중...";
    try {
      const health = await api("/api/n8n/health");
      n8nText.textContent = `n8n 게이트웨이: ${JSON.stringify(health)}`;
    } catch (err) {
      n8nText.textContent = "n8n 게이트웨이 확인 실패 (VPS 로컬 8766 포트, 토큰 필요): " + err.message;
    }
  });

  const wpBtn = document.getElementById("triggerWpButton");
  const blogspotBtn = document.getElementById("triggerBlogspotButton");
  const newsBtn = document.getElementById("triggerNewsButton");
  if (wpBtn) wpBtn.addEventListener("click", () => runBatch("wp25_tick", wpBtn));
  if (blogspotBtn) blogspotBtn.addEventListener("click", () => runBatch("blogger33_daily", blogspotBtn));
  if (newsBtn) newsBtn.addEventListener("click", () => runBatch("news2", newsBtn));

  loadSummaryAndSites();
})();
