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


if __name__ == "__main__":
    unittest.main()
