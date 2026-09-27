"use strict";
/**
 * scripts/n8n_gateway.py 프록시 클라이언트 (127.0.0.1:8766, VPS 로컬 전용).
 *
 * 이 콘솔은 WP/Blogspot/뉴스 발행 로직을 절대 재구현하지 않는다 — "대시보드+트리거만" 원칙
 * (2026-09-27 Chairman 확인). 여기서는 기존 게이트웨이의 /health, /run/<action>,
 * /pipeline/<stage> 를 그대로 호출만 한다.
 *
 * N8N_GATEWAY_TOKEN 환경변수가 없으면 트리거 호출은 501로 명확히 실패한다 (조용히 무시하지 않음) —
 * 이 토큰 값은 이 세션이 알지 못하며, VPS의 /etc/london-project-claude-console/env 에 Chairman/GPT
 * 트랙이 직접 넣어야 한다.
 */

const GATEWAY_BASE = process.env.N8N_GATEWAY_URL || "http://127.0.0.1:8766";
const GATEWAY_TOKEN = process.env.N8N_GATEWAY_TOKEN || "";

async function callGateway(pathname, { method = "GET", body } = {}) {
  if (method !== "GET" && !GATEWAY_TOKEN) {
    const err = new Error(
      "N8N_GATEWAY_TOKEN이 설정되지 않았습니다 — /etc/london-project-claude-console/env 에 값을 추가한 뒤 lpc-console 서비스를 재시작하세요."
    );
    err.statusCode = 501;
    throw err;
  }
  const headers = { "Content-Type": "application/json" };
  if (GATEWAY_TOKEN) headers.Authorization = `Bearer ${GATEWAY_TOKEN}`;

  const res = await fetch(`${GATEWAY_BASE}${pathname}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { ok: false, raw: text };
  }
  if (!res.ok) {
    const err = new Error(json.error || `gateway ${res.status}`);
    err.statusCode = res.status;
    err.body = json;
    throw err;
  }
  return json;
}

function health() {
  return callGateway("/health");
}

function runAction(action) {
  return callGateway(`/run/${encodeURIComponent(action)}`, { method: "POST", body: {} });
}

function pipelineStage(stage, payload) {
  return callGateway(`/pipeline/${encodeURIComponent(stage)}`, { method: "POST", body: payload || {} });
}

module.exports = { health, runAction, pipelineStage, GATEWAY_BASE, hasToken: () => Boolean(GATEWAY_TOKEN) };
