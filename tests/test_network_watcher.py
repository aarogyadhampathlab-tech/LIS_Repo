import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from core.network_watcher import MedicalHandler


class ExistingFileOrderTests(unittest.TestCase):
    def test_existing_logs_are_processed_oldest_to_newest(self):
        prefix = datetime.now().strftime("%m%d%Y")
        with tempfile.TemporaryDirectory() as temporary_directory:
            older_path = Path(temporary_directory) / f"{prefix}_older_R.log"
            newer_path = Path(temporary_directory) / f"{prefix}_newer_R.log"
            older_path.write_text("older", encoding="utf-8")
            newer_path.write_text("newer", encoding="utf-8")
            os.utime(older_path, (1000, 1000))
            os.utime(newer_path, (2000, 2000))

            processed_paths = []
            handler = MedicalHandler(lambda _records: None)
            with patch.object(
                handler,
                "_process_file",
                side_effect=processed_paths.append,
            ):
                handler.process_existing_files(temporary_directory)

        self.assertEqual(processed_paths, [str(older_path), str(newer_path)])


if __name__ == "__main__":
    unittest.main()
