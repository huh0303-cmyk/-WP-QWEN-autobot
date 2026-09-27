// 통합 사이트 설정 탭 (WP+블로그스팟+뉴스+네이버+티스토리) — 신규 독립 스크립트.
// app.js/bridge.js(원본 Electron 렌더러 로직)는 전혀 건드리지 않음. fetch()로 직접
// /api/registry/*, /api/n8n/* 호출. .workspace 그리드 밖에 별도 <section>으로 배치되어
// 기존 패널들과 레이아웃 충돌(겹침) 없음.
(function () {
  const tbody = document.getElementById("registryTableBody");
  const summaryText = document.getElementById("registrySummaryText");
  const filterSelect = document.getElementById("registryPlatformFilter");
  const reloadBtn = document.getElementById("registryReloadButton");
  const n8nBtn = document.getElementById("n8nHealthButton");
  const n8nText = document.getElementById("n8nHealthText");
  if (!tbody) return;

  const PLATFORM_LABEL = {
    wordpress: "WordPress",
    blogspot: "Blogspot",
    news: "뉴스",
    tistory: "Tistory",
    naver: "Naver",
  };
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

  function row(site) {
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid #333";
    const label = site.label || site.title || site.url || site.site_id;
    const needsConfirm = site.needs_confirmation
      ? ` <span style="color:#e0a020;">⚠ 확인필요</span>`
      : "";

    tr.innerHTML = `
      <td style="padding:4px;">${PLATFORM_LABEL[site.platform] || site.platform}</td>
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

    tr.querySelector('[data-action="save"]').addEventListener("click", async () => {
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
    });

    tr.querySelector("[data-action-cell]").appendChild(actionCell(site));

    return tr;
  }

  function render() {
    const filter = filterSelect.value;
    const list = filter ? allSites.filter((s) => s.platform === filter) : allSites;
    tbody.innerHTML = "";
    for (const s of list) tbody.appendChild(row(s));
  }

  async function loadSummaryAndSites() {
    summaryText.textContent = "불러오는 중...";
    try {
      const [{ sites }, summary] = await Promise.all([
        api("/api/registry/sites"),
        api("/api/registry/summary"),
      ]);
      allSites = sites;
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

  filterSelect.addEventListener("change", render);
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
