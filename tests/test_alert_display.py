import unittest

from GUI.alerts import AlertPanelMixin


class AlertDisplayTests(unittest.TestCase):
    def test_groups_only_missing_results_by_patient(self):
        alerts = [
            {
                "alert_key": "missing-wbc",
                "patient_id": "00123",
                "patient_name": "Patient",
                "test_name": "WBC",
                "reason": "MISSING_RESULT",
            },
            {
                "alert_key": "critical-rbc",
                "patient_id": "00123",
                "patient_name": "Patient",
                "test_name": "RBC",
                "reason": "LOW (< 4)",
            },
            {
                "alert_key": "missing-rbc",
                "patient_id": "00123",
                "patient_name": "Updated Patient",
                "test_name": "RBC",
                "reason": "MISSING_RESULT",
            },
            {
                "alert_key": "other-patient",
                "patient_id": "00456",
                "patient_name": "Other",
                "test_name": "WBC",
                "reason": "MISSING_RESULT",
            },
        ]

        grouped = AlertPanelMixin._group_alerts_for_display(alerts)

        self.assertEqual(len(grouped), 3)
        self.assertEqual(grouped[0]["alert_keys"], ["missing-wbc", "missing-rbc"])
        self.assertEqual(grouped[0]["missing_tests"], ["WBC", "RBC"])
        self.assertEqual(grouped[1]["alert_key"], "critical-rbc")
        self.assertEqual(grouped[2]["alert_keys"], ["other-patient"])


class ThresholdAlertBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.alerts = type("AlertHarness", (AlertPanelMixin,), {})()

    def test_disabled_test_skips_its_numeric_threshold_alert(self):
        self.alerts.alert_rules = {
            "GLUCOSE": {"high": 300, "unit": "mg/dL", "enabled": False}
        }

        self.assertIsNone(self.alerts._alert_reason("GLUCOSE", "301 mg/dL"))

    def test_enabled_test_keeps_its_configured_threshold_alert(self):
        self.alerts.alert_rules = {
            "GLUCOSE": {"high": 300, "unit": "mg/dL", "enabled": True}
        }

        self.assertEqual(
            self.alerts._alert_reason("GLUCOSE", "301 mg/dL"),
            "HIGH (> 300)",
        )

    def test_disabling_numeric_threshold_keeps_missing_and_error_alerts(self):
        self.alerts.alert_rules = {
            "GLUCOSE": {"high": 300, "unit": "mg/dL", "enabled": False}
        }

        self.assertEqual(
            self.alerts._alert_reason("GLUCOSE", "MISSING_RESULT"),
            "MISSING_RESULT",
        )
        self.assertEqual(
            self.alerts._alert_reason("GLUCOSE", "Technical Error"),
            "TECHNICAL ERROR",
        )


if __name__ == "__main__":
    unittest.main()
