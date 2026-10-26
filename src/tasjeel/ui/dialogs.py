from typing import List, Optional

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
                             QLineEdit, QProgressBar, QPushButton, QVBoxLayout,
                             QWidget)

from tasjeel.ui.components import StatusDot
from tasjeel.ui.icons import svg_pixmap

DIALOG_WIDTH = 440
DIALOG_RADIUS = 18
KIND_COLORS = {
    "info": "#f5f5f5",
    "success": "#30d158",
    "warning": "#ffd60a",
    "error": "#ff453a",
    "progress": "#0a84ff",
}


class TasjeelDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], title: str, text: str = "", kind: str = "info"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setFixedWidth(DIALOG_WIDTH)
        self.result_index: Optional[int] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(svg_pixmap("quill", "#ffffff", 18, stroke_width=1.6))
        logo.setFixedSize(18, 18)
        brand = QLabel("تسجيل")
        brand.setObjectName("dialogBrand")
        header.addWidget(logo)
        header.addWidget(brand)
        header.addStretch(1)
        layout.addLayout(header)
        layout.addSpacing(20)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        dot = StatusDot()
        dot.set_color(KIND_COLORS.get(kind, KIND_COLORS["info"]))
        self.title_label = QLabel(title)
        self.title_label.setObjectName("dialogTitle")
        self.title_label.setWordWrap(True)
        title_row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(self.title_label, 1)
        layout.addLayout(title_row)

        self.text_label = QLabel(text)
        self.text_label.setObjectName("dialogText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text_label.setVisible(bool(text))
        layout.addSpacing(10)
        layout.addWidget(self.text_label)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self.body.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.body)

        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(10)
        self.buttons.addStretch(1)
        layout.addSpacing(24)
        layout.addLayout(self.buttons)

    def add_body_widget(self, widget: QWidget):
        self.body.addSpacing(8)
        self.body.addWidget(widget)

    def add_button(self, text: str, role: str = "secondary") -> QPushButton:
        button = QPushButton(text)
        button.setObjectName({"primary": "primaryButton", "danger": "dangerButton"}.get(role, "secondaryButton"))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(40)
        index = self.buttons.count() - 1
        button.clicked.connect(lambda: self._finish(index))
        self.buttons.addWidget(button)
        if role in ("primary", "danger"):
            button.setDefault(True)
            button.setFocus()
        return button

    def _finish(self, index: int):
        self.result_index = index
        self.accept()

    def showEvent(self, event):
        self.adjustSize()
        anchor = self.parentWidget().window() if self.parentWidget() else None
        if anchor is not None and anchor.isVisible():
            center = anchor.frameGeometry().center()
        else:
            screen = QApplication.primaryScreen()
            center = screen.availableGeometry().center() if screen else self.rect().center()
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        super().showEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.windowHandle() is not None:
            self.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), DIALOG_RADIUS, DIALOG_RADIUS)
        painter.fillPath(path, QColor("#0a0a0a"))
        painter.setPen(QPen(QColor("#262626"), 1))
        painter.drawPath(path)


def inform(parent: Optional[QWidget], title: str, text: str, kind: str = "info"):
    dialog = TasjeelDialog(parent, title, text, kind)
    dialog.add_button("OK", "primary")
    dialog.exec()


def confirm(parent: Optional[QWidget], title: str, text: str, confirm_text: str = "Continue",
            cancel_text: str = "Cancel", kind: str = "info", destructive: bool = False) -> bool:
    dialog = TasjeelDialog(parent, title, text, kind)
    dialog.add_button(cancel_text)
    dialog.add_button(confirm_text, "danger" if destructive else "primary")
    return dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_index == 1


def choose(parent: Optional[QWidget], title: str, text: str, options: List[str], kind: str = "info") -> Optional[int]:
    dialog = TasjeelDialog(parent, title, text, kind)
    for position, option in enumerate(options):
        dialog.add_button(option, "primary" if position == len(options) - 1 else "secondary")
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.result_index


def ask_text(parent: Optional[QWidget], title: str, text: str, password: bool = False,
             default: str = "", placeholder: str = "", confirm_text: str = "Continue") -> Optional[str]:
    dialog = TasjeelDialog(parent, title, text)
    field = QLineEdit(default)
    field.setPlaceholderText(placeholder)
    field.setMinimumHeight(40)
    if password:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    dialog.add_body_widget(field)
    dialog.add_button("Cancel")
    dialog.add_button(confirm_text, "primary")
    field.returnPressed.connect(lambda: dialog._finish(1))
    field.setFocus()
    if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result_index != 1:
        return None
    value = field.text()
    return value if value.strip() else None


class ProgressDialog(TasjeelDialog):
    def __init__(self, parent: Optional[QWidget], title: str, text: str = ""):
        super().__init__(parent, title, text, "progress")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.detail = QLabel("")
        self.detail.setObjectName("dialogDetail")
        self.add_body_widget(self.bar)
        self.body.addWidget(self.detail)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def set_progress(self, current: int, total: int, label: str):
        if total > 0:
            self.bar.setRange(0, total)
            self.bar.setValue(current)
            self.detail.setText(f"{label}   {current / 1048576:.1f} of {total / 1048576:.1f} MB")
        else:
            self.bar.setRange(0, 0)
            self.detail.setText(label)
