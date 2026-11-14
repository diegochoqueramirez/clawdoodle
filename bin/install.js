#!/usr/bin/env node
// npx clawdoodle [--global | --project] [--force] [--no-setup]
// Copies the skill to ~/.claude/skills/clawdoodle (or ./.claude/skills/clawdoodle with --project),
// then creates its Python venv (Pillow) and runs `clawd doctor`.
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const args = new Set(process.argv.slice(2));
if (args.has("--help") || args.has("-h")) {
  console.log("Usage: npx clawdoodle [--global | --project] [--force] [--no-setup]\n" +
    "  --global    install into ~/.claude/skills (all projects); skips the question\n" +
    "  --project   install into ./.claude/skills (this project only) instead of ~/.claude/skills\n" +
    "  --force     overwrite an existing install (your clawdoodles/ projects are never touched)\n" +
    "  --no-setup  copy files only; skip the Python venv / Pillow / Chrome check");
  process.exit(0);
}

const readline = require("readline");

function ask(question, options) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    console.log(question);
    options.forEach((o, i) => console.log(`  ${i + 1}) ${o}`));
    rl.question("Choose [1]: ", (a) => { rl.close(); const n = parseInt(a, 10); resolve(n >= 1 && n <= options.length ? n - 1 : 0); });
  });
}

async function main() {
const src = path.join(__dirname, "..", ".claude", "skills", "clawdoodle");
let project = args.has("--project");
if (!project && !args.has("--global") && process.stdin.isTTY && process.stdout.isTTY) {
  const i = await ask("Where do you want to install clawdoodle?", [
    `Global: all your projects (${path.join(os.homedir(), ".claude", "skills")})`,
    `This project only (${path.join(process.cwd(), ".claude", "skills")})`,
  ]);
  project = i === 1;
}
const base = project ? path.join(process.cwd(), ".claude", "skills") : path.join(os.homedir(), ".claude", "skills");
const dest = path.join(base, "clawdoodle");

if (!fs.existsSync(src)) { console.error("Skill files not found in the package."); process.exit(1); }
if (fs.existsSync(dest)) {
  if (!args.has("--force")) {
    console.error(`Already installed at ${dest}\nRe-run with --force to update it.`);
    process.exit(1);
  }
  // keep the venv so an update does not need a reinstall of Pillow
  for (const e of fs.readdirSync(dest)) {
    if (e === "engine") {
      for (const f of fs.readdirSync(path.join(dest, "engine"))) {
        if (f !== ".venv") fs.rmSync(path.join(dest, "engine", f), { recursive: true, force: true });
      }
    } else fs.rmSync(path.join(dest, e), { recursive: true, force: true });
  }
}
fs.mkdirSync(base, { recursive: true });
fs.cpSync(src, dest, {
  recursive: true,
  filter: (p) => !/[\\/](\.venv|__pycache__)([\\/]|$)/.test(p),
});
console.log(`Skill copied to ${dest}`);

if (args.has("--no-setup")) { console.log(`Next: python3 "${path.join(dest, "scripts", "setup.py")}"`); process.exit(0); }

const candidates = process.platform === "win32" ? [["py", "-3"], ["python"], ["python3"]] : [["python3"], ["python"]];
const setup = path.join(dest, "scripts", "setup.py");
let ok = false, found = false;
for (const [cmd, ...pre] of candidates) {
  const probe = spawnSync(cmd, [...pre, "--version"], { encoding: "utf8" });
  if (probe.error || probe.status !== 0) continue;
  found = true;
  console.log(`Setting up the Python environment with ${cmd} (Pillow, Chrome check)...`);
  const r = spawnSync(cmd, [...pre, setup], { stdio: "inherit" });
  ok = r.status === 0;
  break;
}
if (!found) console.error("Python 3.9+ was not found. Install it, then run: python scripts/setup.py inside " + dest);
else if (!ok) console.error(`Setup did not finish cleanly. Fix the message above and re-run: python "${setup}"`);
else console.log("\nDone. Open Claude Code and run:  /clawdoodle <topic>");
process.exit(found && ok ? 0 : 1);
}
main().catch((e) => { console.error(e.message || e); process.exit(1); });
