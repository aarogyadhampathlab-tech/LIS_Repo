import unittest
from datetime import datetime, timedelta, timezone

from core.patient_records import patient_freshness, remove_replaced_missing_results
from GUI.main_gui import group_records_by_received_date


class PatientRecordDisplayTests(unittest.TestCase):
    def test_results_are_grouped_by_received_date_in_recency_order(self):
        newest = ("123", "PATIENT", "WBC", "7.4")
        same_day = ("456", "OTHER", "RBC", "4.5")
        older = ("789", "THIRD", "PLT", "200")
        missing_time = ("000", "UNKNOWN", "HGB", "12")
        newest_time = datetime(2026, 11, 15, 10, tzinfo=timezone.utc)
        same_day_time = datetime(2026, 11, 15, 9, tzinfo=timezone.utc)
        older_time = datetime(2026, 11, 14, 23, tzinfo=timezone.utc)

        grouped = group_records_by_received_date(
            [newest, same_day, older, missing_time],
            {
                newest: newest_time,
                same_day: same_day_time,
                older: older_time,
            },
        )

        self.assertEqual(
            list(grouped),
            [newest_time.date(), older_time.date(), None],
        )
        self.assertEqual(grouped[newest_time.date()], [newest, same_day])
        self.assertEqual(grouped[older_time.date()], [older])
        self.assertEqual(grouped[None], [missing_time])

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
