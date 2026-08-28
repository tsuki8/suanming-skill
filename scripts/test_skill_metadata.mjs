import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const SKILL = readFileSync(join(ROOT, "SKILL.md"), "utf8");
const README = readFileSync(join(ROOT, "README.md"), "utf8");
const OPENAI_METADATA = readFileSync(join(ROOT, "agents", "openai.yaml"), "utf8");

test("SKILL.md uses shared Agent Skills frontmatter", () => {
  const match = SKILL.match(/^---\n([\s\S]*?)\n---\n/);
  assert.ok(match, "SKILL.md must start with YAML frontmatter");

  const keys = [...match[1].matchAll(/^([a-z][a-z0-9-]*):/gm)].map((row) => row[1]);
  assert.deepEqual(keys, ["name", "description"]);
  assert.match(match[1], /^name: ziwei-skill$/m);
  assert.match(SKILL, /\$\{CLAUDE_SKILL_DIR\}/);
});

test("all bundled resources referenced by the shared skill exist", () => {
  const requiredPaths = [
    "agents/openai.yaml",
    "references/calculation.md",
    "references/interpretation.md",
    "references/supplementary.md",
    "scripts/ziwei_pan.mjs",
    "scripts/ziwei_time_compare.mjs",
    "scripts/ziwei_auto.py",
  ];

  for (const relativePath of requiredPaths) {
    assert.equal(existsSync(join(ROOT, relativePath)), true, `${relativePath} should exist`);
  }
});

test("host installation and authentication documentation stays discoverable", () => {
  for (const expected of [
    "~/.agents/skills/ziwei-skill",
    "~/.claude/skills/ziwei-skill",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
  ]) {
    assert.match(README, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(OPENAI_METADATA, /\$ziwei-skill/);
});
