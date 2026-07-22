// End-to-end smoke test for the frozen Keel backend bundle.
//
//   node scripts/smoke.mjs <bundle-dir>     # dir containing keel-backend[.exe]
//
// Proves the distributable works in a clean sandbox BEFORE packaging:
//   1. boots the frozen sidecar with a throwaway HOME and no Python env vars
//      (recipients have no Python — the bundle must be fully self-contained),
//   2. health-gates /api/health, then asserts a sweep of core endpoints is 200,
//   3. creates a terminal session and does a real PTY round-trip over WebSocket,
//   4. runs the bundled keel CLI (multi-call `cli` dispatch): --help, admin show,
//      and a real agent creation (`keel agent add`) into a temp project.
//
// Requires Node 22+ (native fetch + WebSocket). Exits non-zero on any failure.
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, existsSync, readdirSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import process from "node:process";

const bundleDir = process.argv[2];
if (!bundleDir) {
  console.error("usage: node scripts/smoke.mjs <bundle-dir>");
  process.exit(2);
}
const exe = path.join(
  bundleDir,
  process.platform === "win32" ? "keel-backend.exe" : "keel-backend"
);
if (!existsSync(exe)) {
  console.error(`FAIL: backend executable not found: ${exe}`);
  process.exit(1);
}

// Clean sandbox: throwaway HOME, and strip Python/venv vars so nothing on the
// build machine can leak into the frozen process.
const fakeHome = mkdtempSync(path.join(tmpdir(), "keel-smoke-home-"));
const env = { ...process.env, HOME: fakeHome, USERPROFILE: fakeHome };
for (const k of Object.keys(env)) {
  if (/^(PYTHON|VIRTUAL_ENV|CONDA)/i.test(k)) delete env[k];
}

const PORT = 18734 + Math.floor(Math.random() * 1000);
const BASE = `http://127.0.0.1:${PORT}`;
let failures = 0;
const ok = (label) => console.log(`  ✓ ${label}`);
const fail = (label, detail = "") => {
  failures++;
  console.error(`  ✗ ${label}${detail ? ` — ${detail}` : ""}`);
};

console.log(`Booting frozen backend: ${exe} (port ${PORT}, HOME=${fakeHome})`);
const server = spawn(exe, ["--host", "127.0.0.1", "--port", String(PORT)], {
  env,
  stdio: ["ignore", "pipe", "pipe"],
});
let serverLog = "";
server.stdout.on("data", (d) => (serverLog += d.toString()));
server.stderr.on("data", (d) => (serverLog += d.toString()));
let serverExited = false;
server.on("exit", () => (serverExited = true));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitHealthy(timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (serverExited) throw new Error("backend exited during startup");
    try {
      const r = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(2000) });
      if (r.status === 200) return;
    } catch {
      /* not up yet */
    }
    await sleep(500);
  }
  throw new Error("health check timed out");
}

async function sweepEndpoints() {
  // Core reads that must be 200 on a fresh, unconfigured install.
  const endpoints = [
    "/api/health",
    "/api/overview",
    "/api/agents",
    "/api/agents/projects",
    "/api/auth/me",
    "/api/auth/roles",
    "/api/admin/settings",
    "/api/activity",
    "/api/activity/stats",
    "/api/mcp/servers",
    "/api/mcp/docker",
    "/api/kg/neo4j/preflight",
    "/api/setup/status",
    "/api/setup/doctor",
    "/api/terminal/sessions",
    "/api/execution/governance",
    "/api/execution/engines",
    "/api/code/graphs",
    "/api/skills/audit",
    "/api/skills/security/status",
  ];
  for (const ep of endpoints) {
    try {
      const r = await fetch(`${BASE}${ep}`, { signal: AbortSignal.timeout(30000) });
      r.status === 200 ? ok(`GET ${ep} -> 200`) : fail(`GET ${ep}`, `status ${r.status}`);
    } catch (e) {
      fail(`GET ${ep}`, e.message);
    }
  }
}

