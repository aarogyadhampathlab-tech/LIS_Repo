import csv
import re
import time

from PySide6.QtCore import QEvent, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    import winsound
except ImportError:
    winsound = None

try:
    from config import CRITICAL_RANGES, REPORT_PATH, TECHNICAL_ERROR_KEYWORDS
except ImportError:
    REPORT_PATH = "lab_reports.csv"
    CRITICAL_RANGES = {}
    TECHNICAL_ERROR_KEYWORDS = []


COLORS = {
    "background": "#11191D",
    "surface": "#182327",
    "surface_alt": "#1E2D31",
    "border": "#2C3E42",
    "text": "#E8F0ED",
    "muted": "#96A9A4",
    "accent": "#75C7B3",
    "accent_dark": "#245E55",
    "accent_soft": "#243B3A",
    "online": "#77C99A",
    "offline": "#E58B83",
    "warning": "#E7BB70",
}


class DraggableDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_offset = None

    def add_drag_area(self, widget):
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, watched, event):
        if isinstance(event, QMouseEvent):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif (
                event.type() == QEvent.Type.MouseMove
                and self._drag_offset is not None
                and event.buttons() & Qt.MouseButton.LeftButton
            ):
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_offset = None
        return super().eventFilter(watched, event)


class LabMark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(COLORS["accent"]), 2.2, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

        flask = QPainterPath()
        flask.moveTo(21, 9)
        flask.lineTo(33, 9)
        flask.moveTo(24, 9)
        flask.lineTo(24, 22)
        flask.lineTo(15, 39)
        flask.quadTo(14, 43, 19, 43)
        flask.lineTo(36, 43)
        flask.quadTo(41, 43, 39, 39)
        flask.lineTo(30, 22)
        flask.lineTo(30, 9)
        painter.drawPath(flask)

        liquid = QPainterPath()
        liquid.moveTo(19, 35)
        liquid.lineTo(35, 35)
        liquid.lineTo(39, 41)
        liquid.quadTo(40, 43, 36, 43)
        liquid.lineTo(19, 43)
        liquid.quadTo(15, 43, 16, 41)
        liquid.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS["accent"]))
        painter.drawPath(liquid)
        painter.setBrush(QColor(COLORS["text"]))
        painter.drawEllipse(23, 31, 3, 3)
        painter.drawEllipse(30, 27, 2.5, 2.5)


