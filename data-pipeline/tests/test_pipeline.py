import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from policy_pipeline.main import load_settings, process_sample


class PipelineTests(unittest.TestCase):
    def test_settings_defaults(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            settings = load_settings()

        self.assertEqual(settings["app_env"], "local")
        self.assertEqual(settings["source_timeout_seconds"], "30")

    def test_process_sample_counts_policies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text(json.dumps({"source": "unit", "policies": [{"id": "p1"}]}), encoding="utf-8")

            result = process_sample(path)

        self.assertEqual(result["source"], "unit")
        self.assertEqual(result["policy_count"], 1)
