#!/usr/bin/env node

/**
 * Deterministic Zi Wei Dou Shu chart CLI.
 *
 * The chart calculation is delegated to the pinned MIT-licensed iztro engine.
 * This wrapper owns argument validation plus stable Markdown/JSON rendering.
 */

import { astro } from "iztro";

const ENGINE_VERSION = "2.6.0";
const SCHEMA_VERSION = "1.0";
const SHICHEN = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"];
const PALACE_BRANCHES = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"];
const MUTAGEN_NAMES = ["禄", "权", "科", "忌"];

function usage() {
  return `紫微斗数排盘（iztro ${ENGINE_VERSION}）

用法：
  node scripts/ziwei_pan.mjs --solar YYYY-MM-DD --hour HH:MM --sex 男|女 [选项]
  node scripts/ziwei_pan.mjs --lunar YYYY-MM-DD --shichen 子|丑|...|亥 --sex 男|女 [选项]

日期与时辰：
  --solar DATE                 公历生日
  --lunar DATE                 农历生日，与 --solar 互斥
  --leap                       农历日期为闰月
  --hour HH:MM                 24 小时制出生时间
  --shichen BRANCH             出生时辰；子时默认早子时
  --zi early|late              --shichen 子时指定早子/晚子
  --sex 男|女                  性别
  --place TEXT                 出生地，仅展示并用于边界提醒

排盘口径：
  --algorithm default|zhongzhou  通行版（默认）或中州派
  --astro-type heaven|earth|human 中州派天盘/地盘/人盘，默认 heaven
  --year-divide normal|exact      正月初一或立春换年，默认 normal
  --horoscope-divide normal|exact 运限按农历月或节气分界，默认 normal
  --age-divide normal|birthday    虚岁按自然年或生日分界，默认 normal
  --day-divide forward|current    晚子时归次日或当日，默认 forward
  --no-fix-leap                  不拆分闰月前后半月

输出：
  --target-date YYYY-MM-DD      附加指定日期的大限与流年数据
  --format markdown|json        默认 markdown
  --help                        显示帮助
`;
}

function fail(message) {
  process.stderr.write(`错误：${message}\n\n${usage()}`);
  process.exit(2);
}

function parseArgs(argv) {
  const valueOptions = new Set([
    "solar",
    "lunar",
    "hour",
    "shichen",
    "zi",
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
  const booleanOptions = new Set(["leap", "no-fix-leap", "help"]);
  const args = {};

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) fail(`无法识别的参数：${token}`);
    const key = token.slice(2);
    if (booleanOptions.has(key)) {
      args[key] = true;
      continue;
    }
    if (!valueOptions.has(key)) fail(`未知选项：--${key}`);
    if (i + 1 >= argv.length || argv[i + 1].startsWith("--")) fail(`--${key} 缺少值`);
    args[key] = argv[i + 1];
    i += 1;
  }
  return args;
}

function normalizeDate(value, label, lunar = false) {
  const match = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(value ?? "");
  if (!match) fail(`${label}必须使用 YYYY-MM-DD 格式`);
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1900 || year > 2100) fail(`${label}年份目前支持 1900–2100`);
  if (month < 1 || month > 12) fail(`${label}月份超出范围`);
  if (lunar) {
    if (day < 1 || day > 30) fail(`${label}日期超出农历月份范围`);
  } else {
    const probe = new Date(Date.UTC(year, month - 1, day));
    if (
      probe.getUTCFullYear() !== year ||
      probe.getUTCMonth() !== month - 1 ||
      probe.getUTCDate() !== day
    ) {
      fail(`${label}不是有效公历日期`);
    }
  }
  return `${year}-${month}-${day}`;
}

