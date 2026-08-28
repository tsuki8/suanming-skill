#!/usr/bin/env node

/** Return the lunar month/day and lunar-year branch needed by time casting. */

import { astro } from "iztro";

const ENGINE_VERSION = "2.6.0";

function fail(message) {
  process.stderr.write(`历法转换失败：${message}\n`);
  process.exit(2);
}

function normalizeSolarDate(value) {
  const match = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(value ?? "");
  if (!match) fail("--solar 必须使用 YYYY-MM-DD 格式");
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1900 || year > 2100) fail("年份目前支持 1900–2100");
  const probe = new Date(Date.UTC(year, month - 1, day));
  if (
    probe.getUTCFullYear() !== year ||
    probe.getUTCMonth() !== month - 1 ||
    probe.getUTCDate() !== day
  ) {
    fail("--solar 不是有效公历日期");
  }
  return `${year}-${month}-${day}`;
}

const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== "--solar") {
  fail("用法：node scripts/meihua_calendar.mjs --solar YYYY-MM-DD");
}

try {
  const solarDate = normalizeSolarDate(args[1]);
  // Gender and birth time do not affect this helper's lunar date/year branch.
  const chart = astro.bySolar(solarDate, 0, "男").toJSON();
  const lunar = chart.rawDates.lunarDate;
  const yearly = chart.rawDates.chineseDate.yearly;
  process.stdout.write(
    `${JSON.stringify(
      {
        engine: { name: "iztro", version: ENGINE_VERSION },
        solarDate,
        lunarYear: lunar.lunarYear,
        lunarMonth: lunar.lunarMonth,
        lunarDay: lunar.lunarDay,
        isLeapMonth: lunar.isLeap,
        yearStem: yearly[0],
        yearBranch: yearly[1],
      },
      null,
      2,
    )}\n`,
  );
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}
