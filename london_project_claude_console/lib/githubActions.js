"use strict";

/** GitHub Actions dispatch client. No VPS, SSH, systemd, or n8n dependency. */
const REPO = process.env.LONDON_PROJECT_GITHUB_REPO || "huh0303-cmyk/-WP-QWEN-autobot";
const REF = process.env.LONDON_PROJECT_GITHUB_REF || "main";
const TOKEN = process.env.LONDON_PROJECT_GITHUB_TOKEN || process.env.GH_DISPATCH_TOKEN || process.env.GITHUB_TOKEN || "";
const API = "https://api.github.com";

const ACTIONS = {
  wp25_tick: { workflow: "daily-publication-floor.yml", inputs: { platform: "wordpress" } },
  blogger33_daily: { workflow: "blogger-33-daily-github.yml", inputs: { site_key: "", slot: "" } },
  news2: { workflow: "newsrooms-daily-publisher.yml", inputs: { preferred_category: "", source_url: "", source_item: "" } },
};

function requireToken() {
  if (!TOKEN) {
    const error = new Error("GitHub Actions token is missing. Configure LONDON_PROJECT_GITHUB_TOKEN with Actions write permission; no job was started.");
    error.statusCode = 501;
    throw error;
  }
}

async function request(pathname, options = {}) {
  requireToken();
  const response = await fetch(API + pathname, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const bodyText = await response.text();
  let body = {};
  try { body = bodyText ? JSON.parse(bodyText) : {}; } catch { body = { message: bodyText.slice(0, 200) }; }
  if (!response.ok) {
    const error = new Error(body.message || `GitHub API HTTP ${response.status}`);
    error.statusCode = response.status;
    throw error;
  }
  return body;
}

async function health() {
  const data = await request(`/repos/${REPO}/actions/runs?per_page=5`);
  return {
    ok: true,
    platform: "github-actions",
    repository: REPO,
    latestRuns: (data.workflow_runs || []).map(run => ({
      id: run.id,
      name: run.name,
      status: run.status,
      conclusion: run.conclusion,
      html_url: run.html_url,
      created_at: run.created_at,
    })),
  };
}

async function runAction(action) {
  const config = ACTIONS[action];
  if (!config) {
    const error = new Error(`No GitHub-native workflow mapping is configured for action: ${action}`);
    error.statusCode = 501;
    throw error;
  }
  await request(`/repos/${REPO}/actions/workflows/${config.workflow}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: REF, inputs: config.inputs }),
  });
  return {
    ok: true,
    platform: "github-actions",
    workflow: config.workflow,
    repository: REPO,
    status: "dispatch_requested",
    url: `https://github.com/${REPO}/actions/workflows/${config.workflow}`,
  };
}

async function pipelineStage(stage) {
  const error = new Error(`Pipeline stage '${stage}' has no verified GitHub-native workflow mapping yet. No work was started.`);
  error.statusCode = 501;
  throw error;
}

module.exports = { health, runAction, pipelineStage, REPO, REF };