def make_app_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(COLORS["surface_alt"]))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 15, 15)
    painter.setPen(QPen(QColor(COLORS["accent"]), 3, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    path = QPainterPath()
    path.moveTo(25, 14)
    path.lineTo(39, 14)
    path.moveTo(28, 14)
    path.lineTo(28, 29)
    path.lineTo(17, 48)
    path.quadTo(16, 52, 21, 52)
    path.lineTo(43, 52)
    path.quadTo(48, 52, 46, 48)
    path.lineTo(36, 29)
    path.lineTo(36, 14)
    painter.drawPath(path)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(COLORS["accent"]))
    painter.drawRoundedRect(20, 42, 24, 8, 3, 3)
    painter.end()
    return QIcon(pixmap)


def create_application(arguments):
    application = QApplication(arguments)
    application.setApplicationName("LIS Lab Monitor")
    return application


class LabApp(QMainWindow):
    records_received = Signal(object)
    network_status_received = Signal(bool, str)
    activity_received = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LIS Lab Monitor")
        self.setWindowIcon(make_app_icon())
        self.resize(1240, 860)
        self.setMinimumSize(940, 650)
        self.setStyleSheet(self._application_stylesheet())

        self.all_records = []
        self.notified_records = set()
        self.alerted_records = set()
        self.notification_window = None
        self.notification_rows = {}
        self.notification_counter = 0
        self.notification_collapsed = False
        self.notification_maximized = False
        self.records_received.connect(self._append_records)
        self.network_status_received.connect(self._set_network_status)
        self.activity_received.connect(self._append_activity)

        self._build_interface()
        self.filter_data()

    def _application_stylesheet(self):
        return f"""
            QWidget {{
                color: {COLORS['text']};
                font-family: "Segoe UI";
                font-size: 10pt;
            }}
            QMainWindow, QWidget#root {{ background: {COLORS['background']}; }}
            QDialog#glucoseNotification {{ background: transparent; border: none; }}
            QFrame#notificationShell {{
                background: transparent;
                border: 1px solid rgba(117, 199, 179, 100);
                border-radius: 18px;
            }}
            QFrame#hero {{
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #19383A, stop:0.55 #1C3437, stop:1 #254D46);
            }}
            QFrame#surface {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QLineEdit {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 12px;
                selection-background-color: {COLORS['accent_dark']};
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
            QTreeWidget {{
                background: {COLORS['surface']};
                alternate-background-color: #1A282C;
                border: none;
                outline: none;
                selection-background-color: {COLORS['accent_soft']};
                selection-color: {COLORS['text']};
                padding: 8px;
            }}
            QTreeWidget::item {{ min-height: 30px; padding: 3px 5px; }}
            QTreeWidget::item:hover {{ background: #213337; }}
            QHeaderView::section {{
                color: {COLORS['muted']};
                background: {COLORS['surface_alt']};
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                padding: 11px 12px;
                font-size: 9pt;
                font-weight: 600;
            }}
            QPlainTextEdit {{
                color: {COLORS['muted']};
                background: {COLORS['surface']};
                border: none;
                padding: 10px;
                selection-background-color: {COLORS['accent_dark']};
                font-family: "Cascadia Code", "Consolas";
                font-size: 9pt;
            }}
            QPushButton {{
                color: {COLORS['text']};
                background: {COLORS['surface_alt']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 9px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #2A3B3E; border-color: #49635E; }}
            QPushButton:pressed {{ background: {COLORS['accent_dark']}; }}
            QPushButton#primary {{
                color: #F2F8F5;
                border: 1px solid #478C7D;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #347F70, stop:1 #245E55);
                padding: 10px 17px;
            }}
            QPushButton#primary:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #409583, stop:1 #2C7166);
            }}
            QMenu {{
                color: {COLORS['text']};
                background: {COLORS['surface_alt']};
                border: 1px solid {COLORS['border']};
                padding: 5px;
            }}
            QMenu::item {{ padding: 8px 22px; border-radius: 5px; }}
            QMenu::item:selected {{ background: {COLORS['accent_soft']}; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: #405653;
                border-radius: 4px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {COLORS['accent_dark']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QMessageBox {{ background: {COLORS['surface']}; }}
        """

    def _build_interface(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(15)

        layout.addWidget(self._build_header())
        layout.addLayout(self._build_search_row())
        layout.addWidget(self._build_results(), 1)
        layout.addLayout(self._build_footer())

    def _build_header(self):
        header = QFrame()
        header.setObjectName("hero")
        row = QHBoxLayout(header)
        row.setContentsMargins(20, 15, 20, 15)
        row.setSpacing(14)

        row.addWidget(LabMark())
        title_stack = QVBoxLayout()
        title_stack.setSpacing(3)
        title = QLabel("LIS LAB MONITOR")
        title.setStyleSheet("font-size: 19pt; font-weight: 700; color: #F0F6F3;")
        subtitle = QLabel("LABORATORY RESULTS  /  LIVE MONITORING")
        subtitle.setStyleSheet(f"font-size: 8pt; font-weight: 600; color: {COLORS['muted']};")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        row.addLayout(title_stack)
        row.addStretch(1)

        self.connection_dot = QLabel("●")
        self.connection_dot.setStyleSheet(f"color: {COLORS['offline']}; font-size: 10pt;")
        row.addWidget(self.connection_dot)
        self.connection_label = QLabel("OFFLINE")
        self.connection_label.setStyleSheet(
            f"color: {COLORS['offline']}; font-size: 9pt; font-weight: 700;"
        )
        row.addWidget(self.connection_label)
        self.alert_label = QLabel("")
        self.alert_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.alert_label.setWordWrap(True)
        self.alert_label.setMaximumWidth(310)
        self.alert_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 600;")
        row.addWidget(self.alert_label)
        return header

    def _build_search_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        self.patient_search = QLineEdit()
        self.patient_search.setPlaceholderText("⌕   Search patients")
        self.patient_search.setClearButtonEnabled(True)
        self.patient_search.setToolTip("Filter results by patient name")
        self.patient_search.textChanged.connect(self.filter_data)

        self.test_search = QLineEdit()
        self.test_search.setPlaceholderText("⌕   Search tests")
        self.test_search.setClearButtonEnabled(True)
        self.test_search.setToolTip("Filter results by test name")
        self.test_search.textChanged.connect(self.filter_data)

        row.addWidget(self.patient_search, 1)
        row.addWidget(self.test_search, 1)
        self.result_count = QLabel("0 PATIENTS  ·  0 RESULTS")
        self.result_count.setMinimumWidth(190)
        self.result_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.result_count.setStyleSheet(f"color: {COLORS['muted']}; font-size: 8pt; font-weight: 600;")
        row.addWidget(self.result_count)
        return row

    def _build_results(self):
        panel = QFrame()
        panel.setObjectName("surface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["PATIENT", "TEST TYPE", "RESULT"])
        self.tree.setColumnWidth(0, 390)
        self.tree.setColumnWidth(1, 360)
        self.tree.setColumnWidth(2, 220)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(18)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree)
        return panel

    def _build_footer(self):
        footer = QHBoxLayout()
        footer.setSpacing(12)

        activity_panel = QFrame()
        activity_panel.setObjectName("surface")
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(12, 8, 12, 8)
        activity_layout.setSpacing(5)
        activity_heading = QLabel("FILE ACTIVITY")
        activity_heading.setStyleSheet(f"color: {COLORS['muted']}; font-size: 8pt; font-weight: 700;")
        activity_layout.addWidget(activity_heading)
        self.activity_text = QPlainTextEdit()
        self.activity_text.setReadOnly(True)
        self.activity_text.setMaximumBlockCount(1200)
        self.activity_text.setMinimumHeight(96)
        self.activity_text.setPlaceholderText("Waiting for file activity…")
        activity_layout.addWidget(self.activity_text)

        save_button = QPushButton("Save report and clear")
        save_button.setObjectName("primary")
        save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        save_button.setToolTip("Append visible results to the report CSV and clear the current list")
        save_button.clicked.connect(self.save_to_csv)
        save_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        footer.addWidget(activity_panel, 1)
        footer.addWidget(save_button, 0, Qt.AlignmentFlag.AlignBottom)
        return footer

    def queue_activity_text(self, text):
        self.activity_received.emit(text)

    @Slot(str)
    def _append_activity(self, text):
        self.activity_text.moveCursor(self.activity_text.textCursor().MoveOperation.End)
        self.activity_text.insertPlainText(text)
        self.activity_text.ensureCursorVisible()

    def add_records(self, records):
        self.records_received.emit(records)

    @Slot(object)
    def _append_records(self, records):
        for record in records:
            self.all_records.append(record)
            self._check_record_alert(*record)
        self.filter_data()
        QApplication.beep()

    def filter_data(self, *args):
        patient_query = self.patient_search.text().strip().lower()
        test_query = self.test_search.text().strip().lower()
        grouped = {}
        visible_result_count = 0

        for patient_name, test_name, result in self.all_records:
            if patient_query not in patient_name.lower() or test_query not in test_name.lower():
                continue
            grouped.setdefault(patient_name, []).append((test_name, result))
            visible_result_count += 1

        self.tree.clear()
        standard_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        for patient_name, tests in grouped.items():
            patient_item = QTreeWidgetItem([patient_name, "", ""])
            patient_item.setData(0, Qt.ItemDataRole.UserRole, patient_name)
            patient_item.setIcon(0, standard_icon)
            patient_item.setForeground(0, QColor(COLORS["text"]))
            patient_item.setExpanded(False)
            self.tree.addTopLevelItem(patient_item)

            for test_name, result in tests:
                test_item = QTreeWidgetItem(["", test_name, result])
                test_item.setForeground(1, QColor(COLORS["muted"]))
                patient_item.addChild(test_item)

        self.result_count.setText(
            f"{len(grouped)} PATIENTS  ·  {visible_result_count} RESULTS"
        )

        for patient_name, tests in grouped.items():
            glucose_result = None
            glucose_test = None
            for test_name, result in tests:
                if "glucose" in test_name.lower():
                    glucose_result = result
                    glucose_test = test_name

            if glucose_result:
                record_key = (patient_name, "glucose", glucose_result)
                if record_key not in self.notified_records:
                    self._show_glucose_notification(
                        patient_name, glucose_test or "GLUCOSE", glucose_result
                    )
                    self.notified_records.add(record_key)

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item is None:
            return
        self.tree.setCurrentItem(item)
        menu = QMenu(self)
        delete_action = menu.addAction("Delete selected patient")
        delete_action.triggered.connect(self.delete_individual)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def delete_individual(self):
        item = self.tree.currentItem()
        if item is None:
            return
        patient_item = item if item.parent() is None else item.parent()
        patient_name = patient_item.data(0, Qt.ItemDataRole.UserRole)
        if not patient_name:
            return
        self.all_records = [record for record in self.all_records if record[0] != patient_name]
        self.notified_records = {
            record for record in self.notified_records if record[0] != patient_name
        }
        self.filter_data()

    def update_network_status(self, online, path):
        self.network_status_received.emit(online, path)

    @Slot(bool, str)
    def _set_network_status(self, online, path):
        color = COLORS["online"] if online else COLORS["offline"]
        status = "ONLINE" if online else "OFFLINE"
        self.connection_dot.setStyleSheet(f"color: {color}; font-size: 10pt;")
        self.connection_label.setText(status)
        self.connection_label.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: 700;")
        self.connection_label.setToolTip(path)

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

    def _show_alert(self, patient_name, test_name, result, alert_reason):
        if winsound:
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        self.alert_label.setText(f"{patient_name}  ·  {test_name}  ·  {alert_reason}")
        self.alert_label.setStyleSheet(f"color: {COLORS['offline']}; font-weight: 700;")
        QTimer.singleShot(10000, lambda: self.alert_label.clear())

    def _check_record_alert(self, patient_name, test_name, result):
        alert_key = (patient_name, test_name, result)
        if alert_key in self.alerted_records:
            return

        if self._is_technical_error(result):
            self._show_alert(patient_name, test_name, result, "TECHNICAL ERROR")
            self.alerted_records.add(alert_key)
            return

        numeric = self._extract_numeric_result(result)
        if numeric is None:
            return

        range_def = CRITICAL_RANGES.get(test_name)
        if not range_def:
            return

        low = range_def.get("low")
        high = range_def.get("high")
        if low is not None and numeric < low:
            self._show_alert(patient_name, test_name, result, f"LOW (< {low})")
            self.alerted_records.add(alert_key)
        elif high is not None and numeric > high:
            self._show_alert(patient_name, test_name, result, f"HIGH (> {high})")
            self.alerted_records.add(alert_key)

    def _show_glucose_notification(self, patient_name, test_name, result):
        if self.notification_window is None:
            dialog = DraggableDialog(
                None,
                Qt.WindowType.Window
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.FramelessWindowHint,
            )
            dialog.setObjectName("glucoseNotification")
            dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            dialog.setWindowTitle("Glucose alerts")
            dialog.setWindowIcon(self.windowIcon())
            dialog.setMinimumWidth(540)
            dialog.setMaximumWidth(760)
            dialog.setStyleSheet(self._application_stylesheet())
            self.notification_window = dialog
            self.notification_collapsed = False
            self.notification_maximized = False
            dialog_layout = QVBoxLayout(dialog)
            dialog_layout.setContentsMargins(0, 0, 0, 0)
            dialog_layout.setSpacing(0)
            self.notification_shell = QFrame()
            self.notification_shell.setObjectName("notificationShell")
            dialog_layout.addWidget(self.notification_shell)
            self.notification_layout = QVBoxLayout(self.notification_shell)
            self.notification_layout.setContentsMargins(10, 8, 10, 8)
            self.notification_layout.setSpacing(5)

            self.notification_header = QFrame()
            self.notification_header.setObjectName("notificationHeader")
            header = QHBoxLayout(self.notification_header)
            header.setContentsMargins(5, 2, 3, 2)
            header.setSpacing(6)
            self.notification_heading = QLabel("GLUCOSE ALERTS")
            self.notification_heading.setStyleSheet(
                f"color: {COLORS['accent']}; font-size: 9pt; font-weight: 700;"
            )
            header.addWidget(self.notification_heading)
            header.addStretch(1)

            self.notification_minimize_button = self._notification_control(
                "−", "Minimize to a small circle", self._minimize_glucose_notifications
            )
            self.notification_delete_button = QPushButton()
            self.notification_delete_button.setFixedSize(27, 26)
            self.notification_delete_button.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
            )
            self.notification_delete_button.setToolTip("Clear all glucose alerts")
            self.notification_delete_button.setAccessibleName("Clear all glucose alerts")
            self.notification_delete_button.setStyleSheet(
                f"QPushButton {{ color: {COLORS['muted']}; background: transparent;"
                f" border: 1px solid {COLORS['border']}; border-radius: 7px; padding: 3px; }}"
                f"QPushButton:hover {{ background: {COLORS['accent_soft']}; }}"
            )
            self.notification_delete_button.clicked.connect(self._clear_glucose_notifications)
            header.addWidget(self.notification_minimize_button)
            header.addWidget(self.notification_delete_button)
            self.notification_layout.addWidget(self.notification_header)

            self.notification_body = QWidget()
            self.notification_body_layout = QVBoxLayout(self.notification_body)
            self.notification_body_layout.setContentsMargins(0, 0, 0, 0)
            self.notification_body_layout.setSpacing(5)
            self.notification_layout.addWidget(self.notification_body)

            self.notification_bubble = QPushButton("1")
            self.notification_bubble.setFixedSize(48, 48)
            self.notification_bubble.setToolTip("Restore glucose alerts")
            self.notification_bubble.setAccessibleName("Restore glucose alert panel")
            self.notification_bubble.setStyleSheet(
                f"QPushButton {{ color: {COLORS['text']};"
                f" background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                f" stop:0 {COLORS['accent_dark']}, stop:1 #367D70);"
                f" border: 2px solid {COLORS['accent']}; border-radius: 24px;"
                " font-size: 11pt; font-weight: 700; padding: 0; }"
                f"QPushButton:hover {{ border-color: {COLORS['text']}; }}"
            )
            self.notification_bubble.clicked.connect(self._restore_glucose_notifications)
            dialog.add_drag_area(self.notification_header)
            dialog.add_drag_area(self.notification_bubble)
            self.notification_layout.addWidget(
                self.notification_bubble, 0, Qt.AlignmentFlag.AlignCenter
            )
            self.notification_bubble.hide()

            shadow = QGraphicsDropShadowEffect(dialog)
            shadow.setBlurRadius(28)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 120))
            dialog.setGraphicsEffect(shadow)

        notification_id = self.notification_counter
        self.notification_counter += 1
        self.notification_heading.setText(f"GLUCOSE ALERTS  ·  {len(self.notification_rows) + 1}")

        alert_card = QFrame()
        alert_card.setObjectName("notificationCard")
        alert_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['surface_alt']}; color: {COLORS['text']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 10px; }}"
        )
        card_layout = QHBoxLayout(alert_card)
        card_layout.setContentsMargins(9, 6, 7, 6)
        card_layout.setSpacing(7)

        patient_label = QLabel(patient_name)
        patient_label.setTextFormat(Qt.TextFormat.PlainText)
        patient_label.setWordWrap(False)
        patient_label.setToolTip(patient_name)
        patient_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        patient_label.setStyleSheet(
            "color: #FFFFFF; font-size: 10pt; font-weight: 700; border: none;"
        )
        test_label = QLabel(test_name.upper())
        test_label.setTextFormat(Qt.TextFormat.PlainText)
        test_label.setWordWrap(False)
        test_label.setStyleSheet(
            "color: #B9CBC5; font-size: 8pt; font-weight: 700; border: none;"
        )
        result_label = QLabel(result)
        result_label.setTextFormat(Qt.TextFormat.PlainText)
        result_label.setWordWrap(False)
        result_label.setToolTip(result)
        result_label.setStyleSheet(
            "color: #FFD27F; font-size: 11pt; font-weight: 800; border: none;"
        )
        card_layout.addWidget(patient_label, 2)
        card_layout.addWidget(test_label, 0)
        card_layout.addWidget(result_label, 1)

        dismiss_button = QPushButton("Remove")
        dismiss_button.setFixedHeight(25)
        dismiss_button.setToolTip("Dismiss this glucose alert")
        dismiss_button.setAccessibleName(f"Dismiss glucose alert for {patient_name}")
        dismiss_button.setStyleSheet(
            f"QPushButton {{ color: {COLORS['muted']}; background: transparent;"
            f" border: none; font-size: 8pt; font-weight: 600; padding: 3px 6px; }}"
            f"QPushButton:hover {{ color: {COLORS['offline']}; background: {COLORS['border']}; }}"
        )
        dismiss_button.clicked.connect(
            lambda checked=False, item_id=notification_id:
                self._dismiss_glucose_notification(item_id)
        )
        card_layout.addWidget(dismiss_button, 0, Qt.AlignmentFlag.AlignTop)

        self.notification_rows[notification_id] = alert_card
        self.notification_bubble.setText(
            str(len(self.notification_rows)) if len(self.notification_rows) < 100 else "99+"
        )
        self.notification_body_layout.addWidget(alert_card)
        if self.notification_collapsed:
            self.notification_bubble.show()
        else:
            self.notification_body.show()
        was_visible = self.notification_window.isVisible()
        self.notification_window.adjustSize()
        self.notification_window.show()
        if not was_visible:
            self._position_glucose_notifications()
        if not self.notification_window.isMaximized():
            self.notification_window.raise_()

    def _toggle_glucose_notifications(self):
        self._minimize_glucose_notifications()

    def _notification_control(self, text, tooltip, callback):
        button = QPushButton(text)
        button.setFixedSize(27, 26)
        button.setToolTip(tooltip)
        button.setStyleSheet(
            f"QPushButton {{ color: {COLORS['muted']}; background: transparent;"
            f" border: 1px solid {COLORS['border']}; border-radius: 7px;"
            " font-size: 11pt; font-weight: 600; padding: 0; }"
            f"QPushButton:hover {{ color: {COLORS['text']}; background: {COLORS['accent_soft']}; }}"
        )
        button.clicked.connect(callback)
        return button

    def _position_glucose_notifications(self):
        screen = QApplication.primaryScreen()
        if screen is None or self.notification_window is None:
            return
        bounds = screen.availableGeometry()
        window = self.notification_window
        y_position = bounds.top() + max(70, (bounds.height() - window.height()) // 2)
        window.move(bounds.left() + 18, y_position)

    def _minimize_glucose_notifications(self):
        if self.notification_window is None:
            return
        window = self.notification_window
        window.showNormal()
        self.notification_maximized = False
        self.notification_collapsed = True
        self.notification_header.hide()
        self.notification_body.hide()
        self.notification_layout.setContentsMargins(0, 0, 0, 0)
        self.notification_layout.setSpacing(0)
        self.notification_bubble.setText(
            str(len(self.notification_rows)) if len(self.notification_rows) < 100 else "99+"
        )
        self.notification_bubble.show()
        window.setMinimumSize(54, 54)
        window.setMaximumSize(54, 54)
        window.resize(54, 54)
        self._position_glucose_notifications()

    def _restore_glucose_notifications(self):
        if self.notification_window is None:
            return
        window = self.notification_window
        self.notification_collapsed = False
        self.notification_maximized = False
        self.notification_layout.setContentsMargins(10, 8, 10, 8)
        self.notification_layout.setSpacing(5)
        window.setMinimumSize(540, 0)
        window.setMaximumSize(760, 16777215)
        self.notification_bubble.hide()
        self.notification_header.show()
        self.notification_body.show()
        window.adjustSize()
        window.showNormal()
        self._position_glucose_notifications()

    def _clear_glucose_notifications(self):
        if self.notification_window is None:
            return
        for alert_card in self.notification_rows.values():
            self.notification_body_layout.removeWidget(alert_card)
            alert_card.deleteLater()
        self.notification_rows.clear()
        self.notification_window.hide()
        self.notification_window.deleteLater()
        self.notification_window = None
        self.notification_collapsed = False
        self.notification_maximized = False

    def _dismiss_glucose_notification(self, notification_id):
        alert_card = self.notification_rows.pop(notification_id, None)
        if alert_card is None:
            return
        self.notification_body_layout.removeWidget(alert_card)
        alert_card.deleteLater()
        self.notification_heading.setText(f"GLUCOSE ALERTS  ·  {len(self.notification_rows)}")
        self.notification_bubble.setText(
            str(len(self.notification_rows)) if len(self.notification_rows) < 100 else "99+"
        )
        if not self.notification_rows and self.notification_window is not None:
            self.notification_window.hide()
            self.notification_window.deleteLater()
            self.notification_window = None

    def save_to_csv(self):
        if not self.all_records:
            QMessageBox.information(self, "No results", "There are no results to save.")
            return
        try:
            with open(REPORT_PATH, "a", newline="", encoding="utf-8") as report_file:
                writer = csv.writer(report_file)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                for record in self.all_records:
                    writer.writerow([timestamp, *record])
            self.all_records = []
            self.notified_records.clear()
            self.alerted_records.clear()
            self.filter_data()
            QMessageBox.information(self, "Report saved", "The report was saved and the list cleared.")
        except Exception as error:
            QMessageBox.critical(self, "Save failed", str(error))
