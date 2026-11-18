import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QModelIndex,
    QPropertyAnimation,
    QStandardPaths,
    QSize,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.alert_store import AlertStore
from core.alert_rules import load_alert_rules
from core.patient_records import (
    index_missing_results,
    patient_freshness,
    remove_replaced_missing_results,
    track_missing_result,
)
from config import PATIENT_LOG_CSV
from core.patient_directory import load_patient_names
from GUI.alerts import AlertPanelMixin
from GUI.common import COLORS
from GUI.glucose_panel import GlucosePanelMixin
from GUI.settings import AlertSettingsPage


MAIN_COLORS = {
    "background": "#EAF2F8",
    "surface": "#FFFFFF",
    "surface_alt": "#F4F7FB",
    "border": "#D6E1EE",
    "text": "#1D3148",
    "muted": "#687B91",
    "accent": "#2F80E2",
    "accent_dark": "#1958A3",
    "accent_soft": "#DCEAFF",
    "online": "#23845B",
    "offline": "#C34F57",
    "warning": "#946315",
}


class LabMark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(0.78, 0.78)
        painter.setPen(QPen(QColor(MAIN_COLORS["accent"]), 2.2, Qt.PenStyle.SolidLine,
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
        painter.setBrush(QColor(MAIN_COLORS["accent"]))
        painter.drawPath(liquid)
        painter.setBrush(QColor(MAIN_COLORS["text"]))
        painter.drawEllipse(23, 31, 3, 3)
        painter.drawEllipse(30, 27, 2.5, 2.5)

def make_app_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(MAIN_COLORS["surface_alt"]))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 15, 15)
    painter.setPen(QPen(QColor(MAIN_COLORS["accent"]), 3, Qt.PenStyle.SolidLine,
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
    painter.setBrush(QColor(MAIN_COLORS["accent"]))
    painter.drawRoundedRect(20, 42, 24, 8, 3, 3)
    painter.end()
    return QIcon(pixmap)


def make_patient_icon_pixmap():
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#E5F0FC"))
    painter.drawEllipse(0, 0, 20, 20)
    painter.setBrush(QColor("#4F83B8"))
    painter.drawEllipse(7, 4, 6, 6)
    painter.drawRoundedRect(4, 12, 12, 6, 4, 4)
    painter.end()
    return pixmap


def create_application(arguments):
    application = QApplication(arguments)
    application.setApplicationName("LIS Lab Monitor")
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    application.setFont(font)
    return application


def group_records_by_received_date(records, received_at_by_record):
    groups = {}
    for record in records:
        received_at = received_at_by_record.get(record)
        date_key = received_at.date() if received_at is not None else None
        groups.setdefault(date_key, []).append(record)
    return groups


class LabApp(AlertPanelMixin, GlucosePanelMixin, QMainWindow):
    records_received = Signal(object)
    network_status_received = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LIS Lab Monitor")
        self.setWindowIcon(make_app_icon())
        self.resize(1240, 860)
        self.setMinimumSize(980, 680)
        self.network_online = False
        self.setStyleSheet(self._main_application_stylesheet())

        self.all_records = []
        self.result_received_at = {}
        self.alert_rules = load_alert_rules()
        self.notified_records = set()
        self.alerted_records = set()
        data_directory = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if not data_directory:
            data_directory = str(Path.home() / ".lis_lab_monitor")
        self.alert_store = AlertStore(Path(data_directory) / "alerts.sqlite3")
        self.acknowledged_glucose_records = (
            self.alert_store.acknowledged_glucose_keys()
        )
        self.emergency_alert_sound = Path(data_directory) / "emergency_alert.wav"
        self.emergency_alert_sound.write_bytes(self._build_emergency_alert_sound())
        self.alerted_records.update(self.alert_store.known_alert_keys())
        self.active_alerts = self.alert_store.unacknowledged_alerts()
        self.alert_sound_timer = QTimer(self)
        self.alert_sound_timer.setInterval(3200)
        self.alert_sound_timer.timeout.connect(self._play_alert_sound)
        self.notification_window = None
        self.notification_rows = {}
        self.inline_notification_rows = {}
        self.glucose_notification_records = {}
        self.notification_counter = 0
        self.notification_collapsed = False
        self.notification_maximized = False
        self.notification_position = None
        self.current_page = "live"
        self.records_received.connect(self._append_records)
        self.network_status_received.connect(self._set_network_status)
        self.view_refresh_timer = QTimer(self)
        self.view_refresh_timer.setSingleShot(True)
        self.view_refresh_timer.setInterval(150)
        self.view_refresh_timer.timeout.connect(self.filter_data)

        self._build_interface()
        self.connection_dot_opacity = QGraphicsOpacityEffect(self.connection_dot)
        self.connection_dot.setGraphicsEffect(self.connection_dot_opacity)
        self.connection_dot_animation = QPropertyAnimation(
            self.connection_dot_opacity, b"opacity", self
        )
        self.connection_dot_animation.setDuration(1000)
        self.connection_dot_animation.setStartValue(0.55)
        self.connection_dot_animation.setEndValue(1.0)
        self.connection_dot_animation.setEasingCurve(
            QEasingCurve.Type.InOutSine
        )
        self.connection_dot_animation.setLoopCount(-1)
        self.patient_names_by_barcode = {}
        self._patient_directory_error = None
        self._patient_directory_signature = None
        self._refresh_patient_directory()
        self.patient_directory_timer = QTimer(self)
        self.patient_directory_timer.setInterval(3000)
        self.patient_directory_timer.timeout.connect(self._refresh_patient_directory)
        self.patient_directory_timer.start()
        self.patient_fetch_toast = None
        self.patient_fetch_toast_timer = QTimer(self)
        self.patient_fetch_toast_timer.setSingleShot(True)
        self.patient_fetch_toast_timer.timeout.connect(self._hide_patient_fetch_toast)
        self.patient_freshness_timer = QTimer(self)
        self.patient_freshness_timer.setInterval(60_000)
        self.patient_freshness_timer.timeout.connect(self.filter_data)
        self.patient_freshness_timer.start()
        self._refresh_active_alerts()
        self.filter_data()

    def _application_stylesheet(self):
        return f"""
            QWidget {{
                color: {COLORS['text']};
                font-family: "Segoe UI Variable";
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
            QComboBox {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 10px;
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
            QComboBox:focus {{ border: 1px solid {COLORS['accent']}; }}
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

    def _main_application_stylesheet(self):
        return f"""
            QWidget#root {{
                background: {MAIN_COLORS['background']};
                color: {MAIN_COLORS['text']};
                font-family: "Segoe UI";
                font-size: 10pt;
            }}
            QFrame#mainSidebar {{
                background: #17324F;
                border: none;
                border-radius: 20px;
            }}
            QFrame#mainHeader, QFrame#summaryCard, QFrame#mainResultsPanel {{
                background: rgba(255, 255, 255, 238);
                border: none;
                border-radius: 16px;
            }}
            QWidget#criticalHistoryPage,
            QWidget#glucosePage,
            QWidget#liveResultsPage {{
                background: transparent;
                border: none;
            }}
            QFrame#summaryCard {{
                border-radius: 14px;
            }}
            QWidget#root QFrame#surface {{
                background: #F4F8FC;
                color: {MAIN_COLORS['text']};
                border: none;
                border-radius: 12px;
            }}
            QWidget#root QLineEdit, QWidget#root QComboBox {{
                background: #F7FAFD;
                color: {MAIN_COLORS['text']};
                border: none;
                border-radius: 9px;
                padding: 9px 11px;
                selection-background-color: {MAIN_COLORS['accent_soft']};
            }}
            QWidget#root QLineEdit:focus, QWidget#root QComboBox:focus {{
                background: #EDF5FE;
            }}
            QWidget#root QComboBox::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
            }}
            QWidget#root QTreeWidget {{
                background: transparent;
                alternate-background-color: #F4F8FC;
                border: none;
                outline: none;
                selection-background-color: {MAIN_COLORS['accent_soft']};
                selection-color: {MAIN_COLORS['text']};
                padding: 5px;
            }}
            QWidget#root QTreeWidget::item {{
                min-height: 34px;
                padding: 5px 7px;
                border: none;
            }}
            QWidget#root QTreeWidget::item:hover {{
                background: #EDF5FF;
            }}
            QWidget#root QHeaderView::section {{
                color: {MAIN_COLORS['muted']};
                background: #F2F6FB;
                border: none;
                padding: 11px 10px;
                font-size: 8pt;
                font-weight: 700;
            }}
            QWidget#root QTableWidget {{
                background: #FFFFFF;
                alternate-background-color: #F6F9FC;
                color: {MAIN_COLORS['text']};
                border: none;
                outline: none;
                gridline-color: transparent;
                selection-background-color: {MAIN_COLORS['accent_soft']};
                selection-color: {MAIN_COLORS['text']};
            }}
            QWidget#root QTableWidget::item {{
                border: none;
                padding: 7px 8px;
            }}
            QWidget#root QPlainTextEdit {{
                color: {MAIN_COLORS['muted']};
                background: #F6F9FC;
                border: 1px solid #E3EAF2;
                border-radius: 9px;
                padding: 8px;
                selection-background-color: {MAIN_COLORS['accent_soft']};
                font-family: "Cascadia Code", "Consolas";
                font-size: 9pt;
            }}
            QWidget#root QPushButton {{
                color: {MAIN_COLORS['text']};
                background: #F5F8FC;
                border: none;
                border-radius: 9px;
                padding: 8px 12px;
                font-weight: 600;
            }}
            QWidget#root QPushButton:hover {{
                background: #EAF2FC;
            }}
            QWidget#root QPushButton:pressed {{
                background: {MAIN_COLORS['accent_soft']};
            }}
            QWidget#root QPushButton#primary {{
                color: #FFFFFF;
                background: #1768C4;
                border: 1px solid #1768C4;
                padding: 10px 16px;
            }}
            QWidget#root QPushButton#primary:hover {{
                background: #125BAE;
            }}
            QWidget#root QPushButton#demoButton {{
                color: #38536F;
                background: transparent;
                border: none;
                padding: 7px 10px;
                font-size: 8pt;
            }}
            QWidget#root QPushButton#sidebarOption {{
                color: #DCEAFF;
                background: transparent;
                border: none;
                text-align: left;
                padding: 10px 11px;
                font-size: 9pt;
                font-weight: 600;
            }}
            QWidget#root QPushButton#sidebarOption:checked {{
                color: #FFFFFF;
                background: rgba(77, 146, 230, 0.32);
                border: none;
            }}
            QWidget#root QPushButton#sidebarOption:hover:!checked {{
                background: rgba(255, 255, 255, 0.08);
            }}
            QMenu {{
                color: {MAIN_COLORS['text']};
                background: #FFFFFF;
                border: 1px solid {MAIN_COLORS['border']};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 7px 20px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background: {MAIN_COLORS['accent_soft']};
            }}
            QWidget#root QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 3px;
            }}
            QWidget#root QScrollBar::handle:vertical {{
                background: #BDCCDC;
                border-radius: 4px;
                min-height: 28px;
            }}
            QWidget#root QScrollBar::handle:vertical:hover {{
                background: #8EA8C4;
            }}
            QWidget#root QScrollBar::add-line:vertical,
            QWidget#root QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QMessageBox {{
                background: {MAIN_COLORS['surface']};
                color: {MAIN_COLORS['text']};
            }}
        """

    def _build_interface(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        layout.addWidget(self._build_sidebar())

        content = QVBoxLayout()
        content.setSpacing(12)
        content.addWidget(self._build_header())
        content.addLayout(self._build_summary_cards())
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        self.live_results_page = self._build_results()
        self.glucose_results_page = self._build_glucose_results_page()
        self.critical_history_page = self._build_critical_history_page()
        self.settings_page = AlertSettingsPage(
            self.alert_rules, self._apply_alert_rules
        )
        for page in (
            self.live_results_page,
            self.glucose_results_page,
            self.critical_history_page,
            self.settings_page,
        ):
            self.content_stack.addWidget(page)
        content.addWidget(self.content_stack, 1)
        layout.addLayout(content, 1)
        self._build_alert_card()

    def _add_navigation_option(self, layout, label, page_id, checked=False):
        button = QPushButton(label)
        button.setObjectName("sidebarOption")
        button.setCheckable(True)
        button.setChecked(checked)
        self.navigation_group.addButton(button)
        button.clicked.connect(
            lambda _checked=False, selected_page=page_id: self._show_content_page(
                selected_page
            )
        )
        self.navigation_buttons[page_id] = button
        layout.addWidget(button)

    def _build_sidebar(self):
        sidebar = QFrame()
        self.sidebar = sidebar
        sidebar.setObjectName("mainSidebar")
        sidebar.setFixedWidth(190)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(15, 17, 15, 15)
        layout.setSpacing(12)

        brand = QHBoxLayout()
        brand.setSpacing(9)
        brand.addWidget(LabMark())
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("AROGYADHAM")
        name.setStyleSheet("color: #F1F7FF; font-size: 8pt; font-weight: 800;")
        hospital = QLabel("HOSPITAL")
        hospital.setStyleSheet(
            "color: #F1F7FF; font-size: 6.5pt; font-weight: 700; letter-spacing: 1px;"
        )
        subtitle = QLabel("LAB MONITOR")
        subtitle.setStyleSheet(
            "color: #B7C9DF; font-size: 6pt; font-weight: 600; letter-spacing: 0.7px;"
        )
        brand_text.addWidget(name)
        brand_text.addWidget(hospital)
        brand_text.addWidget(subtitle)
        brand.addLayout(brand_text, 1)
        layout.addLayout(brand)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(225, 239, 255, 0.18); border: none;")
        layout.addWidget(divider)

        section = QLabel("WORKSPACE")
        section.setStyleSheet("color: #AFC3DA; font-size: 8pt; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(section)

        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        self.navigation_buttons = {}
        self._add_navigation_option(layout, "Live results", "live", checked=True)
        self._add_navigation_option(layout, "Glucose information", "glucose")
        self._add_navigation_option(layout, "Critical ranges", "critical")
        self._add_navigation_option(layout, "Settings", "settings")

        layout.addStretch(1)

        sync_card = QWidget()
        sync_card.setObjectName("monitoringNote")
        sync_card.setStyleSheet(
            "QWidget#monitoringNote { background: rgba(255,255,255,0.07);"
            " border: none; border-radius: 12px; }"
        )
        sync_layout = QVBoxLayout(sync_card)
        sync_layout.setContentsMargins(10, 10, 10, 10)
        sync_layout.setSpacing(4)
        sync_title = QLabel("LIVE MONITORING")
        sync_title.setStyleSheet("color: #F0F6FF; font-size: 8pt; font-weight: 700;")
        sync_note = QLabel("Incoming analyzer logs are checked automatically.")
        sync_note.setWordWrap(True)
        sync_note.setStyleSheet("color: #B7C9DF; font-size: 8pt;")
        sync_layout.addWidget(sync_title)
        sync_layout.addWidget(sync_note)
        layout.addWidget(sync_card)
        self._apply_card_shadow(sidebar)
        return sidebar

    def _build_header(self):
        header = QFrame()
        header.setObjectName("mainHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(17, 13, 17, 13)
        row.setSpacing(9)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Laboratory overview")
        title.setStyleSheet(f"font-size: 16pt; font-weight: 750; color: {MAIN_COLORS['text']};")
        subtitle = QLabel("Live patient results and analyzer activity")
        subtitle.setStyleSheet(f"font-size: 8pt; color: {MAIN_COLORS['muted']};")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        row.addLayout(title_stack)
        row.addStretch(1)

        self.connection_status = QFrame()
        self.connection_status.setStyleSheet(
            "QFrame { background: #F2F7FC; border: none; border-radius: 10px; }"
        )
        status_layout = QHBoxLayout(self.connection_status)
        status_layout.setContentsMargins(9, 6, 9, 6)
        status_layout.setSpacing(6)
        self.connection_dot = QLabel("●")
        self.connection_dot.setStyleSheet(f"color: {MAIN_COLORS['offline']}; font-size: 8pt;")
        status_layout.addWidget(self.connection_dot)
        self.connection_label = QLabel("OFFLINE")
        self.connection_label.setStyleSheet(
            f"color: {MAIN_COLORS['offline']}; font-size: 8pt; font-weight: 700;"
        )
        status_layout.addWidget(self.connection_label)
        row.addWidget(self.connection_status)

        self.alert_label = QLabel("")
        self.alert_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.alert_label.setWordWrap(True)
        self.alert_label.setMaximumWidth(210)
        self.alert_label.setStyleSheet(f"color: {MAIN_COLORS['warning']}; font-weight: 600;")
        row.addWidget(self.alert_label)
        self.demo_alert_button = QPushButton("Trigger Demo Alert")
        self.demo_alert_button.setObjectName("demoButton")
        self.demo_alert_button.setToolTip(
            "Create a clearly labeled test alert to check sound and acknowledgment."
        )
        self.demo_alert_button.clicked.connect(self._trigger_demo_alert)
        row.addWidget(self.demo_alert_button)
        self.demo_missing_button = QPushButton("Trigger Missing Demo")
        self.demo_missing_button.setObjectName("demoButton")
        self.demo_missing_button.setToolTip(
            "Create a test-only MISSING_RESULT alert."
        )
        self.demo_missing_button.clicked.connect(self._trigger_demo_missing_alert)
        row.addWidget(self.demo_missing_button)
        self._apply_card_shadow(header)
        return header

    def _build_summary_cards(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        self.summary_values = {}
        summaries = (
            ("RESULTS IN SESSION", "results"),
            ("PATIENTS", "patients"),
            ("ACTIVE ALERTS", "alerts"),
            ("ANALYZER", "analyzer"),
        )
        for title, key in summaries:
            card = QFrame()
            card.setObjectName("summaryCard")
            self._apply_card_shadow(card)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 9, 12, 9)
            card_layout.setSpacing(4)
            heading = QLabel(title)
            heading.setStyleSheet(
                f"color: {MAIN_COLORS['muted']}; font-size: 7pt; font-weight: 700;"
            )
            value = QLabel("OFFLINE" if key == "analyzer" else "0")
            value.setStyleSheet(
                f"color: {MAIN_COLORS['text']}; font-size: 17pt; font-weight: 750;"
            )
            card_layout.addWidget(heading)
            card_layout.addWidget(value)
            self.summary_values[key] = value
            row.addWidget(card, 1)
        return row

    def _show_content_page(self, page_id):
        page_indices = {"live": 0, "glucose": 1, "critical": 2, "settings": 3}
        self.current_page = page_id
        self.content_stack.setCurrentIndex(page_indices[page_id])
        self.navigation_buttons[page_id].setChecked(True)
        if hasattr(self, "glucose_inline_panel"):
            self.glucose_inline_panel.setVisible(page_id == "glucose")

    def _add_glucose_inline_notification(
        self, notification_id, patient_name, test_name, result
    ):
        super()._add_glucose_inline_notification(
            notification_id, patient_name, test_name, result
        )
        self.glucose_inline_panel.setVisible(self.current_page == "glucose")

    def _refresh_critical_history(self):
        if not hasattr(self, "critical_history_table"):
            return
        history = self.alert_store.recent_critical_alerts(limit=8)
        self._populate_data_table(
            self.critical_history_table,
            [
                (
                    alert["patient_name"],
                    alert["test_name"],
                    alert["flagged_value"],
                    alert["reason"],
                    datetime.fromisoformat(alert["created_at"])
                    .astimezone()
                    .strftime("%m/%d/%Y %I:%M:%S %p"),
                    "Acknowledged"
                    if alert["status"] == "ACKNOWLEDGED"
                    else "Active",
                )
                for alert in history
            ],
        )
        self.critical_history_count.setText(
            f"{len(history)} recent critical results"
        )

    @staticmethod
    def _glucose_record_storage_key(record_key):
        return json.dumps(record_key, ensure_ascii=False, separators=(",", ":"))

    def _acknowledge_glucose_notification(self, notification_id):
        record_key = self.glucose_notification_records.get(notification_id)
        if record_key is None:
            return

        storage_key = self._glucose_record_storage_key(record_key)
        acknowledged_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.alert_store.acknowledge_glucose(storage_key, acknowledged_at)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Acknowledgment failed",
                "The glucose result remains active because acknowledgment was "
                f"not saved.\n\n{error}",
            )
            return

        self.acknowledged_glucose_records.add(storage_key)
        self._dismiss_glucose_notification(notification_id)

    def _clear_glucose_notifications(self):
        storage_keys = {
            self._glucose_record_storage_key(record_key)
            for record_key in self.glucose_notification_records.values()
        }
        acknowledged_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.alert_store.acknowledge_glucose_many(
                storage_keys, acknowledged_at
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Acknowledgment failed",
                "The glucose results remain active because acknowledgment was "
                f"not saved.\n\n{error}",
            )
            return

        self.acknowledged_glucose_records.update(storage_keys)
        super()._clear_glucose_notifications()

    def _update_summary_cards(self):
        if not hasattr(self, "summary_values"):
            return
        self.summary_values["results"].setText(str(len(self.all_records)))
        self.summary_values["patients"].setText(
            str(
                len(
                    {
                        (record[0], self._patient_display_name(record[0], record[1]))
                        for record in self.all_records
                    }
                )
            )
        )
        self.summary_values["alerts"].setText(str(len(self.active_alerts)))
        self.summary_values["analyzer"].setText(
            "ONLINE" if self.network_online else "OFFLINE"
        )
        analyzer_color = MAIN_COLORS["online"] if self.network_online else MAIN_COLORS["offline"]
        self.summary_values["analyzer"].setStyleSheet(
            f"color: {analyzer_color}; font-size: 14pt; font-weight: 750;"
        )

    def _build_search_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        self.patient_filter = QComboBox()
        self.patient_filter.addItem("All", "all")
        self.patient_filter.addItem("UHID", "uhid")
        self.patient_filter.addItem("Name", "name")
        self.patient_filter.setToolTip("Choose which patient field to search")
        self.patient_filter.currentIndexChanged.connect(self._on_patient_filter_changed)

        self.patient_search = QLineEdit()
        self.patient_search.setPlaceholderText("Search patient name or UHID")
        self.patient_search.setClearButtonEnabled(True)
        self.patient_search.setToolTip("Filter results by the selected patient field")
        self.patient_search.textChanged.connect(self._schedule_filter_data)

        self.fetch_patient_names_button = QPushButton("Fetch Names")
        self.fetch_patient_names_button.setToolTip(
            "Match current UHIDs with the saved patient CSV"
        )
        self.fetch_patient_names_button.clicked.connect(
            self._fetch_patient_names_from_csv
        )

        self.test_search = QLineEdit()
        self.test_search.setPlaceholderText("Search tests")
        self.test_search.setClearButtonEnabled(True)
        self.test_search.setToolTip("Filter results by test name")
        self.test_search.textChanged.connect(self._schedule_filter_data)

        row.addWidget(self.patient_filter)
        row.addWidget(self.patient_search, 1)
        row.addWidget(self.test_search, 1)
        row.addWidget(self.fetch_patient_names_button)
        self.result_count = QLabel("0 PATIENTS  ·  0 RESULTS")
        self.result_count.setMinimumWidth(150)
        self.result_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.result_count.setStyleSheet(
            f"color: {MAIN_COLORS['muted']}; font-size: 8pt; font-weight: 600;"
        )
        row.addWidget(self.result_count)
        return row

    def _on_patient_filter_changed(self, *_args):
        placeholder_by_filter = {
            "all": "Search patient name or UHID",
            "uhid": "Search UHID",
            "name": "Search patient name",
        }
        self.patient_search.setPlaceholderText(
            placeholder_by_filter.get(self.patient_filter.currentData(), "Search patient")
        )
        self._schedule_filter_data()

    def _build_data_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    def _populate_data_table(self, table, rows):
        table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column_index == 0:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                if values[-1] in {"OK", "ABNORMAL", "MISSING", "ERROR", "Active", "Acknowledged"} and column_index == len(values) - 1:
                    color = (
                        MAIN_COLORS["online"]
                        if values[-1] in {"OK", "Acknowledged"}
                        else MAIN_COLORS["offline"]
                        if values[-1] in {"MISSING", "ERROR", "Active"}
                        else MAIN_COLORS["warning"]
                    )
                    item.setForeground(QColor(color))
                    font = item.font()
                    font.setBold(values[-1] != "OK")
                    item.setFont(font)
                table.setItem(row_index, column_index, item)

    def _build_glucose_results_page(self):
        page = QWidget()
        page.setObjectName("glucosePage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title, subtitle = self._build_page_heading(
            "Glucose information",
            "Glucose results received from the analyzer",
        )
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._build_glucose_inline_panel())
        self.glucose_results_table = self._build_data_table(
            ["PATIENT", "TEST", "RESULT", "RECEIVED", "STATUS"]
        )
        layout.addWidget(self.glucose_results_table, 1)
        self.glucose_results_count = QLabel("0 glucose results")
        self.glucose_results_count.setStyleSheet(
            f"color: {MAIN_COLORS['muted']}; font-size: 8pt; font-weight: 600;"
        )
        layout.addWidget(self.glucose_results_count)
        return page

    def _build_critical_history_page(self):
        page = QWidget()
        page.setObjectName("criticalHistoryPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title, subtitle = self._build_page_heading(
            "Critical ranges",
            "Recent results outside configured critical limits",
        )
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.critical_history_table = self._build_data_table(
            ["PATIENT", "TEST", "RESULT", "RANGE", "RECEIVED", "STATUS"]
        )
        layout.addWidget(self.critical_history_table, 1)
        self.critical_history_count = QLabel("0 recent critical results")
        self.critical_history_count.setStyleSheet(
            f"color: {MAIN_COLORS['muted']}; font-size: 8pt; font-weight: 600;"
        )
        layout.addWidget(self.critical_history_count)
        return page

    def _build_page_heading(self, title_text, subtitle_text):
        title = QLabel(title_text)
        title.setStyleSheet(
            f"color: {MAIN_COLORS['text']}; font-size: 16pt; font-weight: 750;"
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet(f"color: {MAIN_COLORS['muted']}; font-size: 9pt;")
        return title, subtitle

    def _build_results(self):
        panel = QFrame()
        panel.setObjectName("mainResultsPanel")
        panel.setProperty("pageId", "liveResultsPage")
        self._apply_card_shadow(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(13, 11, 13, 9)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Recent results")
        title.setStyleSheet(
            f"color: {MAIN_COLORS['text']}; font-size: 12pt; font-weight: 700;"
        )
        subtitle = QLabel("Review incoming laboratory values")
        subtitle.setStyleSheet(f"color: {MAIN_COLORS['muted']}; font-size: 8pt;")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        title_row.addLayout(title_stack)
        title_row.addStretch(1)
        layout.addLayout(title_row)
        layout.addLayout(self._build_search_row())

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(
            ["PATIENT / UHID", "TEST", "RESULT", "RECEIVED", "STATUS"]
        )
        self.tree.setColumnWidth(0, 210)
        self.tree.setColumnWidth(1, 235)
        self.tree.setColumnWidth(2, 145)
        self.tree.setColumnWidth(3, 90)
        self.tree.setColumnWidth(4, 105)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(False)
        self.tree.setHeaderHidden(False)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree)
        return panel

    @staticmethod
    def _apply_card_shadow(widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(23, 50, 79, 42))
        widget.setGraphicsEffect(shadow)

    def add_records(self, records):
        self.records_received.emit(records)

    def _schedule_filter_data(self, *_args):
        self.view_refresh_timer.start()

    def _patient_display_name(self, patient_id, patient_name):
        barcode = str(patient_id or "").strip()
        return self.patient_names_by_barcode.get(barcode, patient_name)

    def _fetch_patient_names_from_csv(self):
        try:
            stat = Path(PATIENT_LOG_CSV).stat()
            patient_names = load_patient_names(PATIENT_LOG_CSV)
        except (OSError, ValueError) as error:
            self._patient_directory_signature = None
            self._patient_directory_error = str(error)
            self._show_patient_fetch_toast(
                f"Could not fetch names from the saved CSV: {error}", "error"
            )
            return

        self.patient_names_by_barcode = patient_names
        self._patient_directory_signature = (stat.st_size, stat.st_mtime_ns)
        self._patient_directory_error = None
        self._schedule_filter_data()

        patient_ids = {
            str(record[0] or "").strip()
            for record in self.all_records
            if str(record[0] or "").strip().casefold() not in {"", "unknown"}
        }
        matched_count = sum(
            patient_id in patient_names for patient_id in patient_ids
        )
        if matched_count:
            not_found_count = len(patient_ids) - matched_count
            message = f"Fetched names for {matched_count} of {len(patient_ids)} UHIDs."
            if not_found_count:
                message += f" {not_found_count} not found."
            self._show_patient_fetch_toast(message, "success")
        else:
            message = (
                "No current UHIDs are available to match."
                if not patient_ids
                else "No names were found for the current UHIDs."
            )
            self._show_patient_fetch_toast(message, "not_found")

    def _show_patient_fetch_toast(self, message, status):
        if self.patient_fetch_toast is None:
            self.patient_fetch_toast = QLabel(self)
            self.patient_fetch_toast.setObjectName("patientFetchToast")
            self.patient_fetch_toast.setWordWrap(True)
            self.patient_fetch_toast.setMaximumWidth(360)
            self.patient_fetch_toast.setMargin(10)
            self.patient_fetch_toast.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )

        style_by_status = {
            "success": "background: #E8F5EE; color: #236B48; border: 1px solid #B9DDC8;",
            "error": "background: #FCEDEE; color: #9B3940; border: 1px solid #EAC2C5;",
            "not_found": "background: #FFF6E5; color: #805D1D; border: 1px solid #E9D5A8;",
        }
        self.patient_fetch_toast.setText(message)
        self.patient_fetch_toast.setStyleSheet(
            "QLabel#patientFetchToast { "
            + style_by_status[status]
            + " border-radius: 9px; font-size: 9pt; }"
        )
        self.patient_fetch_toast.adjustSize()
        self.patient_fetch_toast.move(
            max(12, self.width() - self.patient_fetch_toast.width() - 28),
            max(12, self.height() - self.patient_fetch_toast.height() - 28),
        )
        self.patient_fetch_toast.show()
        self.patient_fetch_toast.raise_()
        self.patient_fetch_toast_timer.start(3500)

    def _hide_patient_fetch_toast(self):
        if self.patient_fetch_toast is not None:
            self.patient_fetch_toast.hide()

    def _refresh_patient_directory(self):
        try:
            stat = Path(PATIENT_LOG_CSV).stat()
        except OSError as error:
            self._patient_directory_signature = None
            message = str(error)
            if message != self._patient_directory_error:
                print(f"Error checking patient directory {PATIENT_LOG_CSV}: {error}")
                self._patient_directory_error = message
            return

        signature = (stat.st_size, stat.st_mtime_ns)
        if signature == self._patient_directory_signature:
            return

        try:
            patient_names = load_patient_names(PATIENT_LOG_CSV)
        except (OSError, ValueError) as error:
            message = str(error)
            if message != self._patient_directory_error:
                print(f"Error loading patient directory {PATIENT_LOG_CSV}: {error}")
                self._patient_directory_error = message
            return

        self._patient_directory_error = None
        self._patient_directory_signature = signature
        if patient_names != self.patient_names_by_barcode:
            self.patient_names_by_barcode = patient_names
            self._schedule_filter_data()

    @Slot(object)
    def _append_records(self, records):
        observed_at = datetime.now().astimezone()
        alerts_changed = False
        received_at_by_record = (
            self.alert_store.get_or_create_result_received_at_many(
                records, observed_at
            )
        )
        missing_records = index_missing_results(self.all_records)
        for record in records:
            patient_id, patient_name, test_name, result = record
            remove_replaced_missing_results(
                self.all_records,
                self.result_received_at,
                record,
                missing_records,
            )

            self.all_records.append(record)
            track_missing_result(record, missing_records)
            self.result_received_at[record] = received_at_by_record[record]
            alerts_changed = self._check_record_alert(
                patient_id,
                self._patient_display_name(patient_id, patient_name),
                test_name,
                result,
                refresh=False,
            ) or alerts_changed
        if alerts_changed:
            self._refresh_active_alerts()
        self._schedule_filter_data()

    def filter_data(self, *args):
        patient_query = self.patient_search.text().strip().casefold()
        patient_filter = self.patient_filter.currentData()
        test_query = self.test_search.text().strip().casefold()
        grouped_by_date = {}
        visible_patients = set()
        visible_result_count = 0
        records_by_recency = sorted(
            self.all_records,
            key=lambda record: (
                self.result_received_at[record].timestamp()
                if record in self.result_received_at
                else float("-inf")
            ),
            reverse=True,
        )
        now = datetime.now().astimezone()
        latest_patient_results = {}
        for record in records_by_recency:
            patient_id, patient_name = record[:2]
            patient_display_name = self._patient_display_name(
                patient_id, patient_name
            )
            patient_key = (patient_id, patient_display_name)
            if patient_key not in latest_patient_results:
                latest_patient_results[patient_key] = self.result_received_at.get(
                    record
                )

        for date_key, date_records in group_records_by_received_date(
            records_by_recency, self.result_received_at
        ).items():
            patients = {}
            for patient_id, patient_name, test_name, result in date_records:
                patient_id_text = str(patient_id or "").casefold()
                display_name = self._patient_display_name(patient_id, patient_name)
                patient_name_text = str(display_name or "").casefold()
                test_name_text = str(test_name or "").casefold()
                if patient_filter == "uhid":
                    patient_matches = patient_query in patient_id_text
                elif patient_filter == "name":
                    patient_matches = patient_query in patient_name_text
                else:
                    patient_matches = (
                        patient_query in patient_id_text
                        or patient_query in patient_name_text
                    )
                if not patient_matches or test_query not in test_name_text:
                    continue
                patients.setdefault((patient_id, display_name), []).append(
                    (test_name, result)
                )
                visible_patients.add((patient_id, display_name))
                visible_result_count += 1
            if patients:
                grouped_by_date[date_key] = patients

        self.tree.clear()
        date_items = {}
        patient_rows = []
        patient_icon_pixmap = make_patient_icon_pixmap()
        for date_key, patients in grouped_by_date.items():
            date_label = (
                date_key.strftime("%A, %B %d, %Y")
                if date_key is not None
                else "Date unavailable"
            )
            date_item = QTreeWidgetItem([date_label, "", "", "", ""])
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            date_item.setSizeHint(0, QSize(0, 40))
            for column in range(self.tree.columnCount()):
                date_item.setBackground(column, QColor("#E5F0FC"))
                date_item.setForeground(column, QColor("#245C91"))
                date_font = date_item.font(column)
                date_font.setBold(True)
                date_font.setPointSizeF(10)
                date_item.setFont(column, date_font)
            self.tree.addTopLevelItem(date_item)
            self.tree.setFirstColumnSpanned(
                self.tree.indexOfTopLevelItem(date_item), QModelIndex(), True
            )
            date_item.setExpanded(True)
            date_items[date_key] = date_item
            patient_rows.extend(
                (date_key, patient, tests) for patient, tests in patients.items()
            )

        for date_key, (patient_id, patient_name), tests in patient_rows:
            date_item = date_items[date_key]
            patient_item = QTreeWidgetItem(["", "", "", "", ""])
            patient_item.setData(
                0, Qt.ItemDataRole.UserRole, (patient_id, patient_name)
            )
            date_item.addChild(patient_item)
            patient_details = QWidget(self.tree)
            patient_details.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
            details_layout = QHBoxLayout(patient_details)
            details_layout.setContentsMargins(2, 2, 2, 2)
            details_layout.setSpacing(5)
            patient_icon = QLabel()
            patient_icon.setPixmap(patient_icon_pixmap)
            patient_icon.setFixedSize(20, 20)
            details_layout.addWidget(patient_icon, 0, Qt.AlignmentFlag.AlignTop)
            patient_layout = QVBoxLayout()
            patient_layout.setContentsMargins(0, 0, 0, 0)
            patient_layout.setSpacing(1)
            patient_name_label = QLabel(patient_name)
            patient_name_label.setToolTip(patient_name)
            patient_name_label.setStyleSheet(
                f"color: {MAIN_COLORS['text']}; font-size: 9.5pt; "
                "font-weight: 600; background: transparent;"
            )
            patient_layout.addWidget(patient_name_label)

            patient_meta_layout = QHBoxLayout()
            patient_meta_layout.setContentsMargins(0, 0, 0, 0)
            patient_meta_layout.setSpacing(6)
            if patient_id and patient_id != "UNKNOWN":
                barcode_label = QLabel(f"UHID {patient_id}")
                barcode_label.setStyleSheet(
                    f"color: {MAIN_COLORS['muted']}; font-size: 8pt; "
                    "font-weight: 400; background: transparent;"
                )
                patient_meta_layout.addWidget(barcode_label)
            patient_meta_layout.addStretch(1)
            patient_layout.addLayout(patient_meta_layout)
            details_layout.addLayout(patient_layout, 1)
            self.tree.setItemWidget(patient_item, 0, patient_details)
            received_at = latest_patient_results.get((patient_id, patient_name))
            if received_at is not None:
                freshness = patient_freshness(received_at, now)
                freshness_colors = {
                    "LATEST": (MAIN_COLORS["online"], "#E7F5EE"),
                    "OLD": (MAIN_COLORS["warning"], "#FFF4DD"),
                    "LONG AGO": (MAIN_COLORS["offline"], "#FCEBED"),
                }
                foreground, background = freshness_colors[freshness]
                freshness_label = QLabel(freshness)
                freshness_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                freshness_label.setFixedSize(76, 20)
                freshness_label.setStyleSheet(
                    f"color: {foreground}; background: {background}; "
                    "border: none; border-radius: 10px; "
                    "padding: 0 5px; font-size: 7pt; font-weight: 600;"
                )
                freshness_label.setToolTip(
                    "Time since this patient's most recent result: "
                    "LATEST under 1 hour; OLD 1 to 24 hours; "
                    "LONG AGO 24 hours or more."
                )
                freshness_label.setAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents
                )
                self.tree.setItemWidget(patient_item, 4, freshness_label)
            patient_item.setExpanded(False)

            for test_name, result in tests:
                alert_reason = self._alert_reason(test_name, result)
                if alert_reason == "MISSING_RESULT":
                    status = "MISSING"
                elif alert_reason == "TECHNICAL ERROR":
                    status = "ERROR"
                elif alert_reason:
                    status = "ABNORMAL"
                else:
                    status = "OK"
                received_at = self.result_received_at.get(
                    (patient_id, patient_name, test_name, result)
                )
                received_text = (
                    received_at.strftime("%I:%M:%S %p") if received_at else "—"
                )
                display_result = "MISSING" if status == "MISSING" else result
                test_item = QTreeWidgetItem(
                    ["", test_name, display_result, received_text, status]
                )
                test_item.setForeground(1, QColor(MAIN_COLORS["muted"]))
                test_item.setForeground(2, QColor(MAIN_COLORS["text"]))
                if status == "MISSING":
                    test_item.setForeground(2, QColor(MAIN_COLORS["offline"]))
                    test_item.setBackground(2, QColor("#FCEBED"))
                test_item.setForeground(
                    3,
                    QColor(
                        MAIN_COLORS["muted"]
                    ),
                )
                status_color = (
                    MAIN_COLORS["online"]
                    if status == "OK"
                    else MAIN_COLORS["warning"]
                    if status == "ABNORMAL"
                    else MAIN_COLORS["offline"]
                )
                test_item.setForeground(4, QColor(status_color))
                if status == "OK":
                    test_item.setForeground(1, QColor("#7B8DA0"))
                    test_item.setForeground(2, QColor("#64788D"))
                    test_item.setForeground(3, QColor("#8797A8"))
                    test_item.setForeground(4, QColor("#6D9A83"))
                patient_item.addChild(test_item)

        glucose_rows = []
        for patient_id, patient_name, test_name, result in records_by_recency:
            if "glucose" not in str(test_name or "").casefold():
                continue
            display_name = self._patient_display_name(patient_id, patient_name)
            status = self._result_status(test_name, result)
            received_at = self.result_received_at.get(
                (patient_id, patient_name, test_name, result)
            )
            glucose_rows.append(
                (
                    display_name,
                    test_name,
                    result,
                    received_at.strftime("%m/%d/%Y %I:%M:%S %p")
                    if received_at
                    else "—",
                    status,
                )
            )
        self._populate_data_table(self.glucose_results_table, glucose_rows)
        self.glucose_results_count.setText(f"{len(glucose_rows)} glucose results")

        self.result_count.setText(
            f"{len(visible_patients)} PATIENTS  ·  {visible_result_count} RESULTS"
        )
        self._update_summary_cards()

        for patient_id, patient_name, test_name, result in records_by_recency:
            if "glucose" not in str(test_name or "").casefold():
                continue
            display_name = self._patient_display_name(patient_id, patient_name)
            record_key = (patient_name, patient_id, test_name, result)
            storage_key = self._glucose_record_storage_key(record_key)
            if (
                record_key not in self.notified_records
                and storage_key not in self.acknowledged_glucose_records
            ):
                self._show_glucose_notification(
                    display_name, test_name, result, record_key
                )
                self.notified_records.add(record_key)

    def _result_status(self, test_name, result):
        alert_reason = self._alert_reason(test_name, result)
        if alert_reason == "MISSING_RESULT":
            return "MISSING"
        if alert_reason == "TECHNICAL ERROR":
            return "ERROR"
        return "ABNORMAL" if alert_reason else "OK"

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
        patient_item = item
        while patient_item is not None:
            patient_identity = patient_item.data(0, Qt.ItemDataRole.UserRole)
            if patient_identity:
                break
            patient_item = patient_item.parent()
        if not patient_identity:
            return
        patient_id, patient_name = patient_identity
        self.all_records = [
            record
            for record in self.all_records
            if (record[0], self._patient_display_name(record[0], record[1]))
            != (patient_id, patient_name)
        ]
        self.notified_records = {
            record for record in self.notified_records if record[0] != patient_name
        }
        remaining_records = set(self.all_records)
        self.result_received_at = {
            record: received_at
            for record, received_at in self.result_received_at.items()
            if record in remaining_records
        }
        self.filter_data()

    def update_network_status(self, online, path):
        self.network_status_received.emit(online, path)

    @Slot(bool, str)
    def _set_network_status(self, online, path):
        status_changed = self.network_online != online
        path_changed = self.connection_label.toolTip() != path
        if not status_changed and not path_changed:
            return

        self.network_online = online
        if status_changed:
            color = MAIN_COLORS["online"] if online else MAIN_COLORS["offline"]
            status = "ONLINE" if online else "OFFLINE"
            self.connection_dot.setStyleSheet(f"color: {color}; font-size: 8pt;")
            if online:
                self.connection_dot_animation.start()
            else:
                self.connection_dot_animation.stop()
                self.connection_dot_opacity.setOpacity(1.0)
            self.connection_label.setText(status)
            self.connection_label.setStyleSheet(
                f"color: {color}; font-size: 8pt; font-weight: 700;"
            )
            self._update_summary_cards()
        if path_changed:
            self.connection_label.setToolTip(path)

    def _refresh_active_alerts(self):
        super()._refresh_active_alerts()
        self._update_summary_cards()
        self._refresh_critical_history()

    def _apply_alert_rules(self, alert_rules):
        self.alert_rules = alert_rules
        self.filter_data()
