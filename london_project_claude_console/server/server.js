// 런던프로젝트클로드 - 네이버/티스토리 블로그 자동화 콘솔 (web console)
//
// This is the web-server replacement for the Electron main process. It exposes
// the exact same operations as the original preload.js/ipcMain contract, over
// plain HTTP (for request/response calls) and a single WebSocket (for the
// job:log / job:status / job:tokens / job:preview / job:selectedTitle /
// job:complete / accounts:update push events the renderer subscribes to).
//
// Auth: single shared login (owner + Vietnamese staff use the same credentials -
// confirmed decision, no per-user permission tiers). See README.md for setup.
const path = require("node:path");
const fs = require("node:fs");
const http = require("node:http");
const crypto = require("node:crypto");
const express = require("express");
const multer = require("multer");
const cookieParser = require("cookie-parser");
const { WebSocketServer } = require("ws");

const jobRunner = require("./jobRunner");

const PORT = Number(process.env.PORT || 8787);
const APP_USER = process.env.LPC_USER || "admin";
const APP_PASS = process.env.LPC_PASS || "";
const SESSION_SECRET = process.env.LPC_SESSION_SECRET || crypto.randomBytes(32).toString("hex");

if (!APP_PASS) {
  console.warn("[WARN] LPC_PASS is not set. Set LPC_USER/LPC_PASS env vars before exposing this server publicly.");
}

const runtimeRoot = jobRunner.getRuntimeRoot();
jobRunner.ensureRuntimeFiles(runtimeRoot);
jobRunner.ensureSettingsFile(runtimeRoot);
jobRunner.ensureAccountStoreFile(runtimeRoot, jobRunner.readSettings(runtimeRoot));

const uploadTmpDir = path.join(runtimeRoot, "_uploads_tmp");
fs.mkdirSync(uploadTmpDir, { recursive: true });
const upload = multer({ dest: uploadTmpDir, limits: { fileSize: 15 * 1024 * 1024 } });

const app = express();
app.use(express.json({ limit: "10mb" }));
app.use(cookieParser());

// ---- minimal session auth (single shared login) ----
const sessions = new Map(); // token -> expiresAt
const SESSION_TTL_MS = 12 * 60 * 60 * 1000; // 12h

function issueSession() {
  const token = crypto.randomBytes(24).toString("hex");
  sessions.set(token, Date.now() + SESSION_TTL_MS);
  return token;
}

function isValidSession(token) {
  if (!token) return false;
  const expiresAt = sessions.get(token);
  if (!expiresAt) return false;
  if (Date.now() > expiresAt) {
    sessions.delete(token);
    return false;
  }
  return true;
}

function requireAuth(req, res, next) {
  const token = req.cookies?.lpc_session;
  if (isValidSession(token)) return next();
  // Browser page navigation (not a fetch/XHR API call) -> send to the login page.
  if (req.method === "GET" && !req.path.startsWith("/api/") && (req.headers.accept || "").includes("text/html")) {
    return res.redirect("/login");
  }
  return res.status(401).json({ error: "로그인이 필요합니다." });
}

app.post("/auth/login", (req, res) => {
  const { username, password } = req.body || {};
  if (String(username || "") === APP_USER && String(password || "") === APP_PASS && APP_PASS) {
    const token = issueSession();
    res.cookie("lpc_session", token, {
      httpOnly: true,
      sameSite: "lax",
      secure: req.secure,
      maxAge: SESSION_TTL_MS
    });
    return res.json({ ok: true });
  }
  return res.status(401).json({ error: "아이디 또는 비밀번호가 올바르지 않습니다." });
});

app.post("/auth/logout", (req, res) => {
  const token = req.cookies?.lpc_session;
  if (token) sessions.delete(token);
  res.clearCookie("lpc_session");
  res.json({ ok: true });
});

app.get("/auth/status", (req, res) => {
  res.json({ authenticated: isValidSession(req.cookies?.lpc_session) });
});

// login page is the only public HTML route; everything else requires auth (checked below)
app.get("/login", (req, res) => {
  res.sendFile(path.join(__dirname, "..", "public", "login", "index.html"));
});

