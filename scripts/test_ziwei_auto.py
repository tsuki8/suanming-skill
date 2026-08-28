from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("ziwei_auto.py")


def run_script(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )


class ZiweiAutoTest(unittest.TestCase):
    def test_known_time_builds_six_topic_fact_packets(self) -> None:
        completed = run_script(
            "--solar",
            "2000-08-16",
            "--hour",
            "03:30",
            "--sex",
            "女",
            "--target-date",
            "2025-01-01",
            "--format",
            "json",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        data = json.loads(completed.stdout)

        self.assertEqual(data["mode"], "chart-facts")
        self.assertEqual(data["chartSummary"]["soulPalaceBranch"], "午")
        self.assertEqual(data["chartSummary"]["bodyPalaceBranch"], "戌")
        self.assertEqual(set(data["topics"]), {
            "career",
            "wealth",
            "health",
            "relationship",
            "overall",
            "study",
        })
        self.assertEqual(data["topics"]["career"]["palaces"][0]["name"], "官禄")
        self.assertEqual(
            [row["name"] for row in data["focusStars"]],
            ["文昌", "文曲", "红鸾", "天喜"],
        )
        self.assertEqual(
            [row["mutagen"] for row in data["birthMutagens"]],
            ["禄", "权", "科", "忌"],
        )
        self.assertEqual(data["target"]["nominalAge"], 25)

    def test_missing_time_switches_to_13_candidate_comparison(self) -> None:
        completed = run_script(
            "--solar",
            "2000-08-16",
            "--sex",
            "女",
            "--format",
            "json",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        data = json.loads(completed.stdout)
        self.assertEqual(data["mode"], "time-comparison")
        self.assertEqual(len(data["candidates"]), 13)
        self.assertEqual(data["candidates"][0]["label"], "早子")
        self.assertEqual(data["candidates"][-1]["label"], "晚子")

    def test_output_option_writes_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "facts.md"
            completed = run_script(
                "--solar",
                "2000-08-16",
                "--shichen",
                "寅",
                "--sex",
                "女",
                "--output",
                str(output),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "")
            text = output.read_text(encoding="utf-8")
            self.assertIn("# 紫微斗数自动计算事实包", text)
            self.assertIn("## 六大主题事实输入", text)

    def test_rejects_leap_flag_with_solar_date(self) -> None:
        completed = run_script(
            "--solar",
            "2000-08-16",
            "--leap",
            "--sex",
            "女",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--leap 只能与 --lunar 一起使用", completed.stderr)


if __name__ == "__main__":
    unittest.main()
