import tempfile
import unittest
from pathlib import Path

from gdc_scout.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_loads_project_and_list(self):
        config = load_config("configs/task_spec.yaml")
        self.assertEqual(config["projects"]["luad"]["project_id"], "TCGA-LUAD")
        self.assertEqual(len(config["evidence"]["required_fields"]), 6)

    def test_missing_project_id_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"; p.write_text('{"projects":{"x":{}}}', encoding="utf-8")
            with self.assertRaises(ConfigError): load_config(p)


if __name__ == "__main__": unittest.main()

