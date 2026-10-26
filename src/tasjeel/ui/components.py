import math
from collections import deque
from typing import Optional

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QPainter, QPen, QTextBlockFormat,
                         QTextCursor)
from PyQt6.QtWidgets import (QAbstractButton, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QPushButton, QSizePolicy, QStackedWidget,
                             QTextEdit, QVBoxLayout, QWidget)

from tasjeel.ui.icons import svg_icon, svg_pixmap

RED = "#ff453a"
TEXT = "#f5f5f5"
MUTED = "#8f8f8f"
ICON_IDLE = "#a3a3a3"
MONO_FONT = "Cascadia Mono"
METER_BARS = 56
METER_TICK_MS = 45
METER_FLOOR_DB = -55.0
METER_CEIL_DB = -12.0

STATE_STYLES = {
    "idle": ("#30d158", "Idle", MUTED),
    "recording": (RED, "Live", RED),
    "paused": ("#ffd60a", "Paused", "#ffd60a"),
    "processing": ("#0a84ff", "Working", "#a3a3a3"),
}


class IconButton(QPushButton):
    def __init__(self, icon_name: str, tooltip: str, size: int = 36, icon_size: int = 17, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._icon_size = icon_size
        self.setObjectName("iconButton")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFixedSize(size, size)
        self.setIconSize(QSize(icon_size, icon_size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_tooltip(tooltip)
        self._paint_icon(ICON_IDLE)

    def set_tooltip(self, tooltip: str):
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)

    def set_icon_name(self, icon_name: str):
        self._icon_name = icon_name
        self._paint_icon(TEXT if self.underMouse() else ICON_IDLE)

    def _paint_icon(self, color: str):
        self.setIcon(svg_icon(self._icon_name, color, self._icon_size))

    def enterEvent(self, event):
        if self.isEnabled():
            self._paint_icon(TEXT)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._paint_icon(ICON_IDLE)
        super().leaveEvent(event)

    def changeEvent(self, event):
        if event.type() == event.Type.EnabledChange:
            self._paint_icon(ICON_IDLE if self.isEnabled() else "#3a3a3a")
        super().changeEvent(event)


class GhostButton(QPushButton):
    def __init__(self, icon_name: str, text: str, tooltip: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("ghostButton")
        self.setIcon(svg_icon(icon_name, "#d4d4d4", 16))
        self.setIconSize(QSize(16, 16))
        self.setFixedHeight(44)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)


class ElidedLabel(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), int(self.alignment()), text)

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())


class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#30d158")
        self.setFixedSize(8, 8)

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(QRectF(0.5, 0.5, 7, 7))


class TitleBar(QWidget):
    settings_clicked = pyqtSignal()
    minimize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 16, 0)
        layout.setSpacing(0)

        brand = QWidget()
        brand.setFixedWidth(200)
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(svg_pixmap("quill", "#ffffff", 22, stroke_width=1.6))
        logo.setFixedSize(22, 22)
        wordmark = QLabel("تسجيل")
        wordmark.setObjectName("wordmark")
        wordmark.setAccessibleName("Tasjeel")
        wordmark_font = QFont("Segoe UI", 15)
        wordmark_font.setWeight(QFont.Weight.Bold)
        wordmark.setFont(wordmark_font)
        brand_layout.addWidget(logo)
        brand_layout.addWidget(wordmark)
        brand_layout.addStretch(1)

        status = QWidget()
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        self.status_dot = StatusDot()
        self.status_label = ElidedLabel("Ready")
        self.status_label.setObjectName("statusText")
        self.status_label.setMaximumWidth(330)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        separator = QLabel("·")
        separator.setObjectName("mutedText")
        self.model_label = QLabel("")
        self.model_label.setObjectName("modelText")
        status_layout.addStretch(1)
        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(separator)
        status_layout.addWidget(self.model_label)
        status_layout.addStretch(1)

        controls = QWidget()
        controls.setFixedWidth(200)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        controls_layout.addStretch(1)
        self.settings_button = IconButton("sliders", "Settings and context instructions", icon_size=18)
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        divider = QFrame()
        divider.setObjectName("vDivider")
        divider.setFixedSize(1, 20)
        self.minimize_button = IconButton("minus", "Minimize", icon_size=16)
        self.minimize_button.clicked.connect(self.minimize_clicked.emit)
        self.close_button = IconButton("close", "Close", icon_size=16)
        self.close_button.clicked.connect(self.close_clicked.emit)
        controls_layout.addWidget(self.settings_button)
        controls_layout.addSpacing(4)
        controls_layout.addWidget(divider)
        controls_layout.addSpacing(4)
        controls_layout.addWidget(self.minimize_button)
        controls_layout.addWidget(self.close_button)

        layout.addWidget(brand)
        layout.addWidget(status, 1)
        layout.addWidget(controls)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(event)


class LevelMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip("Microphone input level")
        self.setAccessibleName("Microphone input level")
        self._levels = deque([0.0] * METER_BARS, maxlen=METER_BARS)
        self._latest = 0.0
        self._state = "idle"
        self._timer = QTimer(self)
        self._timer.setInterval(METER_TICK_MS)
        self._timer.timeout.connect(self._tick)

    def set_state(self, state: str):
        self._state = state
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def set_level(self, rms: float):
        if rms <= 0:
            self._latest = 0.0
            return
        db = 20 * math.log10(max(rms, 1e-7))
        self._latest = max(0.0, min(1.0, (db - METER_FLOOR_DB) / (METER_CEIL_DB - METER_FLOOR_DB)))

    def _tick(self):
        if self._state == "recording":
            self._levels.append(self._latest)
        else:
            decayed = [value * 0.6 for value in self._levels]
            self._levels = deque(decayed, maxlen=METER_BARS)
            if max(decayed) < 0.01:
                self._levels = deque([0.0] * METER_BARS, maxlen=METER_BARS)
                self._timer.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        gap = 3.0
        width = self.width()
        height = self.height()
        bar_width = (width - gap * (METER_BARS - 1)) / METER_BARS
        if self._state == "recording":
            base = QColor(RED)
        elif self._state == "paused":
            base = QColor("#5c5c5c")
        else:
            base = QColor("#262626")
        peak = QColor("#ff8a80")
        for index, value in enumerate(self._levels):
            bar_height = 4 + value * (height - 4)
            x = index * (bar_width + gap)
            y = (height - bar_height) / 2
            painter.setBrush(peak if value > 0.85 and self._state == "recording" else base)
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_height), 1.5, 1.5)


