#!/usr/bin/env python3
"""Deterministic Zi Wei Dou Shu topic interpretation and compatibility CLI.

The chart itself always comes from the pinned Node/iztro engine. This module
applies a fixed, inspectable vocabulary to career, wealth, relationship, and
two-person relationship compatibility. It deliberately avoids event promises,
medical claims, investment instructions, and compatibility scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    from ziwei_auto import PAN_SCRIPT, run_node
    from ziwei_rules import (
        BRANCH_CLASHES,
        BRANCH_SIX_HARMONY,
        BRANCH_TRINES,
        BRIGHTNESS_NOTES,
        CHALLENGE_STARS,
        COMPATIBILITY_DISCLAIMER,
        DISCLAIMER,
        FLOWER_STARS,
        MUTAGEN_EFFECTS,
        MUTAGEN_ORDER,
        PALACE_ROLES,
        STAR_RULES,
        SUPPORT_STARS,
        TAG_LABELS,
        TOPIC_ACTIONS,
        TOPIC_ALIASES,
        TOPIC_CORE_PALACE,
        TOPIC_LABELS,
        TOPIC_PALACES,
    )
except ModuleNotFoundError:  # Support import as scripts.ziwei_interpret in tests/tools.
    from .ziwei_auto import PAN_SCRIPT, run_node
    from .ziwei_rules import (
        BRANCH_CLASHES,
        BRANCH_SIX_HARMONY,
        BRANCH_TRINES,
        BRIGHTNESS_NOTES,
        CHALLENGE_STARS,
        COMPATIBILITY_DISCLAIMER,
        DISCLAIMER,
        FLOWER_STARS,
        MUTAGEN_EFFECTS,
        MUTAGEN_ORDER,
        PALACE_ROLES,
        STAR_RULES,
        SUPPORT_STARS,
        TAG_LABELS,
        TOPIC_ACTIONS,
        TOPIC_ALIASES,
        TOPIC_CORE_PALACE,
        TOPIC_LABELS,
        TOPIC_PALACES,
    )


SCHEMA_VERSION = "1.0"
INTERPRETER_VERSION = "1.0.0"
PALACE_ALIASES = {"仆役": "交友"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按固定规则解读事业、财帛、姻缘，或对两张命盘进行姻缘合盘。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "主题可用中文或英文：事业/career、财帛/wealth、姻缘/relationship、合盘/compatibility。\n"
            "合盘时，第一人沿用普通出生参数，第二人使用 --partner-* 参数，并须提供 --partner-consent。"
        ),
    )
    parser.add_argument("--topic", required=True, help="事业、财帛、姻缘或合盘")

    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("--solar", metavar="YYYY-MM-DD", help="第一人公历生日")
    date_group.add_argument("--lunar", metavar="YYYY-MM-DD", help="第一人农历生日")
    parser.add_argument("--leap", action="store_true", help="第一人的农历生日为闰月")

    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument("--hour", metavar="HH:MM", help="第一人 24 小时制出生时间")
    time_group.add_argument("--shichen", metavar="地支", help="第一人出生时辰")
    parser.add_argument("--zi", choices=("early", "late"), help="第一人子时指定早子或晚子")
    parser.add_argument("--sex", required=True, choices=("男", "女"), help="第一人性别")
    parser.add_argument("--place", help="第一人出生城市，仅展示并用于时辰边界提醒")
    parser.add_argument("--label", default="当事人", help="第一人的显示标签，不必填写真实姓名")

    partner_date_group = parser.add_mutually_exclusive_group()
    partner_date_group.add_argument("--partner-solar", metavar="YYYY-MM-DD", help="第二人公历生日")
    partner_date_group.add_argument("--partner-lunar", metavar="YYYY-MM-DD", help="第二人农历生日")
    parser.add_argument("--partner-leap", action="store_true", help="第二人的农历生日为闰月")

    partner_time_group = parser.add_mutually_exclusive_group()
    partner_time_group.add_argument("--partner-hour", metavar="HH:MM", help="第二人出生时间")
    partner_time_group.add_argument("--partner-shichen", metavar="地支", help="第二人出生时辰")
    parser.add_argument(
        "--partner-zi",
        choices=("early", "late"),
        help="第二人子时指定早子或晚子",
    )
    parser.add_argument("--partner-sex", choices=("男", "女"), help="第二人性别")
    parser.add_argument("--partner-place", help="第二人出生城市")
    parser.add_argument("--partner-label", default="对方", help="第二人的显示标签")
    parser.add_argument(
        "--partner-consent",
        action="store_true",
        help="确认已获第二人许可使用其出生资料",
    )

    parser.add_argument("--target-date", metavar="YYYY-MM-DD", help="附加目标日期的大限与流年观察")
    parser.add_argument("--algorithm", choices=("default", "zhongzhou"), default="default")
    parser.add_argument("--astro-type", choices=("heaven", "earth", "human"), default="heaven")
    parser.add_argument("--year-divide", choices=("normal", "exact"), default="normal")
    parser.add_argument("--horoscope-divide", choices=("normal", "exact"), default="normal")
    parser.add_argument("--age-divide", choices=("normal", "birthday"), default="normal")
    parser.add_argument("--day-divide", choices=("forward", "current"), default="forward")
    parser.add_argument("--no-fix-leap", action="store_true")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="写入文件而不是标准输出")
    return parser


def validate_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> str:
    topic = TOPIC_ALIASES.get(args.topic.strip().lower())
    if topic is None:
        parser.error("--topic 必须是事业/career、财帛/wealth、姻缘/relationship 或合盘/compatibility")

    if args.leap and not args.lunar:
        parser.error("--leap 只能与 --lunar 一起使用")
    if args.zi and args.shichen != "子":
        parser.error("--zi 只能与 --shichen 子 一起使用")

    partner_values = (
        args.partner_solar,
        args.partner_lunar,
        args.partner_hour,
        args.partner_shichen,
        args.partner_sex,
        args.partner_place,
        args.partner_zi,
    )
    has_partner_data = any(value is not None for value in partner_values) or args.partner_leap

    if topic == "compatibility":
        if not (args.partner_solar or args.partner_lunar):
            parser.error("合盘必须提供 --partner-solar 或 --partner-lunar")
        if not (args.partner_hour or args.partner_shichen):
            parser.error("合盘必须提供 --partner-hour 或 --partner-shichen")
        if not args.partner_sex:
            parser.error("合盘必须提供 --partner-sex")
        if not args.partner_consent:
            parser.error("合盘必须使用 --partner-consent 确认已获对方许可")
        if args.partner_leap and not args.partner_lunar:
            parser.error("--partner-leap 只能与 --partner-lunar 一起使用")
        if args.partner_zi and args.partner_shichen != "子":
            parser.error("--partner-zi 只能与 --partner-shichen 子 一起使用")
    elif has_partner_data or args.partner_consent:
        parser.error("--partner-* 参数只用于 --topic 合盘/compatibility")

    return topic


def node_arguments(args: argparse.Namespace, *, partner: bool) -> list[str]:
    prefix = "partner_" if partner else ""
    result: list[str] = []
    solar = getattr(args, f"{prefix}solar")
    lunar = getattr(args, f"{prefix}lunar")
    hour = getattr(args, f"{prefix}hour")
    shichen = getattr(args, f"{prefix}shichen")
    zi = getattr(args, f"{prefix}zi")
    sex = getattr(args, f"{prefix}sex")
    place = getattr(args, f"{prefix}place")
    leap = getattr(args, f"{prefix}leap")

    if solar:
        result.extend(("--solar", solar))
    else:
        result.extend(("--lunar", lunar))
    if leap:
        result.append("--leap")
    if hour:
        result.extend(("--hour", hour))
    else:
        result.extend(("--shichen", shichen))
    if zi:
        result.extend(("--zi", zi))
    result.extend(("--sex", sex))
    if place:
        result.extend(("--place", place))
    if args.target_date:
        result.extend(("--target-date", args.target_date))
    for option in (
        "algorithm",
        "astro_type",
        "year_divide",
        "horoscope_divide",
        "age_divide",
        "day_divide",
    ):
        result.extend((f"--{option.replace('_', '-')}", getattr(args, option)))
    if args.no_fix_leap:
        result.append("--no-fix-leap")
    result.extend(("--format", "json"))
    return result


def canonical_palace_name(name: str) -> str:
    canonical = name.removesuffix("宫")
    return PALACE_ALIASES.get(canonical, canonical)


def palace_display(name: str) -> str:
    canonical = canonical_palace_name(name)
    return "命宫" if canonical == "命" else f"{canonical}宫"


def all_stars(palace: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *palace.get("majorStars", []),
        *palace.get("minorStars", []),
        *palace.get("adjectiveStars", []),
    ]


def find_palace(chart: dict[str, Any], name: str) -> dict[str, Any]:
    wanted = canonical_palace_name(name)
    for palace in chart["palaces"]:
        if canonical_palace_name(palace["name"]) == wanted:
            return palace
    raise RuntimeError(f"排盘结果缺少宫位：{name}")


def locate_star(chart: dict[str, Any], star_name: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for palace in chart["palaces"]:
        for star in all_stars(palace):
            if star["name"] == star_name:
                return palace, star
    return None


def effective_major_stars(chart: dict[str, Any], palace: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    stars = palace.get("majorStars", [])
    if stars:
        return stars, palace, False
    opposite = chart["palaces"][(palace["index"] + 6) % 12]
    return opposite.get("majorStars", []), opposite, True


def star_text(star: dict[str, Any]) -> str:
    tags = [star.get("brightness", ""), f"化{star['mutagen']}" if star.get("mutagen") else ""]
    shown = [tag for tag in tags if tag]
    return f"{star['name']}〔{'·'.join(shown)}〕" if shown else star["name"]


def palace_fact(chart: dict[str, Any], palace: dict[str, Any]) -> str:
    stars, source, borrowed = effective_major_stars(chart, palace)
    star_names = "、".join(star_text(star) for star in stars) if stars else "无十四主星"
    minor_names = "、".join(star["name"] for star in palace.get("minorStars", [])) or "无主要辅星"
    if borrowed:
        return (
            f"{palace_display(palace['name'])}在{palace['earthlyBranch']}为空宫，借看对宫"
            f"{palace_display(source['name'])}的{star_names}；本宫辅星为{minor_names}"
        )
    return f"{palace_display(palace['name'])}在{palace['earthlyBranch']}，主星{star_names}；辅星{minor_names}"


def rule_for_star(star_name: str, topic: str) -> str:
    rule = STAR_RULES.get(star_name)
    if not rule:
        return f"{star_name}只作为结构辅助信息，不单独下结论"
    return str(rule[topic])


def brightness_summary(stars: Iterable[dict[str, Any]]) -> str:
    notes: list[str] = []
    for star in stars:
        note = BRIGHTNESS_NOTES.get(star.get("brightness", ""))
        if note and note not in notes:
            notes.append(note)
    return "；".join(notes)


def make_finding(
    title: str,
    *,
    fact: str = "",
    interpretation: str = "",
    practical_note: str = "",
    evidence: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "title": title,
        "fact": fact,
        "traditionalInterpretation": interpretation,
        "practicalNote": practical_note,
        "evidence": list(evidence),
    }


def core_finding(chart: dict[str, Any], topic: str, *, title_prefix: str = "") -> dict[str, Any]:
    core_name = TOPIC_CORE_PALACE[topic]
    palace = find_palace(chart, core_name)
    stars, source, borrowed = effective_major_stars(chart, palace)
    readings = "；".join(rule_for_star(star["name"], topic) for star in stars)
    brightness = brightness_summary(stars)
    if brightness:
        readings = f"{readings}。亮度修正：{brightness}"
    if borrowed:
        readings += "。空宫借星只提供骨架，本宫辅曜与三方四正仍需共同修正"
    return make_finding(
        f"{title_prefix}{palace_display(core_name)}主轴",
        fact=palace_fact(chart, palace),
        interpretation=readings,
        evidence=(
            f"核心宫位：{palace_display(core_name)}·{palace['earthlyBranch']}",
            f"取星来源：{palace_display(source['name'])}·{source['earthlyBranch']}",
        ),
    )


def context_findings(chart: dict[str, Any], topic: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    core_name = TOPIC_CORE_PALACE[topic]
    for palace_name in TOPIC_PALACES[topic]:
        if palace_name == core_name:
            continue
        palace = find_palace(chart, palace_name)
        stars, source, borrowed = effective_major_stars(chart, palace)
        readings = "；".join(rule_for_star(star["name"], topic) for star in stars)
        if not readings:
            readings = "本宫与对宫均无十四主星，需把辅曜和现实经历作为主要校准"
        role = PALACE_ROLES[topic][palace_name]
        borrowed_note = f"，借看{palace_display(source['name'])}" if borrowed else ""
        findings.append(
            make_finding(
                f"{palace_display(palace_name)}：{role}",
                fact=palace_fact(chart, palace),
                interpretation=f"在“{role}”上，传统上可观察为：{readings}{borrowed_note}。",
                evidence=(f"{palace_display(palace_name)}·{palace['earthlyBranch']}",),
            )
        )
    if topic == "career":
        body_palace = next(palace for palace in chart["palaces"] if palace["isBodyPalace"])
        findings.append(
            make_finding(
                "身宫的行动落点",
                fact=f"身宫落在{palace_display(body_palace['name'])}·{body_palace['earthlyBranch']}。",
                interpretation=(
                    f"传统上把身宫视为后天投入较集中的位置；这里提示实际行动会更多通过"
                    f"{PALACE_ROLES['career'].get(canonical_palace_name(body_palace['name']), '该宫主题')}展开。"
                ),
                evidence=(f"身宫：{palace_display(body_palace['name'])}·{body_palace['earthlyBranch']}",),
            )
        )
    return findings


def collect_named_stars(chart: dict[str, Any], topic: str, names: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    wanted_palaces = set(TOPIC_PALACES[topic])
    rows: list[tuple[str, dict[str, Any]]] = []
    for palace in chart["palaces"]:
        if canonical_palace_name(palace["name"]) not in wanted_palaces:
            continue
        for star in all_stars(palace):
            if star["name"] in names:
                rows.append((star["name"], palace))
    return rows


def auxiliary_findings(chart: dict[str, Any], topic: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for title, vocabulary, interpretation_prefix in (
        ("支持与放大条件", SUPPORT_STARS, "这些信号可作为支持条件，但仍需现实资源配合："),
        ("摩擦与减弱条件", CHALLENGE_STARS, "这些信号提示需要提前管理的成本，不等于必然受挫："),
    ):
        rows = collect_named_stars(chart, topic, vocabulary)
        if not rows:
            continue
        facts = "、".join(f"{name}@{palace_display(palace['name'])}" for name, palace in rows)
        readings = "；".join(f"{name}偏向{vocabulary[name]}" for name, _ in rows)
        findings.append(
            make_finding(
                title,
                fact=f"主题相关宫位见{facts}。",
                interpretation=interpretation_prefix + readings + "。",
                evidence=(facts,),
            )
        )
    if topic == "relationship":
        rows = collect_named_stars(chart, topic, FLOWER_STARS)
        if rows:
            facts = "、".join(f"{name}@{palace_display(palace['name'])}" for name, palace in rows)
            readings = "；".join(f"{name}偏向{FLOWER_STARS[name]}" for name, _ in rows)
            findings.append(
                make_finding(
                    "红鸾天喜等关系信号",
                    fact=f"关系相关宫位见{facts}。",
                    interpretation=f"{readings}；它们只能提高关系主题的可见度，不能单独证明恋爱、婚期或所谓正缘。",
                    evidence=(facts,),
                )
            )
    return findings


def birth_mutagen_rows(chart: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for palace in chart["palaces"]:
        for star in all_stars(palace):
            mutagen = star.get("mutagen", "")
            if mutagen:
                rows.append(
                    {
                        "mutagen": mutagen,
                        "star": star["name"],
                        "palace": canonical_palace_name(palace["name"]),
                        "branch": palace["earthlyBranch"],
                    }
                )
    rows.sort(key=lambda row: MUTAGEN_ORDER.index(row["mutagen"]))
    return rows


def mutagen_findings(chart: dict[str, Any], topic: str) -> list[dict[str, Any]]:
    relevant = set(TOPIC_PALACES[topic])
    findings: list[dict[str, Any]] = []
    for row in birth_mutagen_rows(chart):
        palace_name = row["palace"]
        direct = palace_name in relevant
        role = PALACE_ROLES[topic].get(palace_name, "其他人生领域")
        scope_note = "直接进入本主题必看宫位" if direct else "作为主题之外的间接背景"
        findings.append(
            make_finding(
                f"生年化{row['mutagen']}：{row['star']}",
                fact=f"{row['star']}化{row['mutagen']}，落{palace_display(palace_name)}·{row['branch']}。",
                interpretation=(
                    f"传统上表示{MUTAGEN_EFFECTS[row['mutagen']]}于“{role}”；该落点{scope_note}。"
                    + ("化忌不是灾祸，只提示需反复处理和核验的课题。" if row["mutagen"] == "忌" else "")
                ),
                evidence=(f"生年化{row['mutagen']}：{row['star']}@{palace_display(palace_name)}",),
            )
        )
    return findings


def period_overlay(chart: dict[str, Any], period: dict[str, Any], core_palace: str) -> tuple[dict[str, Any], int]:
    wanted = canonical_palace_name(core_palace)
    for index, name in enumerate(period["palaceNames"]):
        if canonical_palace_name(name) == wanted:
            return chart["palaces"][index], index
    raise RuntimeError(f"运限结果缺少{palace_display(core_palace)}")


def period_finding(chart: dict[str, Any], target: dict[str, Any], topic: str, period_key: str) -> dict[str, Any]:
    period = target[period_key]
    core_name = TOPIC_CORE_PALACE[topic]
    overlay_palace, _ = period_overlay(chart, period, core_name)
    relevant = set(TOPIC_PALACES[topic])
    overlay_name = canonical_palace_name(overlay_palace["name"])
    mutagen_facts: list[str] = []
    direct_mutagens: list[str] = []
    for mutagen, star_name in zip(MUTAGEN_ORDER, period["mutagen"], strict=True):
        located = locate_star(chart, star_name)
        if not located:
            continue
        palace, _ = located
        name = canonical_palace_name(palace["name"])
        mutagen_facts.append(f"化{mutagen}{star_name}@{palace_display(name)}")
        if name in relevant:
            direct_mutagens.append(f"化{mutagen}{star_name}进入{palace_display(name)}")
    label = "当前大限" if period_key == "decadal" else "目标流年"
    direct_note = (
        "；".join(direct_mutagens)
        if direct_mutagens
        else "四化未直接落入本主题必看宫位，主要作为间接背景"
    )
    return make_finding(
        label,
        fact=(
            f"{label}{period['heavenlyStem']}{period['earthlyBranch']}，"
            f"{palace_display(core_name)}叠到本命{palace_display(overlay_name)}·{overlay_palace['earthlyBranch']}；"
            f"四化为{'、'.join(mutagen_facts)}。"
        ),
        interpretation=(
            f"这一阶段会通过“{PALACE_ROLES[topic].get(overlay_name, palace_display(overlay_name))}”引入"
            f"{TOPIC_LABELS[topic]}主题；{direct_note}。运限只表示观察窗口，不保证具体事件发生。"
        ),
        evidence=(
            f"{label}{palace_display(core_name)}→本命{palace_display(overlay_name)}",
            *mutagen_facts,
        ),
    )


def target_findings(raw: dict[str, Any], topic: str) -> list[dict[str, Any]]:
    target = raw.get("target")
    if not target:
        return []
    chart = raw["chart"]
    return [
        period_finding(chart, target, topic, "decadal"),
        period_finding(chart, target, topic, "yearly"),
    ]


def subject_summary(raw: dict[str, Any], label: str) -> dict[str, Any]:
    chart = raw["chart"]
    body_palace = next(palace for palace in chart["palaces"] if palace["isBodyPalace"])
    return {
        "label": label,
        "solarDate": chart["solarDate"],
        "lunarDate": chart["lunarDate"],
        "time": chart["time"],
        "timeRange": chart["timeRange"],
        "gender": chart["gender"],
        "soulPalaceBranch": chart["earthlyBranchOfSoulPalace"],
        "bodyPalaceBranch": chart["earthlyBranchOfBodyPalace"],
        "bodyPalaceName": canonical_palace_name(body_palace["name"]),
        "soul": chart["soul"],
        "body": chart["body"],
        "fiveElementsClass": chart["fiveElementsClass"],
    }


def calibration_questions(chart: dict[str, Any], topic: str) -> list[str]:
    core_name = TOPIC_CORE_PALACE[topic]
    core = find_palace(chart, core_name)
    stars, _, _ = effective_major_stars(chart, core)
    star_names = "、".join(star["name"] for star in stars) or "空宫结构"
    mutagen_j = next((row for row in birth_mutagen_rows(chart) if row["mutagen"] == "忌"), None)
    j_text = (
        f"{mutagen_j['star']}化忌所在的{palace_display(mutagen_j['palace'])}"
        if mutagen_j
        else "反复消耗最明显的领域"
    )
    common = {
        "career": (
            f"过去三至五年，{star_names}所代表的工作方式是在什么环境中最容易形成可验证成果？",
            "外部机会、团队协作和个人恢复时间，哪一项最常限制你的职业选择？",
            f"{j_text}是否确实构成工作中的反复成本？若不符合，应降低该条解释权重。",
        ),
        "wealth": (
            f"过去三至五年，你的主要收入和资源管理方式是否符合{star_names}的结构描述？",
            "现金流、储蓄缓冲、长期资产和高波动投入中，现实短板究竟是哪一项？",
            f"{j_text}是否对应可核验的支出或决策摩擦？若不符合，应降低该条解释权重。",
        ),
        "relationship": (
            f"以往关系中，{star_names}所代表的需要是否被你清楚表达，而非期待对方猜到？",
            "工作节奏、社交边界、共同生活和情绪恢复中，哪一项最常成为现实摩擦？",
            f"{j_text}是否对应关系中的反复议题？若不符合，应降低该条解释权重。",
        ),
    }
    return list(common[topic])


def build_single_payload(raw: dict[str, Any], topic: str, label: str) -> dict[str, Any]:
    chart = raw["chart"]
    sections = [
        {"id": "core", "title": "核心结构", "findings": [core_finding(chart, topic)]},
        {"id": "context", "title": "必看宫位联动", "findings": context_findings(chart, topic)},
        {"id": "modifiers", "title": "支持、摩擦与关系信号", "findings": auxiliary_findings(chart, topic)},
        {"id": "mutagens", "title": "生年四化", "findings": mutagen_findings(chart, topic)},
    ]
    timing = target_findings(raw, topic)
    if timing:
        sections.append({"id": "timing", "title": "大限与流年", "findings": timing})
    sections.append(
        {
            "id": "actions",
            "title": "现实行动建议",
            "findings": [
                make_finding(f"建议 {index}", practical_note=action)
                for index, action in enumerate(TOPIC_ACTIONS[topic], start=1)
            ],
        }
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "interpretation",
        "topic": topic,
        "topicLabel": TOPIC_LABELS[topic],
        "interpreter": {"name": "ziwei-rule-interpreter", "version": INTERPRETER_VERSION},
        "engine": raw["engine"],
        "config": raw["config"],
        "subject": subject_summary(raw, label),
        "targetDate": raw["target"]["solarDate"] if raw.get("target") else None,
        "sections": sections,
        "calibrationQuestions": calibration_questions(chart, topic),
        "warnings": raw["warnings"],
        "disclaimer": DISCLAIMER,
    }


def star_tags(stars: Iterable[dict[str, Any]]) -> set[str]:
    tags: set[str] = set()
    for star in stars:
        rule = STAR_RULES.get(star["name"])
        if rule:
            tags.update(str(tag) for tag in rule["tags"])
    return tags


def subject_actual_stars(chart: dict[str, Any]) -> list[dict[str, Any]]:
    soul_palace = find_palace(chart, "命")
    soul_stars, _, _ = effective_major_stars(chart, soul_palace)
    body_palace = next(palace for palace in chart["palaces"] if palace["isBodyPalace"])
    body_stars, _, _ = effective_major_stars(chart, body_palace)
    unique: dict[str, dict[str, Any]] = {star["name"]: star for star in (*soul_stars, *body_stars)}
    return list(unique.values())


def trait_fit_finding(
    owner_chart: dict[str, Any],
    partner_chart: dict[str, Any],
    owner_label: str,
    partner_label: str,
) -> dict[str, Any]:
    spouse = find_palace(owner_chart, "夫妻")
    desired_stars, _, _ = effective_major_stars(owner_chart, spouse)
    actual_stars = subject_actual_stars(partner_chart)
    desired = star_tags(desired_stars)
    actual = star_tags(actual_stars)
    overlap = sorted(desired & actual)
    unshown = sorted(desired - actual)
    overlap_text = "、".join(TAG_LABELS[tag] for tag in overlap) if overlap else "没有直接重复的规则标签"
    gap_text = "、".join(TAG_LABELS[tag] for tag in unshown) if unshown else "未见明显缺口标签"
    return make_finding(
        f"{owner_label}的关系需要与{partner_label}的表达",
        fact=(
            f"{owner_label}夫妻宫取星为{'、'.join(star['name'] for star in desired_stars) or '空宫'}；"
            f"{partner_label}命宫/身宫取星为{'、'.join(star['name'] for star in actual_stars) or '空宫'}。"
        ),
        interpretation=(
            f"固定标签中可直接对接的是：{overlap_text}；需要靠现实沟通确认的是：{gap_text}。"
            "没有标签重合不等于不适合，标签重合也不代表双方会自然做到。"
        ),
        evidence=(
            f"{owner_label}夫妻宫标签：{'、'.join(sorted(desired)) or '无'}",
            f"{partner_label}命/身宫标签：{'、'.join(sorted(actual)) or '无'}",
        ),
    )


def branch_relation(branch_a: str, branch_b: str) -> tuple[str, str]:
    if branch_a == branch_b:
        return "同支", "传统辅助观察中偏向共享某些底层节奏，也可能放大相似盲点，仍需现实校准"
    pair = frozenset((branch_a, branch_b))
    if pair in BRANCH_SIX_HARMONY:
        return "六合", "传统辅助观察中偏向较容易形成配合，但不能代替现实磨合"
    if any(branch_a in group and branch_b in group for group in BRANCH_TRINES):
        return "三合", "传统辅助观察中偏向共享某些节奏或资源，但不能据此保证关系"
    if pair in BRANCH_CLASHES:
        return "相冲", "传统辅助观察中提示节奏、表达或空间需求可能不同，宜明确协商"
    return "无特定合冲", "这一层没有明显合冲信号，应把权重放回双方真实相处和完整命盘结构"


def branch_findings(chart_a: dict[str, Any], chart_b: dict[str, Any], label_a: str, label_b: str) -> list[dict[str, Any]]:
    axes = (
        (f"{label_a}命宫—{label_b}命宫", find_palace(chart_a, "命"), find_palace(chart_b, "命")),
        (f"{label_a}夫妻宫—{label_b}命宫", find_palace(chart_a, "夫妻"), find_palace(chart_b, "命")),
        (f"{label_b}夫妻宫—{label_a}命宫", find_palace(chart_b, "夫妻"), find_palace(chart_a, "命")),
    )
    findings: list[dict[str, Any]] = []
    for title, left, right in axes:
        relation, note = branch_relation(left["earthlyBranch"], right["earthlyBranch"])
        findings.append(
            make_finding(
                title,
                fact=f"地支为{left['earthlyBranch']}—{right['earthlyBranch']}，关系为{relation}。",
                interpretation=note + "；此项只作低权重交叉检查。",
                evidence=(f"{left['earthlyBranch']}—{right['earthlyBranch']}：{relation}",),
            )
        )
    return findings


def cross_mutagen_finding(
    source_chart: dict[str, Any],
    target_chart: dict[str, Any],
    source_label: str,
    target_label: str,
) -> dict[str, Any]:
    facts: list[str] = []
    readings: list[str] = []
    for row in birth_mutagen_rows(source_chart):
        located = locate_star(target_chart, row["star"])
        if not located:
            continue
        palace, _ = located
        palace_name = canonical_palace_name(palace["name"])
        facts.append(f"化{row['mutagen']}{row['star']}→{target_label}{palace_display(palace_name)}")
        readings.append(
            f"化{row['mutagen']}映射到{target_label}的{palace_display(palace_name)}，"
            f"传统上把它视为{MUTAGEN_EFFECTS[row['mutagen']]}的互动领域"
        )
    return make_finding(
        f"{source_label}生年四化映射到{target_label}",
        fact="；".join(facts) + "。",
        interpretation="；".join(readings) + "。跨盘四化是传统辅助观察，不表示一方必然造成另一方的事件。",
        evidence=facts,
    )


def compatibility_aux_finding(chart: dict[str, Any], label: str) -> dict[str, Any]:
    spouse = find_palace(chart, "夫妻")
    rows: list[str] = []
    readings: list[str] = []
    for star in all_stars(spouse):
        if star["name"] in SUPPORT_STARS:
            rows.append(f"{star['name']}（支持）")
            readings.append(f"{star['name']}提示{SUPPORT_STARS[star['name']]}可成为关系资源")
        elif star["name"] in CHALLENGE_STARS:
            rows.append(f"{star['name']}（摩擦）")
            readings.append(f"{star['name']}提示需管理{CHALLENGE_STARS[star['name']]}的互动成本")
    if not rows:
        rows.append("未见规则表中的主要辅煞信号")
        readings.append("这一层不额外放大支持或摩擦，仍以主星结构和现实互动为主")
    return make_finding(
        f"{label}夫妻宫的支持与摩擦",
        fact=f"{palace_fact(chart, spouse)}；筛选结果：{'、'.join(rows)}。",
        interpretation="；".join(readings) + "。",
        evidence=(f"{label}夫妻宫·{spouse['earthlyBranch']}", *rows),
    )


def compatibility_timing_finding(
    raw_a: dict[str, Any], raw_b: dict[str, Any], label_a: str, label_b: str
) -> dict[str, Any] | None:
    if not raw_a.get("target") or not raw_b.get("target"):
        return None
    facts: list[str] = []
    for raw, label in ((raw_a, label_a), (raw_b, label_b)):
        overlay, _ = period_overlay(raw["chart"], raw["target"]["yearly"], "夫妻")
        facts.append(f"{label}流年夫妻宫→本命{palace_display(overlay['name'])}·{overlay['earthlyBranch']}")
    return make_finding(
        "双方目标流年的关系落点",
        fact=f"目标日期{raw_a['target']['solarDate']}：{'；'.join(facts)}。",
        interpretation=(
            "两人的流年关系主题需分别通过各自叠入的本命领域观察；即使双方同时出现关系活跃信号，"
            "也不能据此推断一定相遇、结婚或分手。"
        ),
        evidence=facts,
    )


def build_compatibility_payload(
    raw_a: dict[str, Any], raw_b: dict[str, Any], label_a: str, label_b: str
) -> dict[str, Any]:
    chart_a = raw_a["chart"]
    chart_b = raw_b["chart"]
    sections: list[dict[str, Any]] = [
        {
            "id": "individual",
            "title": "双方单盘关系结构",
            "findings": [
                core_finding(chart_a, "relationship", title_prefix=f"{label_a}："),
                core_finding(chart_b, "relationship", title_prefix=f"{label_b}："),
                compatibility_aux_finding(chart_a, label_a),
                compatibility_aux_finding(chart_b, label_b),
            ],
        },
        {
            "id": "traits",
            "title": "关系需要与表达方式",
            "findings": [
                trait_fit_finding(chart_a, chart_b, label_a, label_b),
                trait_fit_finding(chart_b, chart_a, label_b, label_a),
            ],
        },
        {
            "id": "cross-mutagens",
            "title": "双方生年四化跨盘映射",
            "findings": [
                cross_mutagen_finding(chart_a, chart_b, label_a, label_b),
                cross_mutagen_finding(chart_b, chart_a, label_b, label_a),
            ],
        },
        {
            "id": "branches",
            "title": "宫位地支辅助检查",
            "findings": branch_findings(chart_a, chart_b, label_a, label_b),
        },
    ]
    timing = compatibility_timing_finding(raw_a, raw_b, label_a, label_b)
    if timing:
        sections.append({"id": "timing", "title": "目标日期关系窗口", "findings": [timing]})
    sections.append(
        {
            "id": "actions",
            "title": "合盘后的现实核验",
            "findings": [
                make_finding(
                    "先核对真实意愿",
                    practical_note="分别确认双方对关系性质、承诺节奏和个人空间的真实意愿，不用命盘代替对方表态。",
                ),
                make_finding(
                    "把差异变成可协商事项",
                    practical_note="把陪伴频率、冲突处理、金钱边界、社交边界和共同生活安排逐项讨论。",
                ),
                make_finding(
                    "用实际相处校准",
                    practical_note="观察承诺是否兑现、边界是否受尊重、冲突后能否修复；这些现实证据的权重高于合盘象征。",
                ),
            ],
        }
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "compatibility",
        "topic": "compatibility",
        "topicLabel": TOPIC_LABELS["compatibility"],
        "interpreter": {"name": "ziwei-rule-interpreter", "version": INTERPRETER_VERSION},
        "engine": raw_a["engine"],
        "config": raw_a["config"],
        "subjects": [subject_summary(raw_a, label_a), subject_summary(raw_b, label_b)],
        "targetDate": raw_a["target"]["solarDate"] if raw_a.get("target") else None,
        "sections": sections,
        "calibrationQuestions": [
            "双方对陪伴、空间、承诺和公开关系的期待是否已经直接说清楚？",
            "过去真实相处中，哪些结构描述得到行为证据支持，哪些明显不符合？",
            "出现冲突时，双方能否停止控制、冷处理或猜测，并完成一次可验证的修复？",
        ],
        "warnings": [*raw_a["warnings"], *raw_b["warnings"]],
        "disclaimer": f"{DISCLAIMER}{COMPATIBILITY_DISCLAIMER}",
    }


def render_subject(subject: dict[str, Any]) -> list[str]:
    return [
        f"- {subject['label']}：{subject['solarDate']}（{subject['lunarDate']}），{subject['time']}（{subject['timeRange']}），{subject['gender']}",
        f"  命宫/身宫：{subject['soulPalaceBranch']}/{subject['bodyPalaceBranch']}（身宫落{palace_display(subject['bodyPalaceName'])}）；命主/身主/五行局：{subject['soul']}/{subject['body']}/{subject['fiveElementsClass']}",
    ]


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [f"# 紫微斗数{payload['topicLabel']}规则解读", "", "## 排盘口径与对象", ""]
    config = payload["config"]
    lines.append(
        f"- 引擎：{payload['engine']['name']} {payload['engine']['version']}；"
        f"算法：{config['algorithm']}；盘型：{config['astroTypeLabel']}"
    )
    subjects = payload.get("subjects") or [payload["subject"]]
    for subject in subjects:
        lines.extend(render_subject(subject))
    if payload.get("targetDate"):
        lines.append(f"- 目标日期：{payload['targetDate']}")
    lines.append("")

    for section in payload["sections"]:
        if not section["findings"]:
            continue
        lines.extend((f"## {section['title']}", ""))
        for finding in section["findings"]:
            lines.append(f"### {finding['title']}")
            lines.append("")
            if finding["fact"]:
                lines.append(f"- 脚本事实：{finding['fact']}")
            if finding["traditionalInterpretation"]:
                lines.append(f"- 传统解释：{finding['traditionalInterpretation']}")
            if finding["practicalNote"]:
                lines.append(f"- 现实建议：{finding['practicalNote']}")
            if finding["evidence"]:
                lines.append(f"- 依据：{'；'.join(finding['evidence'])}")
            lines.append("")

    lines.extend(("## 现实校准问题", ""))
    for index, question in enumerate(payload["calibrationQuestions"], start=1):
        lines.append(f"{index}. {question}")
    lines.append("")
    if payload["warnings"]:
        lines.extend(("## 排盘警告", ""))
        lines.extend(f"- {warning}" for warning in payload["warnings"])
        lines.append("")
    lines.extend(("## 使用边界", "", f"> {payload['disclaimer']}", ""))
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
    topic = validate_arguments(parser, args)
    try:
        raw_a = run_node(PAN_SCRIPT, node_arguments(args, partner=False))
        if topic == "compatibility":
            raw_b = run_node(PAN_SCRIPT, node_arguments(args, partner=True))
            payload = build_compatibility_payload(raw_a, raw_b, args.label, args.partner_label)
        else:
            payload = build_single_payload(raw_a, topic, args.label)
        rendered = (
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            if args.format == "json"
            else render_markdown(payload)
        )
        write_output(rendered, args.output)
    except (RuntimeError, ValueError) as error:
        sys.stderr.write(f"解盘失败：{error}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
