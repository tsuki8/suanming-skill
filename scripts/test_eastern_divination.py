"""Regression tests for the deterministic Eastern divination CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eastern_divination.py"


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *arguments),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class EasternDivinationTests(unittest.TestCase):
    def test_rule_table_covers_all_unique_hexagrams(self) -> None:
        from scripts.meihua_rules import HEXAGRAMS, HEXAGRAM_BY_TRIGRAMS, TRIGRAMS

        self.assertEqual(set(HEXAGRAMS), set(range(1, 65)))
        self.assertEqual(len(HEXAGRAM_BY_TRIGRAMS), 64)
        self.assertEqual(len(TRIGRAMS), 8)
        for upper_name in (row["name"] for row in TRIGRAMS.values()):
            for lower_name in (row["name"] for row in TRIGRAMS.values()):
                self.assertIn((upper_name, lower_name), HEXAGRAM_BY_TRIGRAMS)

    def test_classical_number_example(self) -> None:
        result = run_cli(
            "--method",
            "meihua",
            "--question",
            "未来一个月这个项目应优先验证什么？",
            "--numbers",
            "2",
            "3",
            "--moving",
            "1",
            "--first-cast",
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["primaryHexagram"]["number"], 49)
        self.assertEqual(payload["primaryHexagram"]["fullName"], "泽火革")
        self.assertEqual(payload["nuclearHexagram"]["number"], 44)
        self.assertEqual(payload["changedHexagram"]["number"], 31)
        self.assertEqual(payload["movingLine"]["number"], 1)
        self.assertEqual(payload["bodyUse"]["initialRelation"]["code"], "用克体")
        self.assertEqual(payload["bodyUse"]["changedRelation"]["code"], "用生体")

    def test_number_cast_defaults_moving_total_to_sum(self) -> None:
        result = run_cli(
            "--question",
            "下一步先验证哪个现实条件？",
            "--numbers",
            "1",
            "5",
            "--first-cast",
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["casting"]["movingTotal"], 6)
        self.assertEqual(payload["movingLine"]["number"], 6)

    def test_explicit_datetime_uses_lunar_calendar_and_shichen(self) -> None:
        result = run_cli(
            "--question",
            "未来一个月项目推进需要先验证什么？",
            "--datetime",
            "2026-08-28T15:30",
            "--first-cast",
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        casting = payload["casting"]
        self.assertEqual(casting["input"]["lunarMonth"], 7)
        self.assertEqual(casting["input"]["lunarDay"], 16)
        self.assertEqual(casting["input"]["yearBranch"], "午")
        self.assertEqual(casting["input"]["shichen"], "申")
        self.assertEqual(casting["upperTotal"], 30)
        self.assertEqual(casting["lowerTotal"], 39)
        self.assertEqual(payload["primaryHexagram"]["number"], 39)
        self.assertEqual(payload["nuclearHexagram"]["number"], 64)
        self.assertEqual(payload["changedHexagram"]["number"], 8)

    def test_late_zi_convention_is_reported(self) -> None:
        result = run_cli(
            "--question",
            "明天沟通前先核实什么信息？",
            "--datetime",
            "2026-08-28T23:20+08:00",
            "--first-cast",
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["casting"]["input"]["shichen"], "子")
        self.assertEqual(payload["casting"]["input"]["timezoneNote"], "UTC+8")
        self.assertTrue(any("晚子时" in warning for warning in payload["warnings"]))

    def test_datetime_requires_an_explicit_time(self) -> None:
        result = run_cli(
            "--question",
            "下一步先验证哪个现实条件？",
            "--datetime",
            "2026-08-28",
            "--first-cast",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("YYYY-MM-DDTHH:MM", result.stderr)

    def test_first_cast_acknowledgement_is_required(self) -> None:
        result = run_cli(
            "--question",
            "下一步先验证哪个现实条件？",
            "--numbers",
            "2",
            "3",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--first-cast", result.stderr)

    def test_high_risk_question_is_rejected(self) -> None:
        result = run_cli(
            "--question",
            "我应该买哪只股票投资？",
            "--numbers",
            "2",
            "3",
            "--first-cast",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("不能使用占卜程序决定", result.stderr)

    def test_multiple_questions_are_rejected(self) -> None:
        result = run_cli(
            "--question",
            "这个方案是否可行？另一个方案呢？",
            "--numbers",
            "2",
            "3",
            "--first-cast",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("一次只能处理一个问题", result.stderr)

    def test_lost_item_output_puts_reality_checks_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.md"
            result = run_cli(
                "--question",
                "我该怎样缩小钥匙的遗失范围？",
                "--numbers",
                "4",
                "7",
                "--first-cast",
                "--output",
                str(output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("回溯最后确认时间与移动路线", rendered)
            self.assertIn("联系场所失物招领", rendered)
            self.assertIn("不等待占卜结果", rendered)


if __name__ == "__main__":
    unittest.main()
