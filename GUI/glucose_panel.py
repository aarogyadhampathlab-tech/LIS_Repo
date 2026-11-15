from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from GUI.common import COLORS, DraggableDialog

class GlucosePanelMixin:
    def _build_glucose_inline_panel(self):
        panel = QFrame()
        panel.setObjectName("surface")
        self._apply_card_shadow(panel)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(10)

        heading = QLabel("GLUCOSE")
        heading.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 8pt; font-weight: 800;"
        )
        layout.addWidget(heading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(52)
        self.glucose_inline_content = QWidget()
        self.glucose_inline_layout = QHBoxLayout(self.glucose_inline_content)
        self.glucose_inline_layout.setContentsMargins(0, 0, 0, 0)
        self.glucose_inline_layout.setSpacing(8)
        self.glucose_inline_stretch = self.glucose_inline_layout.addStretch(1)
        scroll.setWidget(self.glucose_inline_content)
        layout.addWidget(scroll, 1)
        self.glucose_inline_panel = panel
        self.glucose_inline_panel.hide()
        return panel

    def _show_glucose_notification(
        self, patient_name, test_name, result, record_key
    ):
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
            dialog.drag_position_changed.connect(self._save_glucose_notification_position)
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
        self.glucose_notification_records[notification_id] = record_key
        self.notification_heading.setText(f"GLUCOSE ALERTS  ·  {len(self.notification_rows) + 1}")
        self._add_glucose_inline_notification(
            notification_id, patient_name, test_name, result
        )

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

        dismiss_button = QPushButton("OK")
        dismiss_button.setFixedHeight(25)
        dismiss_button.setToolTip("Acknowledge this glucose result")
        dismiss_button.setAccessibleName(
            f"Acknowledge glucose result for {patient_name}"
        )
        dismiss_button.setStyleSheet(
            f"QPushButton {{ color: {COLORS['muted']}; background: transparent;"
            f" border: none; font-size: 8pt; font-weight: 600; padding: 3px 6px; }}"
            f"QPushButton:hover {{ color: {COLORS['offline']}; background: {COLORS['border']}; }}"
        )
        dismiss_button.clicked.connect(
            lambda checked=False, item_id=notification_id:
                self._acknowledge_glucose_notification(item_id)
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

    def _add_glucose_inline_notification(
        self, notification_id, patient_name, test_name, result
    ):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {COLORS['surface_alt']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 7px; }}"
        )
        row = QHBoxLayout(card)
        row.setContentsMargins(8, 3, 8, 3)
        row.setSpacing(7)

        patient = QLabel(patient_name)
        patient.setTextFormat(Qt.TextFormat.PlainText)
        patient.setMaximumWidth(150)
        patient.setToolTip(patient_name)
        patient.setStyleSheet(
            "color: #FFFFFF; font-size: 8pt; font-weight: 700; border: none;"
        )
        test = QLabel(test_name.upper())
        test.setStyleSheet(
            f"color: {COLORS['muted']}; font-size: 7pt; font-weight: 700; border: none;"
        )
        value = QLabel(result)
        value.setTextFormat(Qt.TextFormat.PlainText)
        value.setToolTip(result)
        if self._alert_reason(test_name, result):
            value.setStyleSheet(
                "color: #FFFFFF; background: #8F2029; border-radius: 4px;"
                " padding: 3px 6px; font-size: 9pt; font-weight: 900;"
            )
        else:
            value.setStyleSheet(
                "color: #FFD27F; font-size: 9pt; font-weight: 800; border: none;"
            )
        row.addWidget(patient)
        row.addWidget(test)
        row.addWidget(value)

        self.glucose_inline_layout.insertWidget(
            self.glucose_inline_layout.count() - 1, card
        )
        self.inline_notification_rows[notification_id] = card
        self.glucose_inline_panel.show()

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
        if self.notification_collapsed:
            if self.notification_position is None:
                x_position = bounds.right() - window.width() - 18
                y_position = bounds.top() + max(
                    70, (bounds.height() - window.height()) // 2
                )
            else:
                x_position = min(
                    max(self.notification_position.x(), bounds.left()),
                    bounds.right() - window.width() + 1,
                )
                y_position = min(
                    max(self.notification_position.y(), bounds.top()),
                    bounds.bottom() - window.height() + 1,
                )
            window.move(x_position, y_position)
            self.notification_position = window.frameGeometry().topLeft()
            return

        y_position = bounds.top() + max(70, (bounds.height() - window.height()) // 2)
        window.move(bounds.left() + 18, y_position)

    def _save_glucose_notification_position(self, position):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.notification_position = position
            return

        bounds = screen.availableGeometry()
        window = self.notification_window
        width = window.width() if window is not None else 54
        height = window.height() if window is not None else 54
        x_position = min(
            max(position.x(), bounds.left()), bounds.right() - width + 1
        )
        y_position = min(
            max(position.y(), bounds.top()), bounds.bottom() - height + 1
        )
        self.notification_position = QPoint(x_position, y_position)
        if window is not None:
            window.move(self.notification_position)

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
        for inline_card in self.inline_notification_rows.values():
            self.glucose_inline_layout.removeWidget(inline_card)
            inline_card.deleteLater()
        self.inline_notification_rows.clear()
        self.glucose_notification_records.clear()
        self.glucose_inline_panel.hide()
        self.notification_window.hide()
        self.notification_window.deleteLater()
        self.notification_window = None
        self.notification_collapsed = False
        self.notification_maximized = False

    def _dismiss_glucose_notification(self, notification_id):
        self.glucose_notification_records.pop(notification_id, None)
        alert_card = self.notification_rows.pop(notification_id, None)
        if alert_card is None:
            return
        self.notification_body_layout.removeWidget(alert_card)
        alert_card.deleteLater()
        inline_card = self.inline_notification_rows.pop(notification_id, None)
        if inline_card is not None:
            self.glucose_inline_layout.removeWidget(inline_card)
            inline_card.deleteLater()
        self.notification_heading.setText(f"GLUCOSE ALERTS  ·  {len(self.notification_rows)}")
        self.notification_bubble.setText(
            str(len(self.notification_rows)) if len(self.notification_rows) < 100 else "99+"
        )
        if not self.notification_rows and self.notification_window is not None:
            self.glucose_inline_panel.hide()
            self.notification_window.hide()
            self.notification_window.deleteLater()
            self.notification_window = None
