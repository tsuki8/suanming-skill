#!/usr/bin/env python3
"""Automate deterministic Zi Wei chart facts and topic input packets.

This Python entry point never calculates stars itself. It delegates all chart
math to the pinned Node/iztro scripts, then gathers the exact facts needed for
career, wealth, health, relationship, overall, and study analysis. When birth
time is omitted, it automatically switches to the 13-candidate comparison.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PAN_SCRIPT = SCRIPT_DIR / "ziwei_pan.mjs"
COMPARE_SCRIPT = SCRIPT_DIR / "ziwei_time_compare.mjs"
MUTAGEN_ORDER = ("禄", "权", "科", "忌")
FOCUS_STARS = ("文昌", "文曲", "红鸾", "天喜")
PALACE_ALIASES = {"交友": ("交友", "仆役")}
TOPICS: dict[str, dict[str, Any]] = {
    "career": {
        "label": "事业",
        "palaces": ("官禄", "财帛", "命", "迁移", "交友", "福德"),
        "focus_stars": (),
        "include_body_palace": True,
    },
    "wealth": {
        "label": "财运",
        "palaces": ("财帛", "官禄", "命", "迁移", "田宅", "福德"),
        "focus_stars": (),
        "include_body_palace": False,
    },
    "health": {
        "label": "健康（身体／心理）",
        "palaces": ("疾厄", "福德", "命"),
        "focus_stars": (),
        "include_body_palace": True,
    },
    "relationship": {
        "label": "感情",
        "palaces": ("夫妻", "福德", "迁移", "命", "官禄", "交友", "田宅"),
        "focus_stars": ("红鸾", "天喜"),
        "include_body_palace": False,
    },
    "overall": {
        "label": "整体",
        "palaces": ("命", "迁移", "财帛", "官禄", "夫妻", "福德"),
        "focus_stars": FOCUS_STARS,
        "include_body_palace": True,
    },
    "study": {
        "label": "学业",
        "palaces": ("命", "福德", "官禄", "迁移", "父母"),
        "focus_stars": ("文昌", "文曲"),
        "include_body_palace": False,
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="自动排盘并整理六大主题所需的确定性紫微斗数事实。",
    )
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("--solar", metavar="YYYY-MM-DD", help="公历生日")
    date_group.add_argument("--lunar", metavar="YYYY-MM-DD", help="农历生日")
    parser.add_argument("--leap", action="store_true", help="农历日期为闰月")

    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument("--hour", metavar="HH:MM", help="24 小时制出生时间")
    time_group.add_argument("--shichen", metavar="地支", help="子、丑、寅等出生时辰")
    parser.add_argument("--zi", choices=("early", "late"), help="子时指定早子或晚子")

    parser.add_argument("--sex", required=True, choices=("男", "女"), help="性别")
    parser.add_argument("--place", help="出生城市，仅展示并用于边界提醒")
    parser.add_argument("--target-date", metavar="YYYY-MM-DD", help="附加目标日期运限")
    parser.add_argument("--algorithm", choices=("default", "zhongzhou"), default="default")
    parser.add_argument("--astro-type", choices=("heaven", "earth", "human"), default="heaven")
    parser.add_argument("--year-divide", choices=("normal", "exact"), default="normal")
    parser.add_argument("--horoscope-divide", choices=("normal", "exact"), default="normal")
    parser.add_argument("--age-divide", choices=("normal", "birthday"), default="normal")
    parser.add_argument("--day-divide", choices=("forward", "current"), default="forward")
    parser.add_argument("--no-fix-leap", action="store_true")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="把结果写入文件，而不是标准输出")
    return parser


def node_arguments(args: argparse.Namespace, *, include_time: bool) -> list[str]:
    result: list[str] = []
    for key in (
        "solar",
        "lunar",
        "sex",
        "place",
        "target_date",
        "algorithm",
        "astro_type",
        "year_divide",
        "horoscope_divide",
        "age_divide",
        "day_divide",
    ):
        value = getattr(args, key)
        if value is not None:
            result.extend((f"--{key.replace('_', '-')}", str(value)))
    if args.leap:
        result.append("--leap")
    if args.no_fix_leap:
        result.append("--no-fix-leap")
    if include_time:
        if args.hour:
            result.extend(("--hour", args.hour))
        elif args.shichen:
            result.extend(("--shichen", args.shichen))
        if args.zi:
            result.extend(("--zi", args.zi))
    result.extend(("--format", "json"))
    return result


def run_node(script: Path, arguments: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ("node", str(script), *arguments),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("未找到 node；请先安装 Node.js 18 或更高版本") from error
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "未知错误"
        raise RuntimeError(message)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Node 排盘输出不是有效 JSON：{error}") from error


def canonical_palace_name(name: str) -> str:
    return name.removesuffix("宫")


def all_stars(palace: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *palace.get("majorStars", []),
        *palace.get("minorStars", []),
        *palace.get("adjectiveStars", []),
    ]


def compact_star(star: dict[str, Any]) -> dict[str, str]:
    return {
        "name": star["name"],
        "brightness": star.get("brightness", ""),
        "mutagen": star.get("mutagen", ""),
    }


def compact_palace(palace: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": palace["name"],
        "heavenlyStem": palace["heavenlyStem"],
        "earthlyBranch": palace["earthlyBranch"],
        "isBodyPalace": palace["isBodyPalace"],
        "majorStars": [compact_star(star) for star in palace.get("majorStars", [])],
        "minorStars": [compact_star(star) for star in palace.get("minorStars", [])],
        "adjectiveStars": [star["name"] for star in palace.get("adjectiveStars", [])],
        "decadalAgeRange": palace["decadal"]["range"],
    }


def palace_by_name(chart: dict[str, Any], name: str) -> dict[str, Any]:
    accepted_names = PALACE_ALIASES.get(name, (name,))
    for palace in chart["palaces"]:
        if canonical_palace_name(palace["name"]) in accepted_names:
            return palace
    raise RuntimeError(f"排盘结果缺少宫位：{name}")


def focus_star_positions(chart: dict[str, Any]) -> list[dict[str, str]]:
    positions: list[dict[str, str]] = []
    for palace in chart["palaces"]:
        for star in all_stars(palace):
            if star["name"] in FOCUS_STARS:
                positions.append(
                    {
                        "name": star["name"],
                        "palace": palace["name"],
                        "earthlyBranch": palace["earthlyBranch"],
                        "brightness": star.get("brightness", ""),
                        "mutagen": star.get("mutagen", ""),
                    }
                )
    positions.sort(key=lambda item: FOCUS_STARS.index(item["name"]))
    return positions


def birth_mutagens(chart: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for palace in chart["palaces"]:
        for star in all_stars(palace):
            if star.get("mutagen"):
                rows.append(
                    {
                        "mutagen": star["mutagen"],
                        "star": star["name"],
                        "palace": palace["name"],
                        "earthlyBranch": palace["earthlyBranch"],
                    }
                )
    rows.sort(key=lambda item: MUTAGEN_ORDER.index(item["mutagen"]))
    return rows


def compact_target(target: dict[str, Any] | None) -> dict[str, Any] | None:
    if target is None:
        return None
    return {
        "solarDate": target["solarDate"],
        "lunarDate": target["lunarDate"],
        "nominalAge": target["age"]["nominalAge"],
        "decadal": {
            "heavenlyStem": target["decadal"]["heavenlyStem"],
            "earthlyBranch": target["decadal"]["earthlyBranch"],
            "palaceNames": target["decadal"]["palaceNames"],
            "mutagen": target["decadal"]["mutagen"],
        },
        "yearly": {
            "heavenlyStem": target["yearly"]["heavenlyStem"],
            "earthlyBranch": target["yearly"]["earthlyBranch"],
            "palaceNames": target["yearly"]["palaceNames"],
            "mutagen": target["yearly"]["mutagen"],
        },
    }


def topic_packets(
    chart: dict[str, Any],
    focus: list[dict[str, str]],
    body_palace: dict[str, Any],
) -> dict[str, Any]:
    packets: dict[str, Any] = {}
    for key, topic in TOPICS.items():
        selected_focus = [
            row for row in focus if row["name"] in topic["focus_stars"]
        ]
        packets[key] = {
            "label": topic["label"],
            "palaces": [
                compact_palace(palace_by_name(chart, name)) for name in topic["palaces"]
            ],
            "bodyPalace": (
                compact_palace(body_palace)
                if topic["include_body_palace"]
                else None
            ),
            "focusStars": selected_focus,
        }
    return packets


def enrich_chart(raw: dict[str, Any]) -> dict[str, Any]:
    chart = raw["chart"]
    focus = focus_star_positions(chart)
    body_palace = next(palace for palace in chart["palaces"] if palace["isBodyPalace"])
    return {
        "schemaVersion": "1.0",
        "mode": "chart-facts",
        "engine": raw["engine"],
        "input": raw["input"],
        "config": raw["config"],
        "chartSummary": {
            "solarDate": chart["solarDate"],
            "lunarDate": chart["lunarDate"],
            "chineseDate": chart["chineseDate"],
            "time": chart["time"],
            "timeRange": chart["timeRange"],
            "soulPalaceBranch": chart["earthlyBranchOfSoulPalace"],
            "bodyPalaceBranch": chart["earthlyBranchOfBodyPalace"],
            "bodyPalaceName": body_palace["name"],
            "soul": chart["soul"],
            "body": chart["body"],
            "fiveElementsClass": chart["fiveElementsClass"],
        },
        "bodyPalace": compact_palace(body_palace),
        "birthMutagens": birth_mutagens(chart),
        "focusStars": focus,
        "topics": topic_packets(chart, focus, body_palace),
        "decadals": raw["decadals"],
        "target": compact_target(raw["target"]),
        "warnings": raw["warnings"],
    }


def star_text(star: dict[str, Any]) -> str:
    tags = [star.get("brightness", ""), star.get("mutagen", "")]
    shown_tags = [tag for tag in tags if tag]
    return f"{star['name']}〔{'·'.join(shown_tags)}〕" if shown_tags else star["name"]


def palace_text(palace: dict[str, Any]) -> str:
    stars = palace["majorStars"]
    star_names = "、".join(star_text(star) for star in stars) if stars else "空宫"
    body_mark = "；身宫" if palace["isBodyPalace"] else ""
    return f"{palace['name']}（{palace['earthlyBranch']}：{star_names}{body_mark}）"


def render_chart_markdown(payload: dict[str, Any]) -> str:
    summary = payload["chartSummary"]
    config = payload["config"]
    input_data = payload["input"]
    lines = [
        "# 紫微斗数自动计算事实包",
        "",
        f"- 日期：{summary['solarDate']}（{summary['lunarDate']}）",
        f"- 时间：{summary['time']}（{summary['timeRange']}）",
        f"- 性别：{input_data['gender']}",
        f"- 口径：{config['algorithm']}／{config['astroTypeLabel']}",
        f"- 命宫／身宫：{summary['soulPalaceBranch']}／{summary['bodyPalaceBranch']}（{summary['bodyPalaceName']}）",
        f"- 命主／身主／五行局：{summary['soul']}／{summary['body']}／{summary['fiveElementsClass']}",
        "",
        "## 生年四化",
        "",
    ]
    for row in payload["birthMutagens"]:
        lines.append(
            f"- 化{row['mutagen']}：{row['star']}（{row['palace']}·{row['earthlyBranch']}）"
        )
    lines.extend(("", "## 重点星曜", ""))
    for row in payload["focusStars"]:
        tags = [row["brightness"], row["mutagen"]]
        suffix = f"〔{'·'.join(tag for tag in tags if tag)}〕" if any(tags) else ""
        lines.append(f"- {row['name']}{suffix}：{row['palace']}·{row['earthlyBranch']}")

    lines.extend(("", "## 六大主题事实输入", ""))
    for topic in payload["topics"].values():
        lines.append(f"### {topic['label']}")
        lines.append("")
        lines.append("- 宫位：" + "；".join(palace_text(item) for item in topic["palaces"]))
        if topic["bodyPalace"]:
            lines.append("- 身宫所在宫位：" + palace_text(topic["bodyPalace"]))
        if topic["focusStars"]:
            lines.append(
                "- 重点星曜："
                + "、".join(
                    f"{row['name']}@{row['palace']}·{row['earthlyBranch']}"
                    for row in topic["focusStars"]
                )
            )
        lines.append("")

    if payload["target"]:
        target = payload["target"]
        lines.extend(
            (
                "## 目标日期运限",
                "",
                f"- 日期／虚岁：{target['solarDate']}／{target['nominalAge']}",
                f"- 大限：{target['decadal']['heavenlyStem']}{target['decadal']['earthlyBranch']}；四化 {'／'.join(target['decadal']['mutagen'])}",
                f"- 流年：{target['yearly']['heavenlyStem']}{target['yearly']['earthlyBranch']}；四化 {'／'.join(target['yearly']['mutagen'])}",
                "",
            )
        )
    if payload["warnings"]:
        lines.extend(("## 警告", ""))
        lines.extend(f"- {warning}" for warning in payload["warnings"])
        lines.append("")
    lines.append(
        "> 本文件只自动整理排盘事实，不自动生成吉凶断语。传统命理仅供文化研究与娱乐参考。"
    )
    lines.append("")
    return "\n".join(lines)


def render_time_comparison(payload: dict[str, Any]) -> str:
    lines = [
        "# 紫微斗数 13 时辰自动比较",
        "",
        f"- 日期：{payload['input']['date']}",
        f"- 性别：{payload['input']['gender']}",
        "",
        "| 索引 | 候选 | 时间范围 | 命／身宫 | 五行局 | 命宫主星 |",
        "|---:|---|---|---|---|---|",
    ]
    for candidate in payload["candidates"]:
        major_stars = candidate["keyPalaces"]["命"]["majorStars"]
        star_names = "、".join(star_text(star) for star in major_stars) if major_stars else "空宫"
        lines.append(
            f"| {candidate['index']} | {candidate['label']} | {candidate['timeRange']} | "
            f"{candidate['soulPalaceBranch']}／{candidate['bodyPalaceBranch']} | "
            f"{candidate['fiveElementsClass']} | {star_names} |"
        )
    lines.extend(
        (
            "",
            "> 未提供出生时间，因此自动进入 13 候选模式；本表不会自动判定唯一时辰。",
            "",
        )
    )
    return "\n".join(lines)


def write_output(text: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(text)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.zi and args.shichen != "子":
        parser.error("--zi 只能与 --shichen 子 一起使用")
    if args.leap and not args.lunar:
        parser.error("--leap 只能与 --lunar 一起使用")

    try:
        if args.hour or args.shichen:
            raw = run_node(PAN_SCRIPT, node_arguments(args, include_time=True))
            payload = enrich_chart(raw)
            rendered = (
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                if args.format == "json"
                else render_chart_markdown(payload)
            )
        else:
            raw = run_node(COMPARE_SCRIPT, node_arguments(args, include_time=False))
            payload = {"mode": "time-comparison", **raw}
            rendered = (
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                if args.format == "json"
                else render_time_comparison(payload)
            )
    except RuntimeError as error:
        sys.stderr.write(f"自动计算失败：{error}\n")
        return 2

    write_output(rendered, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
