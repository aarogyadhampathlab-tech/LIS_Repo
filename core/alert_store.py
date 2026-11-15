import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


class AlertStore:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_key TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    patient_name TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    flagged_value TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'UNACKNOWLEDGED',
                    acknowledged_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS glucose_acknowledgments (
                    record_key TEXT PRIMARY KEY,
                    acknowledged_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS result_received_times (
                    record_key TEXT PRIMARY KEY,
                    received_at TEXT NOT NULL
                )
                """
            )

    def known_alert_keys(self):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            rows = connection.execute("SELECT alert_key FROM alerts").fetchall()
        return {row[0] for row in rows}

    def unacknowledged_alerts(self):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT alert_key, patient_id, patient_name, test_name,
                       flagged_value, reason, created_at
                FROM alerts
                WHERE status = 'UNACKNOWLEDGED'
                ORDER BY created_at, alert_key
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_critical_alerts(self, limit=8):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("The critical alert history limit must be a positive integer.")

        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT patient_name, test_name, flagged_value, reason,
                       created_at, status
                FROM alerts
                WHERE reason LIKE 'LOW (%' OR reason LIKE 'HIGH (%'
                ORDER BY created_at DESC, alert_key DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_alert(
        self,
        alert_key,
        patient_id,
        patient_name,
        test_name,
        flagged_value,
        reason,
        created_at,
    ):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO alerts (
                    alert_key, patient_id, patient_name, test_name,
                    flagged_value, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_key,
                    patient_id,
                    patient_name,
                    test_name,
                    flagged_value,
                    reason,
                    created_at,
                ),
            )
        return cursor.rowcount == 1

    def acknowledge(self, alert_key, acknowledged_at):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE alerts
                SET status = 'ACKNOWLEDGED', acknowledged_at = ?
                WHERE alert_key = ? AND status = 'UNACKNOWLEDGED'
                """,
                (acknowledged_at, alert_key),
            )
        return cursor.rowcount == 1

    def acknowledge_many(self, alert_keys, acknowledged_at):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.executemany(
                """
                UPDATE alerts
                SET status = 'ACKNOWLEDGED', acknowledged_at = ?
                WHERE alert_key = ? AND status = 'UNACKNOWLEDGED'
                """,
                ((acknowledged_at, alert_key) for alert_key in alert_keys),
            )

    def acknowledged_glucose_keys(self):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            rows = connection.execute(
                "SELECT record_key FROM glucose_acknowledgments"
            ).fetchall()
        return {row[0] for row in rows}

    def acknowledge_glucose(self, record_key, acknowledged_at):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO glucose_acknowledgments (
                    record_key, acknowledged_at
                ) VALUES (?, ?)
                """,
                (record_key, acknowledged_at),
            )
        return cursor.rowcount == 1

    def acknowledge_glucose_many(self, record_keys, acknowledged_at):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO glucose_acknowledgments (
                    record_key, acknowledged_at
                ) VALUES (?, ?)
                """,
                ((record_key, acknowledged_at) for record_key in record_keys),
            )

    def get_or_create_result_received_at(self, record, observed_at):
        return self.get_or_create_result_received_at_many(
            [record], observed_at
        )[record]

    def get_or_create_result_received_at_many(self, records, observed_at):
        records_by_key = {
            json.dumps(record, ensure_ascii=False, separators=(",", ":")): record
            for record in records
        }
        if not records_by_key:
            return {}

        record_keys = list(records_by_key)
        received_at_by_key = {}
        observed_at_text = observed_at.isoformat(timespec="seconds")
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO result_received_times (
                    record_key, received_at
                ) VALUES (?, ?)
                """,
                ((record_key, observed_at_text) for record_key in record_keys),
            )
            for start in range(0, len(record_keys), 500):
                batch = record_keys[start:start + 500]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"""
                    SELECT record_key, received_at
                    FROM result_received_times
                    WHERE record_key IN ({placeholders})
                    """,
                    batch,
                ).fetchall()
                received_at_by_key.update(rows)

        return {
            records_by_key[record_key]: datetime.fromisoformat(received_at)
            for record_key, received_at in received_at_by_key.items()
        }