class RecordButton(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(112, 112)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._state = "idle"
        self._phase = 0.0
        self._hover = False
        self._keyboard_focus = False
        self._pulse = QTimer(self)
        self._pulse.setInterval(30)
        self._pulse.timeout.connect(self._advance_pulse)
        self.set_state("idle")

    def set_state(self, state: str):
        self._state = state
        tips = {
            "idle": "Start recording",
            "recording": "Stop and transcribe",
            "paused": "Stop and transcribe",
            "processing": "Transcribing, please wait",
        }
        self.setToolTip(tips[state])
        self.setAccessibleName(tips[state])
        self.setEnabled(state != "processing")
        if state == "recording":
            self._pulse.start()
        else:
            self._pulse.stop()
            self._phase = 0.0
        self.update()

    def _advance_pulse(self):
        self._phase = (self._phase + 30 / 1600) % 1.0
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def sizeHint(self):
        return QSize(112, 112)

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._keyboard_focus = False
        super().focusOutEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = 42.0
        live = self._state in ("recording", "paused")

        if self._state == "recording":
            spread = self._phase * 14
            alpha = int(115 * (1 - self._phase))
            pulse_color = QColor(RED)
            pulse_color.setAlpha(alpha)
            painter.setPen(QPen(pulse_color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(center_x - radius - spread, center_y - radius - spread,
                                       (radius + spread) * 2, (radius + spread) * 2))

        ring = QColor(RED) if live else QColor("#3a3a3a" if self._hover else "#2e2e2e")
        if self.hasFocus() and self._keyboard_focus:
            ring = QColor("#ffffff")
        painter.setPen(QPen(ring, 3))
        painter.setBrush(QColor("#000000"))
        painter.drawEllipse(QRectF(center_x - radius + 1.5, center_y - radius + 1.5,
                                   radius * 2 - 3, radius * 2 - 3))

        painter.setPen(Qt.PenStyle.NoPen)
        if live:
            painter.setBrush(QColor(RED))
            side = 28.0
            painter.drawRoundedRect(QRectF(center_x - side / 2, center_y - side / 2, side, side), 7, 7)
        else:
            dot = 31.0 + (1.5 if self._hover and self.isEnabled() else 0.0)
            painter.setBrush(QColor(RED) if self.isEnabled() else QColor("#5a1d19"))
            painter.drawEllipse(QRectF(center_x - dot, center_y - dot, dot * 2, dot * 2))


class Spinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._rotate)

    def _rotate(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def showEvent(self, event):
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(3, 3, 22, 22)
        painter.setPen(QPen(QColor("#2a2a2a"), 2.5))
        painter.drawEllipse(rect)
        pen = QPen(QColor(TEXT), 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, -self._angle * 16, 90 * 16)


class EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addStretch(1)
        self.icon_box = QLabel()
        self.icon_box.setObjectName("emptyIcon")
        self.icon_box.setFixedSize(56, 56)
        self.icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_box.setPixmap(svg_pixmap("mic", MUTED, 24))
        self.spinner = Spinner()
        self.title = QLabel()
        self.title.setObjectName("emptyTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("emptySubtitle")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setWordWrap(True)
        self.subtitle.setFixedWidth(400)
        self.subtitle.setMinimumHeight(46)
        layout.addWidget(self.icon_box, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.title, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.subtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.set_busy(False)

    def set_busy(self, busy: bool):
        self.icon_box.setVisible(not busy)
        self.spinner.setVisible(busy)
        if busy:
            self.title.setText("Transcribing")
            self.subtitle.setText("Running on this PC. Text appears here as each part is finished.")
        else:
            self.title.setText("Press the red button to start")
            self.subtitle.setText("Your words appear here once you stop. You can also open an existing audio file.")


class MainContentPanel(QWidget):
    toggle_recording = pyqtSignal()
    toggle_pause = pyqtSignal()
    upload_audio_file = pyqtSignal()
    copy_transcription = pyqtSignal()
    clear_transcription = pyqtSignal()
    show_export_context_menu = pyqtSignal()
    open_settings_window = pyqtSignal()
    new_session_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "idle"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_bar = TitleBar()
        self.title_bar.settings_clicked.connect(self.open_settings_window.emit)
        self.title_bar.minimize_clicked.connect(self.minimize_requested.emit)
        self.title_bar.close_clicked.connect(self.close_requested.emit)
        layout.addWidget(self.title_bar)
        layout.addWidget(self._hairline())
        layout.addWidget(self._create_transcript(), 1)
        layout.addWidget(self._hairline())
        layout.addWidget(self._create_dock())

    def _hairline(self) -> QFrame:
        line = QFrame()
        line.setObjectName("hairline")
        line.setFixedHeight(1)
        return line

    def _create_transcript(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 14, 20, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(4)
        title = QLabel("Transcript")
        title.setObjectName("sectionTitle")
        self.word_count_label = QLabel("")
        self.word_count_label.setObjectName("mutedText")
        self.copy_button = IconButton("copy", "Copy transcript")
        self.export_button = IconButton("export", "Export as TXT, DOCX, PDF, HTML or JSON")
        self.clear_button = IconButton("trash", "Clear transcript (Ctrl+Z to undo)")
        self.copy_button.clicked.connect(self.copy_transcription.emit)
        self.export_button.clicked.connect(self.show_export_context_menu.emit)
        self.clear_button.clicked.connect(self.clear_transcription.emit)
        header.addWidget(title)
        header.addSpacing(8)
        header.addWidget(self.word_count_label)
        header.addStretch(1)
        header.addWidget(self.copy_button)
        header.addWidget(self.export_button)
        header.addWidget(self.clear_button)
        layout.addLayout(header)

        self.stack = QStackedWidget()
        self.empty_state = EmptyState()
        self.transcription_text = QTextEdit()
        self.transcription_text.setObjectName("transcript")
        self.transcription_text.setReadOnly(True)
        self.transcription_text.setFrameShape(QFrame.Shape.NoFrame)
        self.transcription_text.document().setDocumentMargin(0)
        self.stack.addWidget(self.empty_state)
        self.stack.addWidget(self.transcription_text)
        layout.addWidget(self.stack, 1)
        return container

    def _create_dock(self) -> QWidget:
        dock = QWidget()
        dock.setFixedHeight(200)
        layout = QVBoxLayout(dock)
        layout.setContentsMargins(24, 16, 24, 14)
        layout.setSpacing(4)

        meter_row = QHBoxLayout()
        meter_row.setSpacing(16)
        self.elapsed_time_label = QLabel("00:00")
        self.elapsed_time_label.setObjectName("timerText")
        mono = QFont(MONO_FONT, 11)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.elapsed_time_label.setFont(mono)
        self.elapsed_time_label.setFixedWidth(64)
        self.elapsed_time_label.setToolTip("Recording length")
        self.vu_meter = LevelMeter()
        self.state_label = QLabel("Idle")
        self.state_label.setFixedWidth(76)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        state_font = QFont("Segoe UI", 9)
        state_font.setWeight(QFont.Weight.DemiBold)
        state_font.setCapitalization(QFont.Capitalization.AllUppercase)
        state_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        self.state_label.setFont(state_font)
        meter_row.addWidget(self.elapsed_time_label)
        meter_row.addWidget(self.vu_meter, 1)
        meter_row.addWidget(self.state_label)
        layout.addLayout(meter_row)

        controls = QGridLayout()
        controls.setHorizontalSpacing(16)
        controls.setColumnStretch(0, 1)
        controls.setColumnStretch(2, 1)

        self.upload_button = GhostButton("upload", "Open file", "Transcribe an audio file (MP3, WAV, M4A, FLAC, OGG)")
        self.upload_button.clicked.connect(self.upload_audio_file.emit)

        center = QHBoxLayout()
        center.setSpacing(12)
        self.pause_button = IconButton("pause", "Pause recording", size=52, icon_size=18)
        self.pause_button.setObjectName("roundButton")
        policy = self.pause_button.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.pause_button.setSizePolicy(policy)
        self.pause_button.clicked.connect(self.toggle_pause.emit)
        self.record_button = RecordButton()
        self.record_button.clicked.connect(self.toggle_recording.emit)
        spacer = QWidget()
        spacer.setFixedSize(52, 52)
        center.addWidget(self.pause_button)
        center.addWidget(self.record_button)
        center.addWidget(spacer)

        self.new_session_button = GhostButton("plus", "New session", "Start fresh (finished sessions are auto-saved)")
        self.new_session_button.clicked.connect(self.new_session_requested.emit)

        controls.addWidget(self.upload_button, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        controls.addLayout(center, 0, 1, Qt.AlignmentFlag.AlignCenter)
        controls.addWidget(self.new_session_button, 0, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(controls, 1)
        return dock

    def set_ui_state(self, state: str):
        self._state = state
        is_idle = state == "idle"
        live = state in ("recording", "paused")
        self.record_button.set_state(state)
        self.pause_button.setVisible(live)
        if state == "paused":
            self.pause_button.set_icon_name("play")
            self.pause_button.set_tooltip("Resume recording")
        else:
            self.pause_button.set_icon_name("pause")
            self.pause_button.set_tooltip("Pause recording")
        self.vu_meter.set_state(state)
        dot_color, label, label_color = STATE_STYLES[state]
        self.title_bar.status_dot.set_color(dot_color)
        self.state_label.setText(label)
        self.state_label.setStyleSheet(f"color: {label_color};")
        self.elapsed_time_label.setStyleSheet(f"color: {TEXT if live else MUTED};")
        for widget in (self.upload_button, self.new_session_button, self.clear_button,
                       self.export_button, self.title_bar.settings_button):
            widget.setEnabled(is_idle)
        self.update_status({"idle": "Ready", "recording": "Recording", "paused": "Paused",
                            "processing": "Transcribing"}[state])
        if is_idle:
            self.update_vu_meter(0)
        if self.record_button.isEnabled():
            self.record_button.setFocus(Qt.FocusReason.OtherFocusReason)
        self._refresh_page()

    def update_status(self, message: str):
        self.title_bar.status_label.setText(message)
        self.title_bar.status_label.setToolTip(message)
        self.title_bar.status_label.update()

    def set_model_label(self, text: str):
        self.title_bar.model_label.setText(text)

    def update_vu_meter(self, level: float):
        self.vu_meter.set_level(level)

    def update_stats(self, time_str: Optional[str] = None, size_str: Optional[str] = None, chunks_str: Optional[str] = None):
        if time_str is not None:
            self.elapsed_time_label.setText(time_str)
        if size_str is not None:
            self.elapsed_time_label.setToolTip(f"Recording length  ·  {size_str}")

    def get_transcription_text(self) -> str:
        return self.transcription_text.toPlainText()

    def set_transcription_text(self, text: str):
        self.transcription_text.setPlainText(text)
        cursor = QTextCursor(self.transcription_text.document())
        cursor.select(QTextCursor.SelectionType.Document)
        block_format = QTextBlockFormat()
        block_format.setLineHeight(150, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor.mergeBlockFormat(block_format)
        self.transcription_text.moveCursor(QTextCursor.MoveOperation.End)
        words = len(text.split())
        self.word_count_label.setText(f"{words} words" if words else "")
        self._refresh_page()

    def append_transcription_text(self, text: str):
        self.set_transcription_text(self.get_transcription_text() + text)

    def _refresh_page(self):
        has_text = bool(self.get_transcription_text().strip())
        self.empty_state.set_busy(self._state == "processing")
        self.stack.setCurrentWidget(self.transcription_text if has_text else self.empty_state)
