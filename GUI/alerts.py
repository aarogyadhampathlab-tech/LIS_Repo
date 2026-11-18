import hashlib
import io
import json
import math
import re
import struct
import wave
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.alert_rules import find_critical_range
from config import CRITICAL_RANGES, TECHNICAL_ERROR_KEYWORDS
from GUI.common import COLORS, DraggableDialog

try:
    import winsound
except ImportError:
    winsound = None

class AlertPanelMixin:
    def _build_alert_card(self):
        self.alert_card = DraggableDialog(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint,
        )
        self.alert_card.setObjectName("criticalAlertPanel")
        self.alert_card.setWindowTitle("Critical LIS alerts")
        self.alert_card.setWindowIcon(self.windowIcon())
        self.alert_card.setMinimumWidth(390)
        self.alert_card.setMaximumWidth(440)
        self.alert_card.setStyleSheet(
            f"QDialog#criticalAlertPanel {{ background: {COLORS['surface']}; "
            f"border: 1px solid {COLORS['offline']}; border-radius: 12px; }}"
        )
        panel_layout = QVBoxLayout(self.alert_card)
        panel_layout.setContentsMargins(10, 8, 10, 10)
        panel_layout.setSpacing(7)

        self.alert_heading = QLabel("CRITICAL ALERTS")
        self.alert_heading.setStyleSheet(
            f"color: {COLORS['offline']}; font-size: 10pt; font-weight: 900;"
        )
        self.alert_queue_label = QLabel()
        self.alert_queue_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 8pt;")
        self.alert_panel_header = QFrame()
        header_layout = QHBoxLayout(self.alert_panel_header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.addWidget(self.alert_heading)
        header_layout.addStretch(1)
        header_layout.addWidget(self.alert_queue_label)
        panel_layout.addWidget(self.alert_panel_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(330)
        self.alert_panel_body = QWidget()
        self.alert_panel_body_layout = QVBoxLayout(self.alert_panel_body)
        self.alert_panel_body_layout.setContentsMargins(0, 0, 0, 0)
        self.alert_panel_body_layout.setSpacing(6)
        scroll.setWidget(self.alert_panel_body)
        panel_layout.addWidget(scroll)
        self.alert_panel_header.installEventFilter(self.alert_card)
        self.alert_card.add_drag_area(self.alert_heading)
        self.alert_card.add_drag_area(self.alert_queue_label)
        self.alert_card.hide()

        shadow = QGraphicsDropShadowEffect(self.alert_card)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.alert_card.setGraphicsEffect(shadow)

    def _extract_numeric_result(self, result):
        if not result:
            return None
        match = re.search(r"[+-]?\d+(?:[.,]\d+)?", result.strip())
        if not match:
            return None
        try:
            return float(match.group().replace(",", "."))
        except ValueError:
            return None

    def _is_technical_error(self, result):
        if not result:
            return False
        lowered = result.strip().lower()
        return any(keyword in lowered for keyword in TECHNICAL_ERROR_KEYWORDS)

    def _alert_reason(self, test_name, result):
        normalized_result = result.strip().casefold() if result else ""
        if (
            not normalized_result
            or normalized_result == "missing_result"
            or "no result" in normalized_result
            or "no-result" in normalized_result
        ):
            return "MISSING_RESULT"

        if self._is_technical_error(result):
            return "TECHNICAL ERROR"

        numeric = self._extract_numeric_result(result)
        if numeric is None:
            return None

        alert_rules = getattr(self, "alert_rules", CRITICAL_RANGES)
        range_def = find_critical_range(test_name, alert_rules)
        if not range_def or not range_def.get("enabled", True):
            return None

        low = range_def.get("low")
        high = range_def.get("high")
        if low is not None and numeric < low:
            return f"LOW (< {low})"
        if high is not None and numeric > high:
            return f"HIGH (> {high})"
        return None

    def _check_record_alert(
        self, patient_id, patient_name, test_name, result, refresh=True
    ):
        reason = self._alert_reason(test_name, result)
        if reason is None:
            return False

        identity = json.dumps(
            [patient_id, patient_name, test_name, result, reason],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        alert_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        if alert_key in self.alerted_records:
            return False

        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.alert_store.create_alert(
                alert_key,
                patient_id,
                patient_name,
                test_name,
                result,
                reason,
                created_at,
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Alert could not be saved",
                f"The alert was not persisted and will not be shown as active.\n\n{error}",
            )
            return False

        self.alerted_records.add(alert_key)
        if refresh:
            self._refresh_active_alerts()
        return True

    def _refresh_active_alerts(self):
        self.active_alerts = self.alert_store.unacknowledged_alerts()
        while self.alert_panel_body_layout.count():
            item = self.alert_panel_body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.active_alerts:
            self.alert_card.hide()
            self.alert_sound_timer.stop()
            if winsound:
                winsound.PlaySound(None, winsound.SND_PURGE)
            return

        display_alerts = self._group_alerts_for_display(self.active_alerts)
        self.alert_heading.setText("CRITICAL ALERTS")
        self.alert_queue_label.setText(f"{len(display_alerts)} active")
        for alert in display_alerts:
            self.alert_panel_body_layout.addWidget(self._build_critical_alert_row(alert))

        self.alert_panel_body_layout.addStretch(1)
        self.alert_card.adjustSize()
        self._position_critical_alert_panel()
        self.alert_card.show()
        self.alert_card.raise_()
        if not self.alert_sound_timer.isActive():
            self._play_alert_sound()
            self.alert_sound_timer.start()

    @staticmethod
    def _group_alerts_for_display(alerts):
        display_alerts = []
        missing_groups = {}
        for alert in alerts:
            if alert["reason"] != "MISSING_RESULT":
                display_alerts.append(alert)
                continue

            patient_id = str(alert["patient_id"] or "").strip()
            patient_name = str(alert["patient_name"] or "").strip()
            if patient_id and patient_id.casefold() != "unknown":
                patient_key = ("uhid", patient_id.casefold())
            elif patient_name and patient_name.casefold() != "unknown":
                patient_key = ("name", patient_name.casefold())
            else:
                patient_key = ("alert", alert["alert_key"])

            group = missing_groups.get(patient_key)
            if group is None:
                group = dict(alert)
                group["alert_keys"] = []
                group["missing_tests"] = []
                missing_groups[patient_key] = group
                display_alerts.append(group)

            group["alert_keys"].append(alert["alert_key"])
            if alert["test_name"] not in group["missing_tests"]:
                group["missing_tests"].append(alert["test_name"])

        return display_alerts

    def _build_critical_alert_row(self, alert):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {COLORS['surface_alt']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(4)

        patient_id = alert["patient_id"]
        patient_name = alert["patient_name"]
        if patient_id and patient_id != "UNKNOWN":
            patient_label = f"UHID {patient_id}"
            if patient_name and patient_name != "UNKNOWN":
                patient_label += f"  ·  {patient_name}"
        else:
            patient_label = patient_name if patient_name != "UNKNOWN" else "UNKNOWN"
        patient = QLabel(patient_label)
        patient.setTextFormat(Qt.TextFormat.PlainText)
        patient.setWordWrap(True)
        patient.setStyleSheet(
            "color: #FFFFFF; font-size: 9pt; font-weight: 700; border: none;"
        )
        is_missing_result = alert["reason"] == "MISSING_RESULT"
        if is_missing_result:
            test_text = "No result for: " + ", ".join(alert["missing_tests"])
        else:
            test_text = f"{alert['test_name']}  ·  {alert['reason']}"
        test = QLabel(test_text)
        test.setTextFormat(Qt.TextFormat.PlainText)
        test.setWordWrap(True)
        if is_missing_result:
            test.setStyleSheet(
                f"color: {COLORS['muted']}; background: {COLORS['surface']}; "
                "border: none; border-radius: 5px; padding: 4px 7px; font-size: 7pt;"
            )
        else:
            test.setStyleSheet(
                f"color: {COLORS['muted']}; font-size: 8pt; border: none;"
            )
        timestamp = QLabel(
            datetime.fromisoformat(alert["created_at"])
            .astimezone()
            .strftime("%m/%d/%Y %I:%M:%S %p")
        )
        timestamp.setStyleSheet(
            f"color: {COLORS['muted']}; font-size: 7pt; border: none;"
        )
        layout.addWidget(patient)
        layout.addWidget(test)
        if not is_missing_result:
            value = QLabel(alert["flagged_value"])
            value.setTextFormat(Qt.TextFormat.PlainText)
            value.setWordWrap(True)
            value.setStyleSheet(
                "color: #FFFFFF; background: #8F2029; border: 1px solid #FF6975;"
                " border-radius: 5px; padding: 5px 8px; font-size: 12pt; font-weight: 900;"
            )
            layout.addWidget(value)

        footer = QHBoxLayout()
        footer.addWidget(timestamp, 1)
        acknowledge = QPushButton("Acknowledge")
        acknowledge.setMinimumHeight(28)
        acknowledge.setStyleSheet(
            "QPushButton { color: #FFFFFF; background: #7A252B; "
            "border: 1px solid #FF6975; border-radius: 6px; padding: 5px 9px; "
            "font-size: 8pt; font-weight: 700; }"
            "QPushButton:hover { background: #9C3038; }"
        )
        if is_missing_result:
            acknowledge.clicked.connect(
                lambda checked=False, keys=tuple(alert["alert_keys"]):
                    self._acknowledge_missing_alerts(keys)
            )
        else:
            acknowledge.clicked.connect(
                lambda checked=False, key=alert["alert_key"]: self._acknowledge_alert(key)
            )
        footer.addWidget(acknowledge)
        layout.addLayout(footer)
        return card

    def _position_critical_alert_panel(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        bounds = screen.availableGeometry()
        self.alert_card.adjustSize()
        self.alert_card.move(
            bounds.right() - self.alert_card.width() - 18,
            bounds.top() + 72,
        )

    def _play_alert_sound(self):
        if winsound:
            winsound.PlaySound(
                str(self.emergency_alert_sound),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
        else:
            QApplication.beep()

    @staticmethod
    def _build_emergency_alert_sound():
        sample_rate = 12000
        segments = ((760, 1160), (1160, 760), (760, 1160), (1160, 760))
        samples = []
        samples_per_segment = int(sample_rate * 0.28)
        for start_frequency, end_frequency in segments:
            for index in range(samples_per_segment):
                progress = index / samples_per_segment
                frequency = start_frequency + (end_frequency - start_frequency) * progress
                envelope = min(1.0, index / 180, (samples_per_segment - index) / 180)
                tone = math.sin(2 * math.pi * frequency * index / sample_rate)
                samples.append(int(26000 * envelope * tone))

        audio = io.BytesIO()
        with wave.open(audio, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(
                b"".join(struct.pack("<h", sample) for sample in samples)
            )
        return audio.getvalue()

    def _trigger_demo_alert(self):
        demo_id = datetime.now().astimezone().strftime("DEMO-%Y%m%d-%H%M%S-%f")
        self._check_record_alert(
            demo_id,
            "DEMO PATIENT (TEST ONLY)",
            "SODIUM (Na+)",
            "110 mmol/L (DEMO)",
        )

    def _trigger_demo_missing_alert(self):
        demo_id = datetime.now().astimezone().strftime("DEMO-MISSING-%Y%m%d-%H%M%S-%f")
        self._check_record_alert(
            demo_id,
            "DEMO PATIENT (TEST ONLY)",
            "GLUCOSE",
            "MISSING_RESULT",
        )

    def _acknowledge_current_alert(self):
        if not self.active_alerts:
            return
        self._acknowledge_alert(self.active_alerts[0]["alert_key"])

    def _acknowledge_alert(self, alert_key):
        acknowledged_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.alert_store.acknowledge(alert_key, acknowledged_at)
            self._refresh_active_alerts()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Acknowledgment failed",
                f"The alert remains active because acknowledgment was not saved.\n\n{error}",
            )

    def _acknowledge_missing_alerts(self, alert_keys):
        acknowledged_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.alert_store.acknowledge_many(alert_keys, acknowledged_at)
            self._refresh_active_alerts()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Acknowledgment failed",
                "The missing-result alerts remain active because acknowledgment "
                f"was not saved.\n\n{error}",
            )
