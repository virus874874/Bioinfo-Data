import csv
import json
import tempfile
import unittest
from pathlib import Path

from gdc_scout.evaluation import evaluate


class EvaluationTests(unittest.TestCase):
    def test_evaluation_writes_report(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            ev = {k: "x" for k in ("endpoint", "url", "request_timestamp", "response_sha256", "parser_version")}; ev["http_status"] = 200; ev["harness_condition"] = "NORMAL"
            (p / "source_snapshot.json").write_text(json.dumps({"ev1": ev}), encoding="utf-8")
            with (p / "dataset_cards.csv").open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["project_id", "stage_coverage", "vital_status_coverage", "endpoint_coverage", "access_level"]); w.writeheader(); w.writerow({"project_id": "P", "stage_coverage": 1, "vital_status_coverage": 1, "endpoint_coverage": 1, "access_level": "public"})
            report = evaluate(p)
            self.assertEqual(report["overall_confidence"], 1.0)
            self.assertTrue((p / "eval_report.json").is_file())


if __name__ == "__main__": unittest.main()

