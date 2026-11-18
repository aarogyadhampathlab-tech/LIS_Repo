import json
import tempfile
import unittest
from pathlib import Path

from core.alert_rules import load_alert_rules, save_alert_rules
from GUI.settings import build_alert_rule_catalog


class AlertRuleSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.configuration_path = Path(self.temporary_directory.name) / "thresholds.json"
        self.configuration_path.write_text(
            json.dumps(
                {
                    "_note": "Existing note",
                    "critical_ranges": {
                        "SODIUM (NA+)": {
                            "low": 127,
                            "high": 155,
                            "unit": "mmol/L",
                        },
                        "GLUCOSE": {"high": 300, "unit": "mg/dL"},
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_saves_enabled_state_without_changing_existing_thresholds(self):
        rules = load_alert_rules(self.configuration_path)
        self.assertTrue(rules["SODIUM (NA+)"]["enabled"])
        rules["GLUCOSE"]["enabled"] = False

        saved = save_alert_rules(rules, self.configuration_path)

        self.assertEqual(saved["SODIUM (NA+)"]["low"], 127)
        self.assertEqual(saved["SODIUM (NA+)"]["high"], 155)
        self.assertEqual(saved["GLUCOSE"]["high"], 300)
        self.assertFalse(
            load_alert_rules(self.configuration_path)["GLUCOSE"]["enabled"]
        )
        self.assertEqual(
            json.loads(self.configuration_path.read_text(encoding="utf-8"))["_note"],
            "Existing note",
        )

    def test_rejects_invalid_thresholds_without_overwriting_configuration(self):
        original = self.configuration_path.read_text(encoding="utf-8")
        rules = load_alert_rules(self.configuration_path)
        rules["SODIUM (NA+)"]["low"] = 155

        with self.assertRaisesRegex(ValueError, "must be below"):
            save_alert_rules(rules, self.configuration_path)

        self.assertEqual(
            self.configuration_path.read_text(encoding="utf-8"), original
        )

    def test_rejects_non_boolean_enabled_setting(self):
        rules = load_alert_rules(self.configuration_path)
        rules["GLUCOSE"]["enabled"] = 1

        with self.assertRaisesRegex(ValueError, "must be true or false"):
            save_alert_rules(rules, self.configuration_path)

    def test_catalog_includes_mapped_tests_without_inventing_thresholds(self):
        configured = load_alert_rules(self.configuration_path)
        catalog = build_alert_rule_catalog(
            configured, ["SODIUM (NA+)", "MAPPED TEST", "GLUCOSE"]
        )

        self.assertIn("MAPPED TEST", catalog)
        self.assertFalse(catalog["MAPPED TEST"]["enabled"])
        self.assertNotIn("low", catalog["MAPPED TEST"])
        self.assertNotIn("high", catalog["MAPPED TEST"])
        self.assertEqual(catalog["GLUCOSE"]["high"], 300)

    def test_disabled_test_can_have_no_thresholds(self):
        rules = {"UNCONFIGURED TEST": {"enabled": False, "unit": ""}}

        saved = save_alert_rules(rules, self.configuration_path)

        self.assertFalse(saved["UNCONFIGURED TEST"]["enabled"])
        self.assertNotIn("low", saved["UNCONFIGURED TEST"])
        self.assertNotIn("high", saved["UNCONFIGURED TEST"])

    def test_test_without_thresholds_cannot_be_enabled(self):
        with self.assertRaisesRegex(ValueError, "before its alert can be enabled"):
            save_alert_rules(
                {"UNCONFIGURED TEST": {"enabled": True, "unit": ""}},
                self.configuration_path,
            )


if __name__ == "__main__":
    unittest.main()
