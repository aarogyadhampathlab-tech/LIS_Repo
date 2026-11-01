import sqlite3
from contextlib import closing
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