function parseClock(value) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value ?? "");
  if (!match) fail("--hour 必须使用 HH:MM 格式");
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) fail("--hour 超出 00:00–23:59 范围");
  return { hour, minute, display: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}` };
}

function timeIndexFromClock(clock) {
  if (clock.hour === 23) return 12;
  if (clock.hour === 0) return 0;
  return Math.floor((clock.hour + 1) / 2);
}

function nearestBoundaryMinutes(clock) {
  const minuteOfDay = clock.hour * 60 + clock.minute;
  const boundaries = [];
  for (let hour = 1; hour <= 23; hour += 2) boundaries.push(hour * 60);
  return Math.min(...boundaries.map((boundary) => Math.abs(minuteOfDay - boundary)));
}

function resolveTime(args, warnings) {
  if (args.hour && args.shichen) fail("--hour 与 --shichen 不能同时使用");
  if (!args.hour && !args.shichen) fail("紫微斗数必须提供 --hour 或 --shichen");

  if (args.hour) {
    const clock = parseClock(args.hour);
    if (nearestBoundaryMinutes(clock) <= 15) {
      warnings.push("出生时间距离时辰边界不超过15分钟；若出生地经度偏离东经120°，应先校正真太阳时再定盘。");
    }
    const timeIndex = timeIndexFromClock(clock);
    return {
      timeIndex,
      display: clock.display,
      shichen: timeIndex === 12 ? "晚子" : SHICHEN[timeIndex],
    };
  }

  const branch = args.shichen;
  const branchIndex = SHICHEN.indexOf(branch);
  if (branchIndex < 0) fail("--shichen 必须是子、丑、寅、卯、辰、巳、午、未、申、酉、戌或亥");
  if (args.zi && branch !== "子") fail("--zi 只能与 --shichen 子 一起使用");
  if (args.zi && !["early", "late"].includes(args.zi)) fail("--zi 只能是 early 或 late");
  if (branch === "子") {
    const late = args.zi === "late";
    if (!args.zi) warnings.push("只提供了子时，默认按早子时排盘；若为23:00–24:00请加 --zi late。");
    return { timeIndex: late ? 12 : 0, display: late ? "晚子时" : "早子时", shichen: late ? "晚子" : "子" };
  }
  return { timeIndex: branchIndex, display: `${branch}时`, shichen: branch };
}

function oneOf(args, key, values, fallback) {
  const value = args[key] ?? fallback;
  if (!values.includes(value)) fail(`--${key} 只能是 ${values.join(" 或 ")}`);
  return value;
}

function starText(star) {
  const tags = [star.brightness, star.mutagen].filter(Boolean);
  return tags.length ? `${star.name}〔${tags.join("·")}〕` : star.name;
}

function starsText(stars) {
  return stars.length ? stars.map(starText).join("、") : "—";
}

function mutagenRows(chartJson) {
  const rows = [];
  for (const palace of chartJson.palaces) {
    for (const star of [...palace.majorStars, ...palace.minorStars]) {
      if (star.mutagen) rows.push({ mutagen: star.mutagen, star: star.name, palace: palace.name, branch: palace.earthlyBranch });
    }
  }
  return MUTAGEN_NAMES.map((name) => rows.find((row) => row.mutagen === name)).filter(Boolean);
}

function palaceBranch(palaceNames, palaceName) {
  const index = palaceNames.indexOf(palaceName);
  return index >= 0 ? PALACE_BRANCHES[index] : "未知";
}

function renderMarkdown(payload) {
  const { input, config, chart, decadals, target, warnings } = payload;
  const lines = [];
  lines.push("# 紫微斗数排盘", "");
  lines.push("## 输入", "");
  lines.push(`- 日期：${input.dateType === "solar" ? "公历" : "农历"} ${input.date}${input.isLeapMonth ? "（闰月）" : ""}`);
  lines.push(`- 时间：${input.timeDisplay}（${chart.time}，${chart.timeRange}）`);
  lines.push(`- 性别：${input.gender}`);
  if (input.place) lines.push(`- 出生地：${input.place}`);
  lines.push(`- 口径：${config.algorithm === "default" ? "通行版／《紫微斗数全书》基础" : `中州派${config.astroTypeLabel}`}`);
  lines.push(`- 闰月处理：${config.fixLeap ? "前半月按上月、后半月按本月" : "不调整"}`);
  lines.push("");

  lines.push("## 基本盘", "");
  lines.push(`- 公历：${chart.solarDate}`);
  lines.push(`- 农历：${chart.lunarDate}`);
  lines.push(`- 干支：${chart.chineseDate}`);
  lines.push(`- 命宫：${chart.earthlyBranchOfSoulPalace}；身宫：${chart.earthlyBranchOfBodyPalace}`);
  lines.push(`- 命主：${chart.soul}；身主：${chart.body}`);
  lines.push(`- 五行局：${chart.fiveElementsClass}`);
  lines.push(`- 生肖／星座：${chart.zodiac}／${chart.sign}`);
  lines.push("");

  lines.push("## 生年四化", "");
  for (const row of mutagenRows(chart)) {
    const palaceName = row.palace.endsWith("宫") ? row.palace : `${row.palace}宫`;
    lines.push(`- 化${row.mutagen}：${row.star}（${palaceName}·${row.branch}）`);
  }
  lines.push("");

  lines.push("## 十二宫", "");
  lines.push("| 宫位 | 干支 | 身宫 | 十四主星 | 辅星 | 杂曜 | 本宫大限 |");
  lines.push("|---|---|---:|---|---|---|---|");
  for (const palace of chart.palaces) {
    const bodyMark = palace.isBodyPalace ? "是" : "";
    const adjectives = palace.adjectiveStars.length ? palace.adjectiveStars.map((star) => star.name).join("、") : "—";
    const range = `${palace.decadal.range[0]}–${palace.decadal.range[1]}虚岁`;
    lines.push(`| ${palace.name} | ${palace.heavenlyStem}${palace.earthlyBranch} | ${bodyMark} | ${starsText(palace.majorStars)} | ${starsText(palace.minorStars)} | ${adjectives} | ${range} |`);
  }
  lines.push("");

  lines.push("## 大限", "");
  lines.push("| 虚岁 | 公历年份 | 大限命宫 | 干支 | 大限四化（禄／权／科／忌） |");
  lines.push("|---|---|---|---|---|");
  for (const decadal of decadals) {
    lines.push(`| ${decadal.ageRange[0]}–${decadal.ageRange[1]} | ${decadal.yearRange[0]}–${decadal.yearRange[1]} | ${decadal.palaceName} | ${decadal.heavenlyStem}${decadal.earthlyBranch} | ${decadal.mutagen.join("／")} |`);
  }
  lines.push("");

  if (target) {
    lines.push(`## ${target.solarDate} 运限`, "");
    lines.push(`- 农历：${target.lunarDate}；虚岁：${target.age.nominalAge}`);
    lines.push(`- 大限：${target.decadal.heavenlyStem}${target.decadal.earthlyBranch}；大限命宫在${palaceBranch(target.decadal.palaceNames, "命宫")}`);
    lines.push(`- 流年：${target.yearly.heavenlyStem}${target.yearly.earthlyBranch}；流年命宫在${palaceBranch(target.yearly.palaceNames, "命宫")}`);
    lines.push(`- 流年四化（禄／权／科／忌）：${target.yearly.mutagen.join("／")}`);
    lines.push("");
  }

  if (warnings.length) {
    lines.push("## 警告", "");
    for (const warning of warnings) lines.push(`- ${warning}`);
    lines.push("");
  }

  lines.push("> 排盘由锁定版本的 iztro 开源引擎确定性生成。不同流派在四化、亮度、闰月和换年规则上可能不同，比较命盘时必须先统一参数。传统命理仅供文化研究与娱乐参考。", "");
  return lines.join("\n");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(usage());
    return;
  }
  if (Boolean(args.solar) === Boolean(args.lunar)) fail("必须且只能提供 --solar 或 --lunar");
  if (!args.sex || !["男", "女"].includes(args.sex)) fail("--sex 必须是男或女");
  if (args.leap && !args.lunar) fail("--leap 只能与 --lunar 一起使用");

  const warnings = [];
  const time = resolveTime(args, warnings);
  const dateType = args.solar ? "solar" : "lunar";
  const date = normalizeDate(args.solar ?? args.lunar, args.solar ? "公历日期" : "农历日期", Boolean(args.lunar));
  const targetDate = args["target-date"] ? normalizeDate(args["target-date"], "目标日期") : null;
  const format = oneOf(args, "format", ["markdown", "json"], "markdown");
  const algorithm = oneOf(args, "algorithm", ["default", "zhongzhou"], "default");
  const astroType = oneOf(args, "astro-type", ["heaven", "earth", "human"], "heaven");
  const config = {
    yearDivide: oneOf(args, "year-divide", ["normal", "exact"], "normal"),
    horoscopeDivide: oneOf(args, "horoscope-divide", ["normal", "exact"], "normal"),
    ageDivide: oneOf(args, "age-divide", ["normal", "birthday"], "normal"),
    dayDivide: oneOf(args, "day-divide", ["forward", "current"], "forward"),
    algorithm,
  };
  const fixLeap = !args["no-fix-leap"];

  const chartObject = astro.withOptions({
    type: dateType,
    dateStr: date,
    timeIndex: time.timeIndex,
    gender: args.sex,
    isLeapMonth: Boolean(args.leap),
    fixLeap,
    language: "zh-CN",
    config,
    astroType,
  });
  const chart = chartObject.toJSON();
  const target = targetDate ? chartObject.horoscope(targetDate).toJSON() : null;

  const payload = {
    schemaVersion: SCHEMA_VERSION,
    engine: { name: "iztro", version: ENGINE_VERSION, license: "MIT" },
    input: {
      dateType,
      date,
      isLeapMonth: Boolean(args.leap),
      timeIndex: time.timeIndex,
      timeDisplay: time.display,
      shichen: time.shichen,
      gender: args.sex,
      place: args.place ?? "",
      targetDate,
    },
    config: {
      ...config,
      astroType,
      astroTypeLabel: { heaven: "天盘", earth: "地盘", human: "人盘" }[astroType],
      fixLeap,
    },
    chart,
    decadals: chartObject.decadalList(),
    target,
    warnings,
  };

  if (format === "json") {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(renderMarkdown(payload));
  }
}

try {
  main();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`排盘失败：${message}\n`);
  process.exit(1);
}