async function mcpRegistrationRoundTrip() {
  // The packaged app must let users register a REMOTE MCP server (no Docker).
  const add = await fetch(`${BASE}/api/mcp/servers`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name: "smoke-remote", url: "https://mcp.example.com:8128/sse",
                           type: "sse", description: "smoke test entry" }),
  });
  if (add.status !== 200) return fail("MCP register", `status ${add.status}`);
  const added = await add.json();
  added.source === "registry"
    ? ok(`MCP server registered (${added.name}, source=registry)`)
    : fail("MCP register", `unexpected source ${added.source}`);

  const list = await (await fetch(`${BASE}/api/mcp/servers`)).json();
  list.some((s) => s.name === "smoke-remote")
    ? ok("registered MCP appears in list")
    : fail("MCP list", "registered server missing");

  const del = await fetch(`${BASE}/api/mcp/servers/smoke-remote`, { method: "DELETE" });
  del.status === 200 ? ok("MCP server removed") : fail("MCP remove", `status ${del.status}`);
}

async function modelFallbackDraft() {
  // With NO model configured, the built-in test-mode provider must still
  // produce schema-compliant story drafts — "testable from the package".
  const r = await fetch(`${BASE}/api/ideate/draft`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      context: "Users need offline exports and audit logging for compliance reviews.",
      count: 2,
    }),
    signal: AbortSignal.timeout(30000),
  });
  if (r.status !== 200) return fail("ideate draft (no model)", `status ${r.status}`);
  const data = await r.json();
  const stories = data.stories ?? [];
  stories.length > 0 && stories[0].title
    ? ok(`ideate draft works with no model configured (${stories.length} stories, source=${data.source})`)
    : fail("ideate draft (no model)", "no stories returned");
}

async function buildGovernanceGate() {
  // Fresh install default is "warn": a domain-less session bundle still works.
  const preview = (body) => fetch(`${BASE}/api/execution/context/preview`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  const warnR = await preview({ prompt: "smoke governance", title: "smoke" });
  warnR.status === 200
    ? ok("domain-less session allowed under default 'warn'")
    : fail("governance warn path", `status ${warnR.status}`);

  // Flip the admin default to enforce -> the same request must be refused (403).
  const put = (level) => fetch(`${BASE}/api/admin/settings`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ build_governance_default: level }),
  });
  const enf = await put("enforce");
  if (enf.status !== 200) return fail("governance set enforce", `status ${enf.status}`);
  const blocked = await preview({ prompt: "smoke governance", title: "smoke" });
  blocked.status === 403
    ? ok("domain-less session refused under 'enforce' (403)")
    : fail("governance enforce path", `expected 403, got ${blocked.status}`);
  await put("warn"); // restore the adoption-friendly default
}

async function neutralBuildSessions() {
  const post = (path, body) => fetch(`${BASE}${path}`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify(body), signal: AbortSignal.timeout(30000),
  });
  // Launch on the vendor-neutral 'local' engine (dry-run) through the seam.
  const s = await post("/api/execution/session", { prompt: "smoke build", engine: "local", dry_run: true });
  if (s.status === 200 && (await s.json()).engine === "local")
    ok("neutral session launch (local, dry-run)");
  else fail("execution/session", `status ${s.status}`);
  // Ask the local engine (answers inline; test-mode → non-authoritative).
  const a = await post("/api/execution/ask", { prompt: "what is this?", engine: "local" });
  a.status === 200 ? ok("engine ask (local)") : fail("execution/ask", `status ${a.status}`);
}