app.use((req, res, next) => {
  if (req.path.startsWith("/auth/")) return next();
  return requireAuth(req, res, next);
});

app.use(express.static(path.join(__dirname, "..", "public")));

// ---- API routes: 1:1 mapping of the original ipcMain.handle channels ----
const wrap = (fn) => async (req, res) => {
  try {
    const result = await fn(req, res);
    res.json(result === undefined ? {} : result);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message || String(error) });
  }
};

app.post("/api/app/getInitialData", wrap(() => jobRunner.getInitialData()));
app.post("/api/chrome/installAndQuit", wrap(() => ({ ok: true, note: "브라우저 콘솔에서는 Chrome이 서버에 이미 설치되어 있어야 합니다." })));
app.post("/api/settings/save", wrap((req) => jobRunner.saveSettings(req.body)));
app.post("/api/codex/refreshUsage", wrap(() => jobRunner.refreshCodexUsage()));
app.post("/api/accounts/save", wrap((req) => jobRunner.saveAccountStore(req.body)));
app.post("/api/accounts/chooseSampleImage", upload.single("image"), wrap((req) => {
  const accountId = req.body?.accountId;
  const uploadedFilePath = req.file ? req.file.path : null;
  return jobRunner.chooseAccountSampleImage(accountId, uploadedFilePath);
}));
app.post("/api/accounts/deleteSampleImage", wrap((req) => jobRunner.deleteAccountSampleImage(req.body?.accountId)));
app.post("/api/accounts/checkSession", wrap((req) => jobRunner.checkAccountSession(req.body?.accountId, req.body?.options || {})));
app.post("/api/tistory/checkSession", wrap((req) => jobRunner.checkTistorySession(req.body?.tistoryBlogId)));
app.post("/api/tistory/testPublish", wrap((req) => jobRunner.startTistoryTestPublish(req.body)));
app.post("/api/history/load", wrap(() => jobRunner.loadHistory()));
app.post("/api/job/start", wrap((req) => {
  if (jobRunner.getActiveJob()) {
    throw new Error("이미 실행 중인 작업이 있습니다. 완료 후 다시 시도하세요.");
  }
  // Fire-and-forget: progress is streamed over WebSocket (job:log/status/...),
  // matching the original app's async ipcMain.handle("job:start", ...) + event push model.
  jobRunner.startJob(req.body).catch((err) => console.error("[job:start]", err));
  return { started: true };
}));

// Serves files from within the runtime root only (mirrors the path-containment
// check in the original file:open / file:showInFolder handlers).
app.get("/api/file/open", (req, res) => {
  const filePath = String(req.query.path || "");
  if (!filePath) return res.status(400).end();
  const resolvedRoot = path.resolve(runtimeRoot);
  const resolved = path.resolve(filePath);
  if (!resolved.startsWith(resolvedRoot)) return res.status(403).end();
  if (!fs.existsSync(resolved)) return res.status(404).end();
  res.sendFile(resolved);
});

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: "/ws" });

function broadcast(channel, payload) {
  const message = JSON.stringify({ channel, payload });
  for (const client of wss.clients) {
    if (client.readyState === client.OPEN) client.send(message);
  }
}
jobRunner.setBroadcaster(broadcast);

wss.on("connection", (ws, req) => {
  // WebSocket upgrade requests don't go through the express cookie-auth middleware
  // above, so re-check the session cookie here before allowing the socket to stay open.
  const cookieHeader = req.headers.cookie || "";
  const token = /lpc_session=([^;]+)/.exec(cookieHeader)?.[1];
  if (!isValidSession(token)) {
    ws.close(4401, "unauthorized");
  }
});

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
async function shutdown() {
  console.log("Shutting down, closing browser sessions...");
  try { await jobRunner.closeAllSessions(); } catch {}
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 5000);
}

server.listen(PORT, () => {
  console.log(`런던프로젝트클로드 web console listening on :${PORT}`);
  console.log(`runtime root: ${runtimeRoot}`);
});
