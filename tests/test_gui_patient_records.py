import unittest
from datetime import datetime, timedelta, timezone

from core.patient_records import patient_freshness, remove_replaced_missing_results


class PatientRecordDisplayTests(unittest.TestCase):
    def test_new_result_replaces_only_matching_missing_test(self):
        missing_record = ("123", "PATIENT", "WBC", "MISSING_RESULT")
        other_test = ("123", "PATIENT", "RBC", "MISSING_RESULT")
        other_patient = ("456", "OTHER", "WBC", "MISSING_RESULT")
        received_at = datetime.now(timezone.utc)
        records = [missing_record, other_test, other_patient]
        received_at_by_record = {
            missing_record: received_at,
            other_test: received_at,
            other_patient: received_at,
        }

        remove_replaced_missing_results(
            records,
            received_at_by_record,
            ("123", "PATIENT", "WBC", "7.4"),
        )

        self.assertEqual(records, [other_test, other_patient])
        self.assertNotIn(missing_record, received_at_by_record)
        self.assertIn(other_test, received_at_by_record)
        self.assertIn(other_patient, received_at_by_record)

    def test_missing_result_remains_when_no_actual_result_arrives(self):
        missing_record = ("123", "PATIENT", "WBC", "MISSING_RESULT")
        received_at = datetime.now(timezone.utc)
        records = [missing_record]
        received_at_by_record = {missing_record: received_at}

        remove_replaced_missing_results(
            records,
            received_at_by_record,
            ("123", "PATIENT", "WBC", "MISSING_RESULT"),
        )

        self.assertEqual(records, [missing_record])
        self.assertEqual(received_at_by_record, {missing_record: received_at})

    def test_patient_freshness_uses_received_time_cutoffs(self):
        now = datetime.now(timezone.utc)

        self.assertEqual(
            patient_freshness(now - timedelta(minutes=59), now),
            "LATEST",
        )
        self.assertEqual(
            patient_freshness(now - timedelta(hours=1), now),
            "OLD",
        )
        self.assertEqual(
            patient_freshness(now - timedelta(hours=24), now),
            "LONG AGO",
        )


if __name__ == "__main__":
    unittest.main()
