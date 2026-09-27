// One-time build script: transforms the original Electron main.js (jobRunner.raw.js)
// into a portable jobRunner.js core module with no Electron dependency.
// Business logic (job orchestration, keyword-lane planning, session verification, etc.)
// between the header and the ipcMain block is copied BYTE-FOR-BYTE / UNCHANGED.
// Only Electron-specific plumbing is replaced:
//   - electron require, app.*, BrowserWindow, dialog -> removed / replaced
//   - emit() -> broadcast(channel, payload) via an injected callback
//   - ipcMain.handle(...) block -> module.exports of plain async functions
const fs = require("node:fs");
const path = require("node:path");

const raw = fs.readFileSync(path.join(__dirname, "jobRunner.raw.js"), "utf8");
const lines = raw.split("\n");

// Header: lines 1-80 (1-indexed) -> index 0-79
const headerEnd = lines.findIndex((l) => l.startsWith("function safeLog("));
if (headerEnd === -1) throw new Error("safeLog marker not found");

// Body: from safeLog(...) up to (not including) "app.whenReady().then(() => {"
const bodyStartIdx = headerEnd;
const bodyEndIdx = lines.findIndex((l) => l.startsWith("app.whenReady().then(() => {"));
if (bodyEndIdx === -1) throw new Error("app.whenReady marker not found");

const body = lines.slice(bodyStartIdx, bodyEndIdx).join("\n");

const newHeader = `// AUTO-PORTED from blogauto-naver-tistory/src/main.js (Electron) by build_jobRunner.js.
// Business logic below (safeLog ... startJob) is byte-for-byte identical to the
// original Electron app's main.js. Only this header and the exports at the
// bottom differ (no Electron dependency; browser-launch model is unchanged --
// naverPublisher.js/tistoryPublisher.js still launch a real, visible Chrome
// window via playwright-core, now under Xvfb+noVNC on the server -- see
// deploy/README.md).
const path = require("node:path");
const fs = require("node:fs");
const crypto = require("node:crypto");
const zlib = require("node:zlib");
const { pathToFileURL } = require("node:url");
const { readHistory, appendHistory, ensureRuntimeFiles } = require("../lib/history");
const { createEmbedding, cosineSimilarity } = require("../lib/embedding");
const { collectSearchResults, summarizeSourceQuality } = require("../lib/search");
const { runCodexGeneration, fetchCodexUsageSnapshot } = require("../lib/codexRunner");
const { normalizeAgentResult, getPreviewImages } = require("../lib/imageAssets");
const { publishToNaver, checkNaverSession, verifyOpenNaverSession } = require("../lib/naverPublisher");
const { publishToTistory, checkTistorySession } = require("../lib/tistoryPublisher");
const { ensureSettingsFile, normalizeCodexModel, normalizeImageAspectRatio, normalizeMaxBodyImages, resolveCodexCmdPath, readSettings, writeSettings } = require("../lib/settings");
const {
  ensureAccountStoreFile,
  readAccountStore,
  writeAccountStore,
  updateAccountSession,
  getAccountProfileDir
} = require("../lib/accountStore");

let activeJob = null;
const activeNaverSessions = new Map();
const activeTistorySessions = new Map();

// Set by server.js after creating the WebSocket broadcaster (replaces mainWindow.webContents.send).
let broadcastFn = () => {};
function setBroadcaster(fn) {
  broadcastFn = typeof fn === "function" ? fn : () => {};
}

function getRuntimeRoot() {
  const overrideRoot = process.env.BLOGAUTO_RUNTIME_ROOT;
  if (overrideRoot) return path.resolve(overrideRoot);
  return path.join(__dirname, "..", "runtime");
}

function emit(channel, payload) {
  broadcastFn(channel, payload);
}

`;

const tailIpc = lines.slice(bodyEndIdx).join("\n");

