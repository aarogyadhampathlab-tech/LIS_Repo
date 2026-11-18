import math
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import TEST_MAP
from core.alert_rules import save_alert_rules


def build_alert_rule_catalog(alert_rules, test_names):
    catalog = {test_name: dict(rule) for test_name, rule in alert_rules.items()}
    for test_name in sorted(set(test_names), key=str.casefold):
        catalog.setdefault(
            test_name,
            {"enabled": False, "unit": ""},
        )
    return catalog


class AlertSettingsPage(QWidget):
    def __init__(self, alert_rules, on_saved):
        super().__init__()
        self.configured_test_names = set(alert_rules)
        self.alert_rules = build_alert_rule_catalog(
            alert_rules, TEST_MAP.values()
        )
        self.on_saved = on_saved
        self._build_ui()
        self._populate_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Alert settings")
        title.setStyleSheet(
            "color: #1D3148; font-size: 16pt; font-weight: 750;"
        )
        subtitle = QLabel(
            "Set per-test numeric thresholds. Missing-result, technical-error, "
            "and glucose notifications are unchanged."
        )
        subtitle.setStyleSheet("color: #687B91; font-size: 9pt;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("mainResultsPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(13, 11, 13, 11)
        panel_layout.setSpacing(10)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["THRESHOLD ALERT", "TEST", "LOW", "HIGH", "UNIT"]
        )
        self.table.setStyleSheet(
            "QTableWidget { color: #1D3148; }"
            "QTableWidget QLineEdit { color: #1D3148; background: #FFFFFF;"
            " border: 1px solid #2F80E2; border-radius: 4px;"
            " padding: 1px 5px; selection-background-color: #DCEAFF;"
            " selection-color: #1D3148; }"
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 145)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 130)
        panel_layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.save_status = QLabel("")
        self.save_status.setStyleSheet(
            "color: #23845B; font-size: 8pt;"
        )
        footer.addWidget(self.save_status, 1)
        self.save_button = QPushButton("Save settings")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self._save_changes)
        footer.addWidget(self.save_button)
        panel_layout.addLayout(footer)
        layout.addWidget(panel, 1)

    def _populate_table(self):
        self.table.setRowCount(len(self.alert_rules))
        for row, (test_name, rule) in enumerate(self.alert_rules.items()):
            enabled = QTableWidgetItem()
            enabled.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            enabled.setCheckState(
                Qt.CheckState.Checked
                if rule.get("enabled", True)
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, 0, enabled)

            name_item = QTableWidgetItem(test_name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_item.setForeground(QColor("#1D3148"))
            self.table.setItem(row, 1, name_item)

            for column, bound in ((2, "low"), (3, "high")):
                value = rule.get(bound)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setForeground(QColor("#1D3148"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)

            unit_item = QTableWidgetItem(rule.get("unit", ""))
            unit_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 4, unit_item)

    @staticmethod
    def _parse_threshold(value, test_name, bound):
        text = value.strip()
        if not text:
            return None
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
            raise ValueError(f"The {bound} threshold for {test_name!r} must be numeric.")

        number = float(text)
        if not math.isfinite(number):
            raise ValueError(f"The {bound} threshold for {test_name!r} must be finite.")
        return int(number) if number.is_integer() and "." not in text else number

    def _save_changes(self):
        updated_rules = {}
        try:
            for row, test_name in enumerate(self.alert_rules):
                enabled = self.table.item(row, 0).checkState() == Qt.CheckState.Checked
                rule = {
                    "enabled": enabled,
                    "unit": self.alert_rules[test_name].get("unit", ""),
                }
                for column, bound in ((2, "low"), (3, "high")):
                    value = self._parse_threshold(
                        self.table.item(row, column).text(), test_name, bound
                    )
                    if value is not None:
                        rule[bound] = value
                if (
                    enabled
                    or "low" in rule
                    or "high" in rule
                    or test_name in self.configured_test_names
                ):
                    updated_rules[test_name] = rule

            saved_rules = save_alert_rules(updated_rules)
            self.configured_test_names = set(saved_rules)
            self.alert_rules = build_alert_rule_catalog(
                saved_rules, TEST_MAP.values()
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Invalid alert settings", str(error))
            return

        self.on_saved(self.alert_rules)
        self.save_status.setText("Saved and applied immediately.")
