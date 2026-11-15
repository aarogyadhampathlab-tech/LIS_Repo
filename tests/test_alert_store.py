import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.alert_store import AlertStore


class GlucoseAcknowledgmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "alerts.sqlite3"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_acknowledgment_is_retained_when_store_is_reopened(self):
        store = AlertStore(self.database_path)
        self.assertTrue(store.acknowledge_glucose('["patient","test","100"]', "time"))

        reopened_store = AlertStore(self.database_path)
        self.assertEqual(
            reopened_store.acknowledged_glucose_keys(),
            {'["patient","test","100"]'},
        )

    def test_acknowledge_many_persists_each_record(self):
        store = AlertStore(self.database_path)
        store.acknowledge_glucose_many({"first", "second"}, "time")

        self.assertEqual(
            AlertStore(self.database_path).acknowledged_glucose_keys(),
            {"first", "second"},
        )

    def test_acknowledge_many_marks_each_alert(self):
        store = AlertStore(self.database_path)
        store.create_alert("first", "123", "Patient", "WBC", "", "MISSING_RESULT", "time")
        store.create_alert("second", "123", "Patient", "RBC", "", "MISSING_RESULT", "time")

        store.acknowledge_many(["first", "second"], "acknowledged")

        self.assertEqual(store.unacknowledged_alerts(), [])

    def test_result_received_time_is_persisted_across_restarts(self):
        record = ("260012150", "UNKNOWN", "WBC", "7.3")
        first_observed_at = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
        later_observed_at = first_observed_at + timedelta(hours=5)

        store = AlertStore(self.database_path)
        saved_time = store.get_or_create_result_received_at(
            record, first_observed_at
        )
        reopened_store = AlertStore(self.database_path)
        replayed_time = reopened_store.get_or_create_result_received_at(
            record, later_observed_at
        )

        self.assertEqual(saved_time, first_observed_at)
        self.assertEqual(replayed_time, first_observed_at)

    def test_distinct_result_gets_its_own_received_time(self):
        first_record = ("123", "UNKNOWN", "WBC", "7.3")
        next_record = ("123", "UNKNOWN", "WBC", "7.5")
        first_observed_at = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
        next_observed_at = first_observed_at + timedelta(minutes=10)
        store = AlertStore(self.database_path)

        self.assertEqual(
            store.get_or_create_result_received_at(
                first_record, first_observed_at
            ),
            first_observed_at,
        )
        self.assertEqual(
            store.get_or_create_result_received_at(next_record, next_observed_at),
            next_observed_at,
        )


if __name__ == "__main__":
    unittest.main()