async function terminalRoundTrip() {
  const create = await fetch(`${BASE}/api/terminal/sessions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ cols: 100, rows: 30, title: "smoke" }),
  });
  if (create.status !== 200) return fail("terminal create", `status ${create.status}`);
  const { id } = await create.json();
  ok(`terminal session created (${id})`);

  const marker = `KEEL_SMOKE_${Date.now()}`;
  const sawMarker = await new Promise((resolve) => {
    const ws = new WebSocket(`ws://127.0.0.1:${PORT}/api/terminal/sessions/${id}/ws`);
    ws.binaryType = "arraybuffer";
    let out = "";
    const timer = setTimeout(() => {
      ws.close();
      resolve(false);
    }, 20000);
    ws.onopen = () => ws.send(new TextEncoder().encode(`echo ${marker}\r`));
    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) out += new TextDecoder().decode(ev.data);
      else if (typeof ev.data === "string") out += ev.data;
      // Marker appears once as the echoed keystrokes; require the OUTPUT line
      // (2nd occurrence) to prove the shell actually executed the command.
      if (out.split(marker).length > 2) {
        clearTimeout(timer);
        ws.close();
        resolve(true);
      }
    };
    ws.onerror = () => {
      clearTimeout(timer);
      resolve(false);
    };
  });
  sawMarker ? ok("terminal PTY round-trip (echo via WebSocket)") : fail("terminal PTY round-trip");
  await fetch(`${BASE}/api/terminal/sessions/${id}`, { method: "DELETE" }).catch(() => {});
}

function runCli(args, expectInOutput, timeoutMs = 120000) {
  const r = spawnSync(exe, ["cli", ...args], {
    env,
    encoding: "utf-8",
    timeout: timeoutMs,
  });
  const output = `${r.stdout ?? ""}${r.stderr ?? ""}`;
  const label = `keel ${args.join(" ")}`;
  if (r.status !== 0) return fail(label, `exit ${r.status}: ${output.slice(-400)}`);
  if (expectInOutput && !output.includes(expectInOutput))
    return fail(label, `missing "${expectInOutput}" in output`);
  ok(label);
}

function cliAndAgentCreation() {
  runCli(["--help"], "Usage");
  runCli(["admin", "show"], "App title");
  // The real user flow: scaffold a project, then add an agent to it.
  const workdir = path.join(fakeHome, "smoke-work");
  mkdirSync(workdir, { recursive: true });
  runCli(["project", "create", "smoke-project", "--path", workdir,
          "--framework", "adk", "--use-case", "basic"]);
  const proj = path.join(workdir, "smoke-project");
  runCli(["agent", "add", "smoke-agent", "--type", "basic", "--path", proj]);
  const created =
    existsSync(proj) && readdirSync(proj, { recursive: true }).some((f) => /smoke.agent|agent/i.test(String(f)));
  created
    ? ok(`agent creation wrote files into ${proj}`)
    : fail("agent creation", "no agent files generated");
}

try {
  await waitHealthy();
  ok("backend healthy (frozen, clean sandbox)");
  // Boot must install the `keel` wrapper terminal sessions rely on.
  const wrapper = path.join(
    fakeHome, ".keel", "bin", process.platform === "win32" ? "keel.cmd" : "keel");
  existsSync(wrapper)
    ? ok(`keel CLI wrapper installed (${wrapper})`)
    : fail("keel CLI wrapper", `missing ${wrapper}`);
  console.log("\n— endpoint sweep —");
  await sweepEndpoints();
  console.log("\n— MCP registration e2e —");
  await mcpRegistrationRoundTrip();
  console.log("\n— model fallback e2e (test-mode) —");
  await modelFallbackDraft();
  console.log("\n— build governance e2e —");
  await buildGovernanceGate();
  console.log("\n— vendor-neutral build sessions e2e —");
  await neutralBuildSessions();
  console.log("\n— terminal e2e —");
  await terminalRoundTrip();
  console.log("\n— keel CLI e2e (bundled, multi-call) —");
  cliAndAgentCreation();
} catch (e) {
  fail("smoke run", e.message);
  console.error("\n--- backend log (tail) ---\n" + serverLog.slice(-3000));
} finally {
  server.kill("SIGTERM");
  await sleep(1500);
  if (!serverExited) server.kill("SIGKILL");
}

if (failures) {
  console.error(`\nSMOKE FAILED: ${failures} check(s) failed`);
  console.error("\n--- backend log (tail) ---\n" + serverLog.slice(-3000));
  process.exit(1);
}
console.log("\nSMOKE PASSED: distributable backend is healthy end to end");
