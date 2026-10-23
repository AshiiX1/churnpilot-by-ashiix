from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.paths import DATASET_FILENAME, dataset_candidates, resolve_dataset_path


class DatasetPathTests(unittest.TestCase):
    def test_prefers_csv_beside_executable_when_present(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            exe_dir = base / "dist" / "ChurnPilot"
            bundle = exe_dir / "_internal"
            cwd = base / "other"
            expected = exe_dir / "data" / DATASET_FILENAME
            expected.parent.mkdir(parents=True)
            expected.write_text("stub", encoding="utf-8")

            result = resolve_dataset_path(
                executable_dir=exe_dir,
                bundle_root=bundle,
                working_dir=cwd,
            )
            self.assertEqual(result, expected)

    def test_finds_csv_in_pyinstaller_internal_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            exe_dir = base / "dist" / "ChurnPilot"
            bundle = exe_dir / "_internal"
            cwd = base / "other"
            expected = bundle / "data" / DATASET_FILENAME
            expected.parent.mkdir(parents=True)
            expected.write_text("stub", encoding="utf-8")

            result = resolve_dataset_path(
                executable_dir=exe_dir,
                bundle_root=bundle,
                working_dir=cwd,
            )
            self.assertEqual(result, expected)

    def test_returns_expected_external_path_when_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            exe_dir = base / "dist" / "ChurnPilot"
            bundle = exe_dir / "_internal"
            cwd = base / "other"

            result = resolve_dataset_path(
                executable_dir=exe_dir,
                bundle_root=bundle,
                working_dir=cwd,
            )
            self.assertEqual(result, exe_dir / "data" / DATASET_FILENAME)

    def test_candidates_are_unique(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            candidates = dataset_candidates(
                executable_dir=base,
                bundle_root=base,
                working_dir=base,
            )
            self.assertEqual(len(candidates), 1)


if __name__ == "__main__":
    unittest.main()
