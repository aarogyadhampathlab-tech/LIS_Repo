import tempfile
import unittest
from pathlib import Path

from core.patient_directory import load_patient_names


class PatientDirectoryTests(unittest.TestCase):
    def test_loads_barcode_names_and_uses_latest_duplicate(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "patients.csv"
            csv_path.write_text(
                "Barcode,Patient Name,Timestamp\n"
                '"00123","First Name","time 1"\n'
                '"00123","Updated Name","time 2"\n'
                '"00456","Second Patient","time 2"\n',
                encoding="utf-8",
            )

            self.assertEqual(
                load_patient_names(csv_path),
                {"00123": "Updated Name", "00456": "Second Patient"},
            )

    def test_rejects_csv_without_required_columns(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "patients.csv"
            csv_path.write_text("ID,Name\n1,Patient\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Barcode and Patient Name"):
                load_patient_names(csv_path)


if __name__ == "__main__":
    unittest.main()
