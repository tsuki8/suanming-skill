#!/usr/bin/env node

/**
 * Compare all 13 Zi Wei Dou Shu birth-time indexes without guessing a time.
 *
 * Each candidate delegates chart calculation to ziwei_pan.mjs so validation,
 * lineage options, and the pinned iztro engine stay in one place.
 */

import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const PAN_SCRIPT = join(HERE, "ziwei_pan.mjs");
const SCHEMA_VERSION = "1.0";
const CANDIDATES = [
  { index: 0, label: "早子", branch: "子", zi: "early" },
  { index: 1, label: "丑", branch: "丑" },
  { index: 2, label: "寅", branch: "寅" },
  { index: 3, label: "卯", branch: "卯" },
  { index: 4, label: "辰", branch: "辰" },
  { index: 5, label: "巳", branch: "巳" },
  { index: 6, label: "午", branch: "午" },
  { index: 7, label: "未", branch: "未" },
  { index: 8, label: "申", branch: "申" },
  { index: 9, label: "酉", branch: "酉" },
  { index: 10, label: "戌", branch: "戌" },
  { index: 11, label: "亥", branch: "亥" },
  { index: 12, label: "晚子", branch: "子", zi: "late" },
];
const VALUE_OPTIONS = new Set([
  "solar",
  "lunar",
  "sex",
  "place",
  "algorithm",
  "astro-type",
  "year-divide",
  "horoscope-divide",
  "age-divide",
  "day-divide",
  "target-date",
  "format",
]);
const BOOLEAN_OPTIONS = new Set(["leap", "no-fix-leap", "help"]);
const PASSTHROUGH_ORDER = [
  "solar",
  "lunar",
  "sex",
  "place",
  "algorithm",
  "astro-type",
  "year-divide",
  "horoscope-divide",
  "age-divide",
  "day-divide",
  "target-date",
];
const KEY_PALACES = ["命", "官禄", "财帛", "夫妻", "疾厄", "福德", "迁移"];
const FOCUS_STARS = ["文昌", "文曲", "红鸾", "天喜"];

function usage() {
  return `紫微斗数 13 时辰候选比较

用法：
  node scripts/ziwei_time_compare.mjs --solar YYYY-MM-DD --sex 男|女 [选项]
  node scripts/ziwei_time_compare.mjs --lunar YYYY-MM-DD [--leap] --sex 男|女 [选项]

本脚本接受 ziwei_pan.mjs 的出生日期、性别、地点、排盘口径和
--target-date 选项，但不接受 --hour、--shichen 或 --zi。

输出：
  --format markdown|json        默认 markdown
  --help                        显示帮助
`;
}

function fail(message) {
  process.stderr.write(`错误：${message}\n\n${usage()}`);
  process.exit(2);
}

function failFromChild(error, candidate) {
  const stderr = error?.stderr?.toString().trim();
  if (stderr) {
    process.stderr.write(`${stderr}\n`);
  } else {
    process.stderr.write(`候选 ${candidate.label} 排盘失败\n`);
  }
  process.exit(Number.isInteger(error?.status) ? error.status : 2);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) fail(`无法识别的参数：${token}`);
    const key = token.slice(2);
    if (BOOLEAN_OPTIONS.has(key)) {
      args[key] = true;
      continue;
    }
    if (!VALUE_OPTIONS.has(key)) fail(`未知选项：--${key}`);
    if (i + 1 >= argv.length || argv[i + 1].startsWith("--")) fail(`--${key} 缺少值`);
    args[key] = argv[i + 1];
    i += 1;
  }
  return args;
}

function canonicalPalaceName(name) {
  return name.replace(/宫$/u, "");
}

function palace(chart, name) {
  return chart.palaces.find((item) => canonicalPalaceName(item.name) === name);
}

function allStars(palaceItem) {
  return [
    ...(palaceItem.majorStars ?? []),
    ...(palaceItem.minorStars ?? []),
    ...(palaceItem.adjectiveStars ?? []),
  ];
}

function starText(star) {
  const tags = [star.brightness, star.mutagen].filter(Boolean);
  return tags.length ? `${star.name}〔${tags.join("·")}〕` : star.name;
}

function majorStarsText(palaceItem) {
  return palaceItem?.majorStars?.length ? palaceItem.majorStars.map(starText).join("、") : "空宫";
}

function focusStarRows(chart) {
  const rows = [];
  for (const palaceItem of chart.palaces) {
    for (const star of allStars(palaceItem)) {
      if (FOCUS_STARS.includes(star.name)) {
        rows.push({
          name: star.name,
          palace: palaceItem.name,
          earthlyBranch: palaceItem.earthlyBranch,
          brightness: star.brightness ?? "",
          mutagen: star.mutagen ?? "",
        });
      }
    }
  }
  return rows.sort((a, b) => FOCUS_STARS.indexOf(a.name) - FOCUS_STARS.indexOf(b.name));
}

function mutagenRows(chart) {
  const rows = [];
  for (const palaceItem of chart.palaces) {
    for (const star of allStars(palaceItem)) {
      if (star.mutagen) {
        rows.push({
          mutagen: star.mutagen,
          star: star.name,
          palace: palaceItem.name,
          earthlyBranch: palaceItem.earthlyBranch,
        });
      }
    }
  }
  return rows;
}

function targetSummary(target) {
  if (!target) return null;
  return {
    solarDate: target.solarDate,
    lunarDate: target.lunarDate,
    nominalAge: target.age.nominalAge,
    decadal: {
      heavenlyStem: target.decadal.heavenlyStem,
      earthlyBranch: target.decadal.earthlyBranch,
      palaceNames: target.decadal.palaceNames,
      mutagen: target.decadal.mutagen,
    },
    yearly: {
      heavenlyStem: target.yearly.heavenlyStem,
      earthlyBranch: target.yearly.earthlyBranch,
      palaceNames: target.yearly.palaceNames,
      mutagen: target.yearly.mutagen,
    },
  };
}

