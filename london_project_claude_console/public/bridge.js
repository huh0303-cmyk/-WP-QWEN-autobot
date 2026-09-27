/*
 * Browser-side replacement for the original Electron preload.js.
 * Implements the exact same window.blogAuto surface that public/app.js (unchanged,
 * ported verbatim from the desktop console) already calls, but backed by
 * fetch() + WebSocket instead of ipcRenderer/contextBridge.
 */
(() => {
  const listeners = {
    "job:log": [],
    "job:status": [],
    "job:tokens": [],
    "job:preview": [],
    "job:selectedTitle": [],
    "job:complete": [],
    "accounts:update": []
  };

  function on(channel, handler) {
    if (listeners[channel]) listeners[channel].push(handler);
  }

  function dispatch(channel, payload) {
    (listeners[channel] || []).forEach((handler) => {
      try { handler(payload); } catch (err) { console.error(`[bridge] ${channel} handler error`, err); }
    });
  }

  let ws;
  let wsRetryDelay = 1000;
  function connectSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws`);
    ws.addEventListener("open", () => { wsRetryDelay = 1000; });
    ws.addEventListener("message", (event) => {
      let msg;
      try { msg = JSON.parse(event.data); } catch { return; }
      if (msg && msg.channel) dispatch(msg.channel, msg.payload);
    });
    ws.addEventListener("close", () => {
      setTimeout(connectSocket, wsRetryDelay);
      wsRetryDelay = Math.min(wsRetryDelay * 1.5, 15000);
    });
    ws.addEventListener("error", () => ws.close());
  }
  connectSocket();

  async function callApi(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body === undefined ? {} : body)
    });
    if (res.status === 401) {
      location.href = "/login";
      throw new Error("로그인이 필요합니다.");
    }
    const text = await res.text();
    let data;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (!res.ok) {
      const message = (data && data.error) || res.statusText || "요청 실패";
      throw new Error(message);
    }
    return data;
  }

  async function uploadSampleImage(accountId, file) {
    const form = new FormData();
    form.append("accountId", accountId);
    form.append("image", file);
    const res = await fetch("/api/accounts/chooseSampleImage", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "업로드 실패");
    return data;
  }

  // The desktop app opened a native OS file picker (dialog.showOpenDialog) here.
  // The browser has no equivalent, so we drive the hidden <input type="file"> that
  // index.html adds next to the "Upload / change" button, and resolve once the user
  // picks a file (or resolve immediately, unchanged, if they cancel).
  function chooseAccountSampleImageViaHiddenInput(accountId) {
    return new Promise((resolve, reject) => {
      const input = document.getElementById("chooseAccountSampleImageInput");
      if (!input) {
        reject(new Error("파일 선택 UI를 찾을 수 없습니다."));
        return;
      }
      const cleanup = () => { input.removeEventListener("change", onChange); input.value = ""; };
      const onChange = async () => {
        const file = input.files && input.files[0];
        cleanup();
        if (!file) {
          resolve(await callApi("/api/app/getInitialData").then((d) => d.accountStore));
          return;
        }
        try {
          resolve(await uploadSampleImage(accountId, file));
        } catch (err) {
          reject(err);
        }
      };
      input.addEventListener("change", onChange);
      input.click();
    });
  }

  window.blogAuto = {
    getInitialData: () => callApi("/api/app/getInitialData"),
    openChromeInstallAndQuit: () => callApi("/api/chrome/installAndQuit"),
    refreshCodexUsage: () => callApi("/api/codex/refreshUsage"),
    saveSettings: (settings) => callApi("/api/settings/save", settings),
    saveAccountStore: (store) => callApi("/api/accounts/save", store),
    chooseAccountSampleImage: (accountId) => chooseAccountSampleImageViaHiddenInput(accountId),
    deleteAccountSampleImage: (accountId) => callApi("/api/accounts/deleteSampleImage", { accountId }),
    checkAccountSession: (accountId, options) => callApi("/api/accounts/checkSession", { accountId, options }),
    checkTistorySession: (tistoryBlogId) => callApi("/api/tistory/checkSession", { tistoryBlogId }),
    testTistoryPublish: (form) => callApi("/api/tistory/testPublish", form),
    loadHistory: () => callApi("/api/history/load"),
    startJob: (form) => callApi("/api/job/start", form),
    openRuntimeFolder: () => Promise.resolve(false), // no-op in the browser; use "런타임 폴더 열기" -> file listing page instead
    openFile: (filePath) => window.open(`/api/file/open?path=${encodeURIComponent(filePath)}`, "_blank"),
    showFileInFolder: () => Promise.resolve(false), // no-op in the browser
    onLog: (handler) => on("job:log", handler),
    onStatus: (handler) => on("job:status", handler),
    onTokens: (handler) => on("job:tokens", handler),
    onPreview: (handler) => on("job:preview", handler),
    onSelectedTitle: (handler) => on("job:selectedTitle", handler),
    onComplete: (handler) => on("job:complete", handler),
    onAccountsUpdate: (handler) => on("accounts:update", handler)
  };
})();
