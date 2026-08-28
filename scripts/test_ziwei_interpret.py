from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.ziwei_interpret import branch_relation


SCRIPT = Path(__file__).resolve().with_name("ziwei_interpret.py")


def run_script(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )


BASE = (
    "--solar",
    "2000-08-16",
    "--hour",
    "03:30",
    "--sex",
    "女",
)

PARTNER = (
    "--partner-solar",
    "1998-12-20",
    "--partner-hour",
    "14:20",
    "--partner-sex",
    "男",
)


class ZiweiInterpretTest(unittest.TestCase):
    def test_same_branch_is_not_misclassified_as_trine(self) -> None:
        relation, _ = branch_relation("午", "午")
        self.assertEqual(relation, "同支")

    def test_career_json_contains_evidence_and_timing(self) -> None:
        completed = run_script(
            "--topic",
            "事业",
            *BASE,
            "--target-date",
            "2026-08-28",
            "--format",
            "json",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        data = json.loads(completed.stdout)

        self.assertEqual(data["mode"], "interpretation")
        self.assertEqual(data["topic"], "career")
        self.assertEqual(data["sections"][0]["findings"][0]["title"], "官禄宫主轴")
        self.assertTrue(data["sections"][0]["findings"][0]["evidence"])
        context_titles = [row["title"] for row in data["sections"][1]["findings"]]
        self.assertIn("身宫的行动落点", context_titles)
        mutagens = next(section for section in data["sections"] if section["id"] == "mutagens")
        self.assertEqual(len(mutagens["findings"]), 4)
        timing = next(section for section in data["sections"] if section["id"] == "timing")
        self.assertEqual([row["title"] for row in timing["findings"]], ["当前大限", "目标流年"])

    def test_wealth_alias_and_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "wealth.md"
            completed = run_script("--topic", "财运", *BASE, "--output", str(output))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "")
            text = output.read_text(encoding="utf-8")
            self.assertIn("# 紫微斗数财帛规则解读", text)
            self.assertIn("财帛宫主轴", text)
            self.assertIn("现金流", text)

    def test_relationship_markdown_has_relationship_signals_and_boundaries(self) -> None:
        completed = run_script("--topic", "relationship", *BASE)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("夫妻宫主轴", completed.stdout)
        self.assertIn("红鸾天喜等关系信号", completed.stdout)
        self.assertIn("不能单独证明恋爱、婚期或所谓正缘", completed.stdout)
        self.assertIn("并非经科学验证", completed.stdout)

    def test_compatibility_requires_partner_consent(self) -> None:
        completed = run_script("--topic", "合盘", *BASE, *PARTNER)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--partner-consent", completed.stderr)

    def test_compatibility_builds_two_sided_non_scored_analysis(self) -> None:
        completed = run_script(
            "--topic",
            "compatibility",
            *BASE,
            "--label",
            "甲方",
            *PARTNER,
            "--partner-label",
            "乙方",
            "--partner-consent",
            "--target-date",
            "2026-08-28",
            "--format",
            "json",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        data = json.loads(completed.stdout)

        self.assertEqual(data["mode"], "compatibility")
        self.assertEqual([row["label"] for row in data["subjects"]], ["甲方", "乙方"])
        section_ids = [section["id"] for section in data["sections"]]
        self.assertEqual(
            section_ids,
            ["individual", "traits", "cross-mutagens", "branches", "timing", "actions"],
        )
        self.assertNotIn("score", completed.stdout.lower())
        cross = next(section for section in data["sections"] if section["id"] == "cross-mutagens")
        self.assertEqual(len(cross["findings"]), 2)
        self.assertTrue(all(len(row["evidence"]) == 4 for row in cross["findings"]))

    def test_partner_arguments_are_rejected_for_single_chart_topic(self) -> None:
        completed = run_script("--topic", "事业", *BASE, *PARTNER)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--partner-* 参数只用于", completed.stderr)


if __name__ == "__main__":
    unittest.main()