function candidateSummary(candidate, payload) {
  const keyPalaces = Object.fromEntries(
    KEY_PALACES.map((name) => {
      const item = palace(payload.chart, name);
      return [name, {
        name: item.name,
        earthlyBranch: item.earthlyBranch,
        majorStars: item.majorStars,
        isBodyPalace: item.isBodyPalace,
      }];
    }),
  );
  return {
    index: candidate.index,
    label: candidate.label,
    time: payload.chart.time,
    timeRange: payload.chart.timeRange,
    chineseDate: payload.chart.chineseDate,
    soulPalaceBranch: payload.chart.earthlyBranchOfSoulPalace,
    bodyPalaceBranch: payload.chart.earthlyBranchOfBodyPalace,
    soul: payload.chart.soul,
    body: payload.chart.body,
    fiveElementsClass: payload.chart.fiveElementsClass,
    keyPalaces,
    birthMutagens: mutagenRows(payload.chart),
    focusStars: focusStarRows(payload.chart),
    decadals: payload.decadals.map((item) => ({
      ageRange: item.ageRange,
      yearRange: item.yearRange,
      palaceName: item.palaceName,
      heavenlyStem: item.heavenlyStem,
      earthlyBranch: item.earthlyBranch,
      mutagen: item.mutagen,
    })),
    target: targetSummary(payload.target),
  };
}

function runCandidate(args, candidate) {
  const childArgs = [];
  for (const key of PASSTHROUGH_ORDER) {
    if (args[key] !== undefined) childArgs.push(`--${key}`, args[key]);
  }
  if (args.leap) childArgs.push("--leap");
  if (args["no-fix-leap"]) childArgs.push("--no-fix-leap");
  childArgs.push("--shichen", candidate.branch);
  if (candidate.zi) childArgs.push("--zi", candidate.zi);
  childArgs.push("--format", "json");

  const stdout = execFileSync(process.execPath, [PAN_SCRIPT, ...childArgs], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return JSON.parse(stdout);
}

function focusText(candidate, names) {
  const rows = candidate.focusStars.filter((row) => names.includes(row.name));
  return rows.length
    ? rows.map((row) => `${row.name}@${canonicalPalaceName(row.palace)}${row.earthlyBranch}`).join("、")
    : "—";
}

function renderMarkdown(payload) {
  const lines = [
    "# 紫微斗数 13 时辰候选比较",
    "",
    `- 日期：${payload.input.dateType === "solar" ? "公历" : "农历"} ${payload.input.date}${payload.input.isLeapMonth ? "（闰月）" : ""}`,
    `- 性别：${payload.input.gender}`,
    `- 口径：${payload.config.algorithm === "default" ? "通行版" : `中州派${payload.config.astroTypeLabel}`}`,
  ];
  if (payload.input.place) lines.push(`- 出生地：${payload.input.place}`);
  if (payload.input.targetDate) lines.push(`- 校准目标日期：${payload.input.targetDate}`);
  lines.push(
    "",
    "| 索引 | 候选 | 时间范围 | 命／身宫 | 五行局 | 命宫主星 | 官禄主星 | 财帛主星 | 夫妻主星 | 昌曲 | 红鸾天喜 |",
    "|---:|---|---|---|---|---|---|---|---|---|---|",
  );
  for (const item of payload.candidates) {
    lines.push(`| ${item.index} | ${item.label} | ${item.timeRange} | ${item.soulPalaceBranch}／${item.bodyPalaceBranch} | ${item.fiveElementsClass} | ${majorStarsText(item.keyPalaces["命"])} | ${majorStarsText(item.keyPalaces["官禄"])} | ${majorStarsText(item.keyPalaces["财帛"])} | ${majorStarsText(item.keyPalaces["夫妻"])} | ${focusText(item, ["文昌", "文曲"])} | ${focusText(item, ["红鸾", "天喜"])} |`);
  }
  lines.push(
    "",
    "> 本表只列结构差异，不自动判定出生时辰。请优先核对出生记录、家属记忆和有明确年份的经历，再保留 2–3 个候选继续校准。传统命理仅供文化研究与娱乐参考。",
    "",
  );
  return lines.join("\n");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(usage());
    return;
  }
  if (Boolean(args.solar) === Boolean(args.lunar)) fail("必须且只能提供 --solar 或 --lunar");
  if (!args.sex) fail("必须提供 --sex 男|女");
  if (args.format && !["markdown", "json"].includes(args.format)) fail("--format 只能是 markdown 或 json");

  let firstPayload;
  const candidates = CANDIDATES.map((candidate) => {
    try {
      const payload = runCandidate(args, candidate);
      firstPayload ??= payload;
      return candidateSummary(candidate, payload);
    } catch (error) {
      failFromChild(error, candidate);
    }
  });
  const payload = {
    schemaVersion: SCHEMA_VERSION,
    engine: firstPayload.engine,
    input: {
      dateType: firstPayload.input.dateType,
      date: firstPayload.input.date,
      isLeapMonth: firstPayload.input.isLeapMonth,
      gender: firstPayload.input.gender,
      place: firstPayload.input.place,
      targetDate: firstPayload.input.targetDate,
    },
    config: firstPayload.config,
    candidates,
  };

  if (args.format === "json") {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(renderMarkdown(payload));
  }
}

main();
