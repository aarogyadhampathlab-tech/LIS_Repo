import unittest

from core.parser_logic import parse_log_line


class ParseLogLineTests(unittest.TestCase):
    def test_parses_analyzer_barcode_for_patient_directory_lookup(self):
        record = parse_log_line("CeltacAlpha\t260012150\t\t\tWBC\t7.3")

        self.assertEqual(
            record,
            ("260012150", "UNKNOWN", "ID: WBC", "7.3"),
        )

    def test_preserves_legacy_patient_name_and_barcode_columns(self):
        record = parse_log_line("2023-10-27\tJANE SMITH\t67890\t0\t301\t95 mg/dL")

        self.assertEqual(
            record,
            ("67890", "JANE SMITH", "TOTAL PROTEIN", "95 mg/dL"),
        )


if __name__ == "__main__":
    unittest.main()
