import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(HERE, "ziwei_pan.mjs");
const COMPARE_SCRIPT = join(HERE, "ziwei_time_compare.mjs");

function runJson(...args) {
  const stdout = execFileSync(process.execPath, [SCRIPT, ...args, "--format", "json"], {
    encoding: "utf8",
  });
  return JSON.parse(stdout);
}

function runCompareJson(...args) {
  const stdout = execFileSync(process.execPath, [COMPARE_SCRIPT, ...args, "--format", "json"], {
    encoding: "utf8",
  });
  return JSON.parse(stdout);
}

function palace(chart, name) {
  return chart.palaces.find((item) => item.name === name);
}

test("golden chart: public iztro documentation example", () => {
  const data = runJson(
    "--solar",
    "2000-08-16",
    "--hour",
    "03:30",
    "--sex",
    "女",
  );

  assert.equal(data.engine.name, "iztro");
  assert.equal(data.chart.lunarDate, "二〇〇〇年七月十七");
  assert.equal(data.chart.chineseDate, "庚辰 甲申 丙午 庚寅");
  assert.equal(data.chart.time, "寅时");
  assert.equal(data.chart.earthlyBranchOfSoulPalace, "午");
  assert.equal(data.chart.earthlyBranchOfBodyPalace, "戌");
  assert.equal(data.chart.fiveElementsClass, "木三局");
  assert.deepEqual(
    palace(data.chart, "命宫").majorStars.map((star) => [star.name, star.mutagen]),
    [["紫微", ""]],
  );
  assert.deepEqual(
    palace(data.chart, "夫妻").majorStars.map((star) => star.name),
    ["七杀"],
  );
  assert.deepEqual(
    palace(data.chart, "官禄").majorStars.map((star) => star.name),
    ["廉贞", "天府"],
  );
});

test("solar and lunar inputs generate the same golden chart", () => {
  const solar = runJson("--solar", "2000-08-16", "--shichen", "寅", "--sex", "女");
  const lunar = runJson("--lunar", "2000-07-17", "--shichen", "寅", "--sex", "女");
  assert.equal(lunar.chart.solarDate, solar.chart.solarDate);
  assert.equal(lunar.chart.earthlyBranchOfSoulPalace, solar.chart.earthlyBranchOfSoulPalace);
  assert.deepEqual(lunar.chart.palaces, solar.chart.palaces);
});

test("late Zi and early Zi map to distinct time indexes", () => {
  const early = runJson("--solar", "2000-08-16", "--shichen", "子", "--zi", "early", "--sex", "女");
  const late = runJson("--solar", "2000-08-16", "--shichen", "子", "--zi", "late", "--sex", "女");
  assert.equal(early.input.timeIndex, 0);
  assert.equal(late.input.timeIndex, 12);
  assert.equal(early.chart.time, "早子时");
  assert.equal(late.chart.time, "晚子时");
});

test("target date includes current decadal and yearly data", () => {
  const data = runJson(
    "--solar",
    "2000-08-16",
    "--shichen",
    "寅",
    "--sex",
    "女",
    "--target-date",
    "2025-01-01",
  );
  assert.equal(data.target.age.nominalAge, 25);
  assert.equal(`${data.target.decadal.heavenlyStem}${data.target.decadal.earthlyBranch}`, "庚辰");
  assert.equal(`${data.target.yearly.heavenlyStem}${data.target.yearly.earthlyBranch}`, "甲辰");
  assert.deepEqual(data.target.yearly.mutagen, ["廉贞", "破军", "武曲", "太阳"]);
  assert.equal(data.target.monthly.name, "流月");
  assert.equal(data.target.daily.name, "流日");
  assert.equal(data.target.hourly.name, "流时");
});

test("explicit Zhongzhou configuration is preserved", () => {
  const data = runJson(
    "--solar",
    "2000-08-16",
    "--shichen",
    "寅",
    "--sex",
    "女",
    "--algorithm",
    "zhongzhou",
    "--astro-type",
    "heaven",
  );
  assert.equal(data.config.algorithm, "zhongzhou");
  assert.equal(data.config.astroType, "heaven");
});

