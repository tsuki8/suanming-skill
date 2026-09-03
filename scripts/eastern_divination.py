#!/usr/bin/env python3
"""Deterministic Eastern divination CLI with a Meihua Yishu first method.

This tool calculates symbols and generates bounded reflection prompts. It does
not claim supernatural accuracy, provide high-stakes advice, or make random
choices on the user's behalf.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from meihua_rules import (
        CONTROLS,
        DISCLAIMER,
        GENERATES,
        HEXAGRAM_BY_TRIGRAMS,
        HEXAGRAMS,
        HIGH_RISK_KEYWORDS,
        LINE_STAGES,
        SOURCES,
        TRIGRAM_BY_NAME,
        TRIGRAMS,
    )
except ModuleNotFoundError:  # Support import as scripts.eastern_divination.
    from .meihua_rules import (
        CONTROLS,
        DISCLAIMER,
        GENERATES,
        HEXAGRAM_BY_TRIGRAMS,
        HEXAGRAMS,
        HIGH_RISK_KEYWORDS,
        LINE_STAGES,
        SOURCES,
        TRIGRAM_BY_NAME,
        TRIGRAMS,
    )


SCHEMA_VERSION = "1.0"
INTERPRETER_VERSION = "1.0.0"
SCRIPT_DIR = Path(__file__).resolve().parent
CALENDAR_SCRIPT = SCRIPT_DIR / "meihua_calendar.mjs"
EARTHLY_BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
LINE_LABELS = ("初爻", "二爻", "三爻", "四爻", "五爻", "上爻")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="确定性生成梅花易数本卦、互卦、变卦和反思性解读。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "数字起卦：--numbers 必须提供三个三位数，依次取上卦、下卦和动爻。\n"
            "时间起卦：--datetime 使用明确的当地民用时间，不读取系统当前时间。"
        ),
    )
    parser.add_argument("--method", choices=("meihua",), default="meihua")
    parser.add_argument("--question", required=True, help="一个清晰、具体、可验证的问题")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--numbers",
        nargs=3,
        type=int,
        metavar=("UPPER", "LOWER", "MOVING"),
        help="三个 100–999 的整数，依次取上卦、下卦和动爻",
    )
    source_group.add_argument(
        "--datetime",
        dest="casting_datetime",
        metavar="YYYY-MM-DDTHH:MM",
        help="用当地民用时间按传统年月日时法起卦",
    )
    parser.add_argument(
        "--first-cast",
        action="store_true",
        help="确认这是该问题的首次起卦，不为追求满意答案而重复",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="写入文件而不是标准输出")
    return parser


def normalized_remainder(value: int, divisor: int) -> int:
    return (value - 1) % divisor + 1


def validate_question(parser: argparse.ArgumentParser, args: argparse.Namespace) -> str:
    question = " ".join(args.question.strip().split())
    if len(question) < 4:
        parser.error("--question 过短；请提供一个清晰、具体、可验证的问题")
    if len(question) > 200:
        parser.error("--question 最多 200 个字符")
    if question.count("?") + question.count("？") > 1:
        parser.error("一次只能处理一个问题；请拆分后只保留一个问号")
    if not args.first_cast:
        parser.error("必须使用 --first-cast 确认这是同一问题的首次起卦")
    for category, keywords in HIGH_RISK_KEYWORDS.items():
        matched = [keyword for keyword in keywords if keyword in question]
        if matched:
            parser.error(
                f"该问题涉及{category}（命中：{'、'.join(matched)}），不能使用占卜程序决定；"
                "请改用现实证据和合格专业意见"
            )
    if args.numbers and any(value < 100 or value > 999 for value in args.numbers):
        parser.error("--numbers 的三个数都必须是 100 到 999 的三位整数")
    return question


def parse_casting_datetime(value: str) -> datetime:
    normalized = value.strip()
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2})?",
        normalized,
    ):
        raise RuntimeError(
            "--datetime 必须使用 YYYY-MM-DDTHH:MM 格式，可选添加秒或 ±HH:MM 时区"
        )
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise RuntimeError("--datetime 不是有效公历日期或时间") from error
    if parsed.year < 1900 or parsed.year > 2100:
        raise RuntimeError("--datetime 年份目前支持 1900–2100")
    return parsed


def run_calendar(solar_date: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ("node", str(CALENDAR_SCRIPT), "--solar", solar_date),
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
        raise RuntimeError(f"历法转换输出不是有效 JSON：{error}") from error


def shichen_for_hour(hour: int) -> tuple[str, int]:
    index = 0 if hour in (23, 0) else (hour + 1) // 2
    return EARTHLY_BRANCHES[index], index + 1


def number_casting(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    upper_raw, lower_raw, moving_raw = args.numbers
    return (
        {
            "source": "numbers",
            "input": {"upperNumber": upper_raw, "lowerNumber": lower_raw, "movingNumber": moving_raw},
            "upperTotal": upper_raw,
            "lowerTotal": lower_raw,
            "movingTotal": moving_raw,
            "upperTrigramNumber": normalized_remainder(upper_raw, 8),
            "lowerTrigramNumber": normalized_remainder(lower_raw, 8),
            "movingLine": normalized_remainder(moving_raw, 6),
            "formula": "第一数以八取余为上卦；第二数以八取余为下卦；动爻数以六取余",
        },
        [],
    )


def datetime_casting(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    parsed = parse_casting_datetime(args.casting_datetime)
    calendar = run_calendar(f"{parsed.year:04d}-{parsed.month:02d}-{parsed.day:02d}")
    year_branch = calendar["yearBranch"]
    try:
        year_number = EARTHLY_BRANCHES.index(year_branch) + 1
    except ValueError as error:
        raise RuntimeError(f"历法转换返回未知年支：{year_branch}") from error
    shichen, time_number = shichen_for_hour(parsed.hour)
    upper_total = year_number + calendar["lunarMonth"] + calendar["lunarDay"]
    lower_total = upper_total + time_number
    warnings: list[str] = []
    if parsed.hour == 23:
        warnings.append("输入处于晚子时；本程序按输入的民用日期不换日，并把子时记为一数。")
    if calendar["isLeapMonth"]:
        warnings.append("输入落在农历闰月；本程序按同名月份数字起卦，不另加一月。")
    offset = parsed.utcoffset()
    timezone_note = (
        f"UTC{offset.total_seconds() / 3600:+g}"
        if offset is not None
        else "未附时区；按输入地当地民用时间解释"
    )
    return (
        {
            "source": "datetime",
            "input": {
                "datetime": parsed.isoformat(timespec="minutes"),
                "timezoneNote": timezone_note,
                "solarDate": calendar["solarDate"],
                "lunarYear": calendar["lunarYear"],
                "lunarMonth": calendar["lunarMonth"],
                "lunarDay": calendar["lunarDay"],
                "isLeapMonth": calendar["isLeapMonth"],
                "yearBranch": year_branch,
                "yearBranchNumber": year_number,
                "shichen": shichen,
                "shichenNumber": time_number,
                "calendarEngine": calendar["engine"],
            },
            "upperTotal": upper_total,
            "lowerTotal": lower_total,
            "movingTotal": lower_total,
            "upperTrigramNumber": normalized_remainder(upper_total, 8),
            "lowerTrigramNumber": normalized_remainder(lower_total, 8),
            "movingLine": normalized_remainder(lower_total, 6),
            "formula": "年支数+农历月+农历日取上卦；再加时辰数取下卦，并以同一总数取动爻",
            "calendarConvention": "农历年支、农历月日、十二时辰；闰月同数；晚子时民用日期不换日",
        },
        warnings,
    )


def trigram_from_lines(lines: Iterable[int]) -> dict[str, object]:
    wanted = tuple(lines)
    for trigram in TRIGRAMS.values():
        if trigram["lines"] == wanted:
            return trigram
    raise RuntimeError(f"无法识别三爻结构：{wanted}")


def hexagram_from_lines(lines: tuple[int, ...]) -> dict[str, object]:
    if len(lines) != 6:
        raise RuntimeError("重卦必须包含六爻")
    lower = trigram_from_lines(lines[:3])
    upper = trigram_from_lines(lines[3:])
    number = HEXAGRAM_BY_TRIGRAMS[(str(upper["name"]), str(lower["name"]))]
    return HEXAGRAMS[number]


def hexagram_payload(lines: tuple[int, ...]) -> dict[str, Any]:
    row = hexagram_from_lines(lines)
    upper = TRIGRAM_BY_NAME[str(row["upper"])]
    lower = TRIGRAM_BY_NAME[str(row["lower"])]
    return {
        "number": row["number"],
        "name": row["name"],
        "fullName": f"{upper['nature']}{lower['nature']}{row['name']}",
        "symbol": chr(0x4DC0 + int(row["number"]) - 1),
        "theme": row["theme"],
        "upperTrigram": {key: upper[key] for key in ("name", "symbol", "nature", "element", "direction", "theme")},
        "lowerTrigram": {key: lower[key] for key in ("name", "symbol", "nature", "element", "direction", "theme")},
        "linesBottomToTop": list(lines),
        "diagramTopToBottom": ["⚊" if value else "⚋" for value in reversed(lines)],
    }


def element_relation(body_element: str, use_element: str) -> dict[str, str]:
    if body_element == use_element:
        return {
            "code": "比和",
            "text": "体用同属一行，传统上视为节奏较一致；仍需检查是否共同放大同一盲点。",
        }
    if GENERATES[use_element] == body_element:
        return {
            "code": "用生体",
            "text": "用卦生体卦，传统上视为外部条件对主体有所支持；适合用小规模现实证据确认。",
        }
    if GENERATES[body_element] == use_element:
        return {
            "code": "体生用",
            "text": "体卦生用卦，传统上视为主体需要持续投入；宜核算时间、注意力和资源成本。",
        }
    if CONTROLS[use_element] == body_element:
        return {
            "code": "用克体",
            "text": "用卦克体卦，传统上视为外部事项给主体带来压力；宜降低暴露并补充事实核验。",
        }
    if CONTROLS[body_element] == use_element:
        return {
            "code": "体克用",
            "text": "体卦克用卦，传统上视为主体能够推动事项，但也需承担控制和执行成本。",
        }
    raise RuntimeError(f"无法识别五行关系：{body_element}/{use_element}")


def body_use_payload(
    primary_lines: tuple[int, ...], changed_lines: tuple[int, ...], moving_line: int
) -> dict[str, Any]:
    moving_in_lower = moving_line <= 3
    original_lower = trigram_from_lines(primary_lines[:3])
    original_upper = trigram_from_lines(primary_lines[3:])
    changed_lower = trigram_from_lines(changed_lines[:3])
    changed_upper = trigram_from_lines(changed_lines[3:])
    if moving_in_lower:
        body = original_upper
        use = original_lower
        changed_use = changed_lower
        use_position = "下卦"
    else:
        body = original_lower
        use = original_upper
        changed_use = changed_upper
        use_position = "上卦"
    return {
        "rule": "动爻所在经卦为用，不动经卦为体",
        "movingTrigramPosition": use_position,
        "body": {key: body[key] for key in ("name", "nature", "element", "theme")},
        "use": {key: use[key] for key in ("name", "nature", "element", "theme")},
        "initialRelation": element_relation(str(body["element"]), str(use["element"])),
        "changedUse": {key: changed_use[key] for key in ("name", "nature", "element", "theme")},
        "changedRelation": element_relation(str(body["element"]), str(changed_use["element"])),
    }


def classify_question(question: str) -> str:
    domains = (
        ("lost-item", ("丢", "遗失", "失物", "找回", "不见了")),
        ("relationship", ("感情", "关系", "恋爱", "姻缘", "相处", "对方")),
        ("career", ("工作", "事业", "岗位", "面试", "职业", "项目")),
        ("study", ("学习", "考试", "论文", "课程", "升学")),
    )
    for domain, keywords in domains:
        if any(keyword in question for keyword in keywords):
            return domain
    return "general"


def practical_actions(domain: str, body_use: dict[str, Any], moving_line: int) -> list[str]:
    common = [
        "先写下支持与反驳卦象解释的现实证据各一项，避免只选择符合期待的信息。",
        "把下一步缩小为可逆、可观察的小行动，并在预定时间依据结果复盘。",
    ]
    if body_use["initialRelation"]["code"] in ("用克体", "体生用"):
        common.insert(0, "先核算时间、金钱、注意力和关系成本，给自己保留退出与调整空间。")
    else:
        common.insert(0, "即使传统结构偏支持，也先用低成本试验确认，不扩大为成功保证。")
    stage_action = (
        "目前更适合补齐前提和基础信息。"
        if moving_line <= 2
        else "目前更适合管理转换过程中的边界与沟通。"
        if moving_line <= 4
        else "目前更适合检查过度投入，并规划收尾或下一阶段。"
    )
    common.append(stage_action)
    domain_actions = {
        "lost-item": [
            "回溯最后确认时间与移动路线，逐一检查容器、夹层、充电点和交接位置。",
            "联系场所失物招领；涉及证件、设备或账户时立即挂失、冻结或报警，不等待占卜结果。",
        ],
        "relationship": [
            "直接核对双方真实意愿、边界和可兑现承诺，不用卦象代替对方表态。",
        ],
        "career": [
            "用岗位或合作职责、薪酬或合作合同、资源承诺、交付标准和退出条件等可验证信息评估机会。",
        ],
        "study": [
            "用模拟成绩、反馈记录、时间投入和截止日期校准学习计划。",
        ],
        "general": ["列出至少两个现实选项、各自成本和最迟决策时间。"],
    }
    return [*common, *domain_actions[domain]]


def build_payload(question: str, casting: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    upper = TRIGRAMS[casting["upperTrigramNumber"]]
    lower = TRIGRAMS[casting["lowerTrigramNumber"]]
    primary_lines = tuple((*lower["lines"], *upper["lines"]))
    moving_line = casting["movingLine"]
    changed_list = list(primary_lines)
    changed_list[moving_line - 1] = 1 - changed_list[moving_line - 1]
    changed_lines = tuple(changed_list)
    nuclear_lines = (
        primary_lines[1],
        primary_lines[2],
        primary_lines[3],
        primary_lines[2],
        primary_lines[3],
        primary_lines[4],
    )
    primary = hexagram_payload(primary_lines)
    nuclear = hexagram_payload(nuclear_lines)
    changed = hexagram_payload(changed_lines)
    body_use = body_use_payload(primary_lines, changed_lines, moving_line)
    domain = classify_question(question)
    warnings = [
        *warnings,
        "不要对同一问题重复起卦以追求满意答案；同一对话连续 24 小时最多处理 3 个不同占卜请求。",
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "eastern-divination",
        "method": "meihua",
        "methodLabel": "梅花易数",
        "interpreter": {"name": "meihua-rule-interpreter", "version": INTERPRETER_VERSION},
        "question": question,
        "questionDomain": domain,
        "firstCastAcknowledged": True,
        "casting": casting,
        "primaryHexagram": primary,
        "nuclearHexagram": nuclear,
        "changedHexagram": changed,
        "movingLine": {
            "number": moving_line,
            "label": LINE_LABELS[moving_line - 1],
            "before": "阳" if primary_lines[moving_line - 1] else "阴",
            "after": "阳" if changed_lines[moving_line - 1] else "阴",
            "stageInterpretation": LINE_STAGES[moving_line],
        },
        "bodyUse": body_use,
        "interpretation": {
            "primaryTheme": f"本卦{primary['fullName']}：{primary['theme']}。这是当前问题的象征性起点，不是结果保证。",
            "innerOuter": (
                f"下卦{lower['name']}象征内在条件或行动基础，侧重{lower['theme']}；"
                f"上卦{upper['name']}象征外部环境或可见表现，侧重{upper['theme']}。"
            ),
            "processTheme": f"互卦{nuclear['fullName']}提示过程层可关注：{nuclear['theme']}。",
            "changeTheme": f"变卦{changed['fullName']}提示后续调整方向可关注：{changed['theme']}。",
            "bodyUseTheme": (
                f"初始体用为{body_use['initialRelation']['code']}：{body_use['initialRelation']['text']}"
                f"变后为{body_use['changedRelation']['code']}：{body_use['changedRelation']['text']}"
            ),
            "movingLineTheme": f"{LINE_LABELS[moving_line - 1]}发动：{LINE_STAGES[moving_line]}。",
            "reflectionQuestions": [
                f"“{primary['theme']}”在现实中有哪些明确证据支持，又有哪些证据反驳？",
                f"从{primary['fullName']}到{changed['fullName']}，真正可控的变化是什么？",
                "如果完全不参考占卜，只看成本、期限、合同、行为和反馈，你会如何决定下一步？",
            ],
            "practicalActions": practical_actions(domain, body_use, moving_line),
        },
        "warnings": warnings,
        "sources": list(SOURCES),
        "disclaimer": DISCLAIMER,
    }


def render_hexagram(title: str, row: dict[str, Any], moving_line: int | None = None) -> list[str]:
    lines = [f"### {title}：{row['symbol']} {row['fullName']}（第 {row['number']} 卦）", ""]
    for top_index, symbol in enumerate(row["diagramTopToBottom"]):
        line_number = 6 - top_index
        moving_mark = " ← 动爻" if moving_line == line_number else ""
        lines.append(f"    {symbol}  {LINE_LABELS[line_number - 1]}{moving_mark}")
    lines.extend(
        (
            "",
            f"- 上卦：{row['upperTrigram']['symbol']} {row['upperTrigram']['name']}（{row['upperTrigram']['nature']}／{row['upperTrigram']['element']}）",
            f"- 下卦：{row['lowerTrigram']['symbol']} {row['lowerTrigram']['name']}（{row['lowerTrigram']['nature']}／{row['lowerTrigram']['element']}）",
            f"- 主题：{row['theme']}",
            "",
        )
    )
    return lines


def render_markdown(payload: dict[str, Any]) -> str:
    casting = payload["casting"]
    lines = [
        "# 东方占卜：梅花易数规则结果",
        "",
        "## 输入与计算口径",
        "",
        f"- 问题：{payload['question']}",
        f"- 起卦来源：{'数字起卦' if casting['source'] == 'numbers' else '年月日时起卦'}",
        f"- 公式：{casting['formula']}",
        f"- 计算：上卦总数 {casting['upperTotal']} → {casting['upperTrigramNumber']}；下卦总数 {casting['lowerTotal']} → {casting['lowerTrigramNumber']}；动爻总数 {casting['movingTotal']} → {casting['movingLine']} 爻",
    ]
    if casting.get("calendarConvention"):
        lines.append(f"- 历法口径：{casting['calendarConvention']}")
    lines.append("")
    lines.extend(render_hexagram("本卦", payload["primaryHexagram"], payload["movingLine"]["number"]))
    lines.extend(render_hexagram("互卦", payload["nuclearHexagram"]))
    lines.extend(render_hexagram("变卦", payload["changedHexagram"]))

    body_use = payload["bodyUse"]
    lines.extend(("## 体用事实", ""))
    lines.append(
        f"- 体卦：{body_use['body']['name']}（{body_use['body']['nature']}／{body_use['body']['element']}）；"
        f"用卦：{body_use['use']['name']}（{body_use['use']['nature']}／{body_use['use']['element']}）"
    )
    lines.append(
        f"- 初始关系：{body_use['initialRelation']['code']}；变后用卦：{body_use['changedUse']['name']}，"
        f"关系为{body_use['changedRelation']['code']}"
    )
    lines.append("")

    interpretation = payload["interpretation"]
    lines.extend(("## 传统象征解释", ""))
    for key in (
        "primaryTheme",
        "innerOuter",
        "processTheme",
        "changeTheme",
        "bodyUseTheme",
        "movingLineTheme",
    ):
        lines.append(f"- {interpretation[key]}")
    lines.extend(("", "## 现实校准问题", ""))
    for index, question in enumerate(interpretation["reflectionQuestions"], start=1):
        lines.append(f"{index}. {question}")
    lines.extend(("", "## 可执行建议", ""))
    for action in interpretation["practicalActions"]:
        lines.append(f"- {action}")
    if payload["warnings"]:
        lines.extend(("", "## 使用提醒", ""))
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    lines.extend(("", "## 资料来源", ""))
    for source in payload["sources"]:
        lines.append(f"- [{source['title']}]({source['url']})")
    lines.extend(("", "## 使用边界", "", f"> {payload['disclaimer']}", ""))
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
    question = validate_question(parser, args)
    try:
        if args.numbers:
            casting, warnings = number_casting(args)
        else:
            casting, warnings = datetime_casting(args)
        payload = build_payload(question, casting, warnings)
        rendered = (
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            if args.format == "json"
            else render_markdown(payload)
        )
        write_output(rendered, args.output)
    except (RuntimeError, ValueError, KeyError) as error:
        sys.stderr.write(f"东方占卜失败：{error}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