// Convert the ipcMain.handle block into exported async functions.
// We keep the exact original request/response logic; only the transport differs
// (Express route in server.js calls these functions directly instead of ipcMain).
const newTail = `
// ---- Below: ported from the ipcMain.handle(...) block in the original main.js.
// Each handler becomes a plain async function called by an Express route in server.js.
// dialog.showOpenDialog (native file picker) is replaced by a multer file upload in
// server.js; the uploaded file's disk path is passed in as \`uploadedFilePath\`.

async function getInitialData() {
  const runtimeRoot = getRuntimeRoot();
  const settings = readSettings(runtimeRoot);
  return {
    runtimeRoot,
    codexCmdPath: resolveCodexCmdPath(settings.codexCmdPath),
    chrome: detectChromeInstall(),
    settings,
    accountStore: withAccountImageUrls(runtimeRoot, readAccountStore(runtimeRoot, settings)),
    history: readHistory(runtimeRoot)
  };
}

function saveSettings(settings) {
  const runtimeRoot = getRuntimeRoot();
  return writeSettings(runtimeRoot, settings);
}

async function refreshCodexUsage() {
  const runtimeRoot = getRuntimeRoot();
  const settings = readSettings(runtimeRoot);
  const savedRateLimits = settings.codexRateLimits || null;
  if (activeJob || process.env.BLOGAUTO_SKIP_CODEX_USAGE_REFRESH === "1") {
    return {
      skipped: true,
      rateLimits: savedRateLimits,
      tokenUsage: { total: 0, rateLimits: savedRateLimits }
    };
  }
  let snapshot;
  try {
    snapshot = await fetchCodexUsageSnapshot({
      codexCmdPath: resolveCodexCmdPath(settings.codexCmdPath),
      cwd: runtimeRoot
    });
  } catch (error) {
    snapshot = {
      source: "unavailable",
      unavailableReason: error instanceof Error ? error.message : String(error || "Codex 사용량 조회 실패"),
      rateLimits: null,
      tokenUsage: { total: 0, rateLimits: null }
    };
  }
  if (snapshot.rateLimits) persistCodexRateLimits(runtimeRoot, snapshot.rateLimits);
  if (!snapshot.rateLimits && savedRateLimits) {
    return {
      ...snapshot,
      source: snapshot.source || "saved",
      savedFallback: true,
      rateLimits: savedRateLimits,
      tokenUsage: {
        ...(snapshot.tokenUsage || {}),
        total: Number(snapshot.tokenUsage?.total || 0),
        rateLimits: savedRateLimits
      }
    };
  }
  return snapshot;
}

function saveAccountStore(store) {
  const runtimeRoot = getRuntimeRoot();
  const saved = writeAccountStore(runtimeRoot, store, readSettings(runtimeRoot));
  const publicStore = withAccountImageUrls(runtimeRoot, saved);
  emit("accounts:update", publicStore);
  return publicStore;
}

// options.uploadedFilePath replaces the original dialog.showOpenDialog() result.
async function chooseAccountSampleImage(accountId, uploadedFilePath) {
  const runtimeRoot = getRuntimeRoot();
  const settings = readSettings(runtimeRoot);
  const store = readAccountStore(runtimeRoot, settings);
  const account = store.accounts.find((item) => item.id === accountId);
  if (!account) throw new Error("Account not found.");
  if (!uploadedFilePath) {
    return withAccountImageUrls(runtimeRoot, store);
  }
  const sourcePath = uploadedFilePath;
  const destDir = accountAssetDir(runtimeRoot, account.id);
  fs.mkdirSync(destDir, { recursive: true });
  const destPath = accountSampleImagePath(runtimeRoot, account.id, sourcePath);
  fs.copyFileSync(sourcePath, destPath);
  fs.rmSync(sourcePath, { force: true }); // clean up multer tmp upload
  const nextHash = fileHash(destPath);
  const changed = nextHash !== account.sampleImageHash;
  account.sampleImagePath = destPath;
  account.sampleImageHash = nextHash;
  account.sampleImageUpdatedAt = new Date().toISOString();
  if (changed) {
    account.imageStylePromptStatus = account.imageStylePrompt ? "stale" : "missing";
    account.imageStylePromptError = "";
  }
  const saved = writeAccountStore(runtimeRoot, store, settings);
  const publicStore = withAccountImageUrls(runtimeRoot, saved);
  emit("accounts:update", publicStore);
  return publicStore;
}

function deleteAccountSampleImage(accountId) {
  const runtimeRoot = getRuntimeRoot();
  const settings = readSettings(runtimeRoot);
  const store = readAccountStore(runtimeRoot, settings);
  const account = store.accounts.find((item) => item.id === accountId);
  if (!account) throw new Error("Account not found.");
  const samplePath = String(account.sampleImagePath || "");
  const assetRoot = path.resolve(accountAssetDir(runtimeRoot, account.id));
  const resolvedSample = samplePath ? path.resolve(samplePath) : "";
  if (resolvedSample && resolvedSample.startsWith(assetRoot) && fs.existsSync(resolvedSample)) {
    fs.rmSync(resolvedSample, { force: true });
  }
  account.sampleImagePath = "";
  account.sampleImageHash = "";
  account.sampleImageUpdatedAt = "";
  account.imageStylePrompt = "";
  account.imageStylePromptUpdatedAt = "";
  account.imageStylePromptStatus = "missing";
  account.imageStylePromptSourceImageHash = "";
  account.imageStylePromptError = "";
  const saved = writeAccountStore(runtimeRoot, store, settings);
  const publicStore = withAccountImageUrls(runtimeRoot, saved);
  emit("accounts:update", publicStore);
  return publicStore;
}

async function checkAccountSession(accountId, options = {}) {
  if (activeJob) {
    throw new Error("작업 실행 중에는 계정 세션을 다시 확인할 수 없습니다.");
  }
  const runtimeRoot = getRuntimeRoot();
  const settings = readSettings(runtimeRoot);
  const store = readAccountStore(runtimeRoot, settings);
  const account = store.accounts.find((item) => item.id === accountId);
  if (!account) throw new Error("계정을 찾을 수 없습니다.");
  const browserProfileDir = getAccountProfileDir(runtimeRoot, account);
  const key = sessionKeyFor(account, browserProfileDir);
  safeLog("session", \`계정 profile: \${browserProfileDir}\`);
  const existingNaverSession = reusableNaverSession(key);
  const result = existingNaverSession
    ? await verifyOpenNaverSession({
      blogId: account.blogId || account.naverId,
      browserProfileDir,
      preparedContext: existingNaverSession.context,
      preparedPage: existingNaverSession.page,
      interactiveLogin: true,
      domNotes: settings.naverEditorDomNotes || "",
      runtimeRoot,
      log: (message, level) => safeLog("session", message, level)
    })
    : await checkNaverSession({
      blogId: account.blogId || account.naverId,
      browserProfileDir,
      interactiveLogin: true,
      keepOpen: true,
      requireEditor: true,
      domNotes: settings.naverEditorDomNotes || "",
      runtimeRoot,
      log: (message, level) => safeLog("session", message, level)
    });
  const { preparedSession, page, ...publicResult } = result;
  if (options.includeTistorySession !== false && settings.publishToTistoryAfterNaver === true && settings.tistoryBlogId) {
    try {
      const tistoryProfileDir = getTistoryProfileDir(runtimeRoot, settings.tistoryBlogId);
      const tistoryKey = tistorySessionKey(settings.tistoryBlogId, tistoryProfileDir);
      const existingTistorySession = reusableTistorySession(tistoryKey);
      const tistoryResult = existingTistorySession
        ? {
          status: "valid",
          reason: "reused_open_tistory_editor",
          url: existingTistorySession.page?.url?.() || "",
          preparedSession: existingTistorySession
        }
        : await checkTistorySession({
          tistoryBlogId: settings.tistoryBlogId,
          browserProfileDir: tistoryProfileDir,
          runtimeRoot,
          keepOpen: true,
          log: (message, level) => safeLog("session", message, level)
        });
      if (tistoryResult.preparedSession) {
        activeTistorySessions.set(tistoryKey, tistoryResult.preparedSession);
      }
      publicResult.tistorySession = {
        status: tistoryResult.status,
        reason: tistoryResult.reason || "",
        url: tistoryResult.url || ""
      };
      writeSettings(runtimeRoot, {
        tistorySessionStatus: tistoryResult.status === "valid" ? "valid" : "unknown",
        tistorySessionCheckedAt: new Date().toISOString()
      });
    } catch (error) {
      publicResult.tistorySession = { status: "expired", reason: error.message };
      writeSettings(runtimeRoot, {
        tistorySessionStatus: "expired",
        tistorySessionCheckedAt: new Date().toISOString()
      });
    }
  }
  const sessionStatus = result.status === "valid" ? "valid" : result.status === "expired" ? "expired" : "unknown";
  const saved = updateAccountSession(runtimeRoot, account.id, sessionStatus, settings);
  emit("accounts:update", saved);
  if (result.status !== "valid") {
    safeLog("session", \`\${account.label || account.blogId || account.naverId} 계정 세션이 만료 상태입니다.\`, "warn");
    return publicResult;
  }
  if (preparedSession) activeNaverSessions.set(key, preparedSession);
  safeLog("session", \`\${account.label || account.blogId || account.naverId} 계정 글쓰기 편집기 확인 완료.\`);
  return publicResult;
}

async function checkTistorySessionHandler(tistoryBlogId) {
  if (activeJob) {
    throw new Error("작업 실행 중에는 티스토리 세션을 확인할 수 없습니다.");
  }
  const runtimeRoot = getRuntimeRoot();
  const settings = readSettings(runtimeRoot);
  const selectedBlogId = String(tistoryBlogId || settings.tistoryBlogId || "").trim();
  const browserProfileDir = getTistoryProfileDir(runtimeRoot, selectedBlogId);
  const key = tistorySessionKey(selectedBlogId, browserProfileDir);
  const existingTistorySession = reusableTistorySession(key);
  const result = existingTistorySession
    ? {
      status: "valid",
      reason: "reused_open_tistory_editor",
      url: existingTistorySession.page?.url?.() || "",
      preparedSession: existingTistorySession
    }
    : await checkTistorySession({
      tistoryBlogId: selectedBlogId,
      browserProfileDir,
      runtimeRoot,
      keepOpen: true,
      log: (message, level) => safeLog("session", message, level)
    });
  if (result.preparedSession) activeTistorySessions.set(key, result.preparedSession);
  writeSettings(runtimeRoot, {
    tistoryBlogId: selectedBlogId,
    tistorySessionStatus: result.status === "valid" ? "valid" : "unknown",
    tistorySessionCheckedAt: new Date().toISOString()
  });
  return { status: result.status, reason: result.reason || "", url: result.url || "" };
}

function loadHistory() {
  return readHistory(getRuntimeRoot());
}

function getActiveJob() {
  return activeJob;
}

function detectChromeInstallHandler() {
  return detectChromeInstall();
}

module.exports = {
  setBroadcaster,
  getRuntimeRoot,
  getInitialData,
  saveSettings,
  refreshCodexUsage,
  saveAccountStore,
  chooseAccountSampleImage,
  deleteAccountSampleImage,
  checkAccountSession,
  checkTistorySession: checkTistorySessionHandler,
  startTistoryTestPublish,
  loadHistory,
  startJob,
  getActiveJob,
  detectChromeInstall: detectChromeInstallHandler,
  ensureRuntimeFiles,
  ensureSettingsFile,
  ensureAccountStoreFile,
  readSettings,
  closeAllSessions: async () => {
    for (const key of activeTistorySessions.keys()) {
      await closeTistorySession(key).catch(() => {});
    }
    for (const session of activeNaverSessions.values()) {
      await session.context?.close().catch(() => {});
    }
    activeNaverSessions.clear();
    activeTistorySessions.clear();
  }
};
`;

const out = newHeader + body + newTail;
fs.writeFileSync(path.join(__dirname, "jobRunner.js"), out, "utf8");
console.log("wrote jobRunner.js:", out.split("\n").length, "lines");