const configurationCases = [
  {
    label: "all defaults",
    birth: ["--solar", "2000-08-16", "--shichen", "寅", "--sex", "女"],
    args: [],
    expected: {
      algorithm: "default",
      astroType: "heaven",
      yearDivide: "normal",
      horoscopeDivide: "normal",
      ageDivide: "normal",
      dayDivide: "forward",
      fixLeap: true,
    },
  },
  {
    label: "Zhongzhou heaven chart",
    birth: ["--solar", "2000-08-16", "--shichen", "寅", "--sex", "女"],
    args: ["--algorithm", "zhongzhou", "--astro-type", "heaven"],
    expected: { algorithm: "zhongzhou", astroType: "heaven" },
    expectedChart: { earthlyBranchOfSoulPalace: "午" },
  },
  {
    label: "Zhongzhou earth chart",
    birth: ["--solar", "2000-08-16", "--shichen", "寅", "--sex", "女"],
    args: ["--algorithm", "zhongzhou", "--astro-type", "earth"],
    expected: { algorithm: "zhongzhou", astroType: "earth" },
    expectedChart: { earthlyBranchOfSoulPalace: "戌", fiveElementsClass: "土五局" },
  },
  {
    label: "Zhongzhou human chart",
    birth: ["--solar", "2000-08-16", "--shichen", "寅", "--sex", "女"],
    args: ["--algorithm", "zhongzhou", "--astro-type", "human"],
    expected: { algorithm: "zhongzhou", astroType: "human" },
    expectedChart: { earthlyBranchOfSoulPalace: "申", fiveElementsClass: "水二局" },
  },
  {
    label: "lunar-new-year boundary",
    birth: ["--solar", "2000-02-04", "--shichen", "寅", "--sex", "女"],
    args: ["--year-divide", "normal"],
    expected: { yearDivide: "normal" },
    expectedChart: { chineseDate: "己卯 丁丑 壬辰 壬寅", fiveElementsClass: "火六局" },
  },
  {
    label: "Li Chun year boundary",
    birth: ["--solar", "2000-02-04", "--shichen", "寅", "--sex", "女"],
    args: ["--year-divide", "exact"],
    expected: { yearDivide: "exact" },
    expectedChart: { chineseDate: "庚辰 己丑 壬辰 壬寅", fiveElementsClass: "土五局" },
  },
  {
    label: "solar-term horoscope boundary",
    birth: ["--solar", "2000-08-16", "--shichen", "寅", "--sex", "女"],
    args: ["--horoscope-divide", "exact"],
    expected: { horoscopeDivide: "exact" },
  },
  {
    label: "birthday age division",
    birth: ["--solar", "2000-08-16", "--shichen", "寅", "--sex", "女", "--target-date", "2025-01-01"],
    args: ["--age-divide", "birthday"],
    expected: { ageDivide: "birthday" },
  },
  {
    label: "late Zi remains on current day",
    birth: ["--solar", "2000-08-16", "--shichen", "子", "--zi", "late", "--sex", "女"],
    args: ["--day-divide", "current"],
    expected: { dayDivide: "current" },
    expectedChart: { chineseDate: "庚辰 甲申 丙午 戊子" },
  },
  {
    label: "leap-month adjustment enabled",
    birth: ["--lunar", "2001-04-20", "--leap", "--shichen", "寅", "--sex", "女"],
    args: [],
    expected: { fixLeap: true },
    expectedChart: {
      earthlyBranchOfSoulPalace: "辰",
      earthlyBranchOfBodyPalace: "申",
    },
  },
  {
    label: "leap-month adjustment disabled",
    birth: ["--lunar", "2001-04-20", "--leap", "--shichen", "寅", "--sex", "女"],
    args: ["--no-fix-leap"],
    expected: { fixLeap: false },
    expectedChart: {
      earthlyBranchOfSoulPalace: "卯",
      earthlyBranchOfBodyPalace: "未",
    },
  },
];

for (const { label, birth, args, expected, expectedChart = {} } of configurationCases) {
  test(`configuration: ${label}`, () => {
    const data = runJson(...birth, ...args);
    for (const [key, value] of Object.entries(expected)) {
      assert.equal(data.config[key], value, `${key} should be ${value}`);
    }
    for (const [key, value] of Object.entries(expectedChart)) {
      assert.equal(data.chart[key], value, `chart.${key} should be ${value}`);
    }
    assert.equal(data.chart.palaces.length, 12);
  });
}

test("missing birth time fails clearly", () => {
  const result = spawnSync(process.execPath, [SCRIPT, "--solar", "2000-08-16", "--sex", "女"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /必须提供 --hour 或 --shichen/);
});

test("birth-time comparison returns all 13 deterministic candidates", () => {
  const data = runCompareJson("--solar", "2000-08-16", "--sex", "女");
  assert.equal(data.candidates.length, 13);
  assert.deepEqual(data.candidates.map((item) => item.index), [...Array(13).keys()]);
  assert.equal(data.candidates[0].label, "早子");
  assert.equal(data.candidates[12].label, "晚子");
  assert.equal(data.candidates[0].time, "早子时");
  assert.equal(data.candidates[12].time, "晚子时");

  const yin = data.candidates[2];
  assert.equal(yin.label, "寅");
  assert.equal(yin.soulPalaceBranch, "午");
  assert.equal(yin.bodyPalaceBranch, "戌");
  assert.deepEqual(yin.keyPalaces["命"].majorStars.map((star) => star.name), ["紫微"]);
  assert.equal(yin.decadals.length > 0, true);
  assert.deepEqual(yin.focusStars.map((star) => star.name), ["文昌", "文曲", "红鸾", "天喜"]);
});

test("birth-time comparison preserves target-date calibration data", () => {
  const data = runCompareJson(
    "--solar",
    "2000-08-16",
    "--sex",
    "女",
    "--target-date",
    "2025-01-01",
  );
  assert.equal(data.input.targetDate, "2025-1-1");
  assert.equal(data.candidates[2].target.nominalAge, 25);
  assert.deepEqual(data.candidates[2].target.yearly.mutagen, ["廉贞", "破军", "武曲", "太阳"]);
});
