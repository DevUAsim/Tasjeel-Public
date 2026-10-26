from typing import Any, Dict, Optional

from PyQt6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt,
                          pyqtSignal)
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFormLayout,
                             QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from tasjeel.audio.handler import get_audio_input_devices
from tasjeel.config.settings import SUPPORTED_LANGUAGES, settings_manager
from tasjeel.ui import dialogs
from tasjeel.ui.components import IconButton
from tasjeel.utils.key_manager import save_api_key, validate_api_key

SHEET_WIDTH = 420
WINDOW_RADIUS = 23
MASKED_KEY_DISPLAY = "********"
WHISPER_PROVIDER = "Whisper (Local)"
GEMINI_PROVIDER = "Gemini (Cloud)"
WHISPER_MODEL_CHOICES = [
    ("small.en", "small.en  (recommended)"),
    ("distil-small.en", "distil small.en  (fastest)"),
    ("base.en", "base.en  (lightest)"),
    ("tiny.en", "tiny.en"),
    ("medium.en", "medium.en  (slow on CPU)"),
    ("distil-medium.en", "distil medium.en"),
    ("distil-large-v3", "distil large-v3  (GPU)"),
    ("large-v3-turbo", "large-v3 turbo  (GPU)"),
    ("large-v3", "large-v3  (GPU)"),
]
COMPUTE_CHOICES = [
    ("cpu", "int8", "CPU · int8  (recommended)"),
    ("cpu", "float32", "CPU · float32"),
    ("cuda", "float16", "NVIDIA GPU · float16"),
    ("cuda", "int8_float16", "NVIDIA GPU · int8"),
]
SPEAKER_CHOICES = ["1 Speaker", "2 Speakers", "Multiple Speakers"]
NOISE_CHOICES = ["Low", "Medium", "High"]


def model_summary() -> str:
    if "gemini" in (settings_manager.get("TRANSCRIPTION_PROVIDER") or "").lower():
        return f"Gemini · {settings_manager.get('GEMINI_MODEL_NAME')}"
    model = settings_manager.get("WHISPER_MODEL") or ""
    device = (settings_manager.get("WHISPER_DEVICE") or "cpu").upper()
    compute = settings_manager.get("WHISPER_COMPUTE_TYPE") or ""
    if device == "CUDA":
        device = "GPU"
    return f"Whisper {model} · {device} {compute}".strip()


class SettingsSheet(QWidget):
    provider_changed = pyqtSignal(str)
    whisper_config_changed = pyqtSignal()
    audio_device_changed = pyqtSignal(object)
    summary_changed = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent: QWidget, api_key_exists: bool):
        super().__init__(parent)
        self.api_key_exists = api_key_exists
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.panel = QFrame(self)
        self.panel.setObjectName("sheetPanel")
        self._animation = QPropertyAnimation(self.panel, b"pos", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._build()
        self._load()
        self.hide()

    def _build(self):
        outer = QVBoxLayout(self.panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(64)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 16, 0)
        title = QLabel("Settings")
        title.setObjectName("sheetTitle")
        close_button = IconButton("close", "Close (changes save automatically)", icon_size=16)
        close_button.clicked.connect(self.close_sheet)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        header_layout.addWidget(close_button)
        outer.addWidget(header)
        outer.addWidget(self._hairline())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 8, 24, 28)
        layout.setSpacing(0)

        layout.addWidget(self._section_label("Context instructions"))
        hint = QLabel("Names, terms or spellings the transcriber should expect")
        hint.setObjectName("fieldLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addSpacing(8)
        self.context_edit = QPlainTextEdit()
        self.context_edit.setPlaceholderText("e.g. Speaker names, product names, technical terms")
        self.context_edit.setFixedHeight(104)
        layout.addWidget(self.context_edit)

        layout.addSpacing(24)
        layout.addWidget(self._hairline())
        layout.addWidget(self._section_label("Transcription"))

        engine_form = self._form()
        segment = QFrame()
        segment.setObjectName("segmentGroup")
        segment_layout = QHBoxLayout(segment)
        segment_layout.setContentsMargins(3, 3, 3, 3)
        segment_layout.setSpacing(0)
        self.whisper_button = QPushButton("Whisper (local)")
        self.whisper_button.setToolTip("Runs offline on this PC")
        self.gemini_button = QPushButton("Gemini (cloud)")
        self.gemini_button.setToolTip("Sends audio to Google Gemini. Needs an API key.")
        self.engine_group = QButtonGroup(self)
        for button in (self.whisper_button, self.gemini_button):
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.engine_group.addButton(button)
            segment_layout.addWidget(button)
        engine_form.addRow(self._field_label("Engine"), segment)
        layout.addWidget(self._wrap(engine_form))

        self.whisper_section = QWidget()
        whisper_form = self._form()
        self.whisper_section.setLayout(whisper_form)
        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Downloaded once from Hugging Face, then works offline")
        for model, label in WHISPER_MODEL_CHOICES:
            self.model_combo.addItem(label, model)
        self.compute_combo = QComboBox()
        self.compute_combo.setToolTip("int8 is fastest on CPUs without an NVIDIA GPU")
        for device, compute, label in COMPUTE_CHOICES:
            self.compute_combo.addItem(label, f"{device}|{compute}")
        whisper_form.addRow(self._field_label("Model"), self.model_combo)
        whisper_form.addRow(self._field_label("Compute"), self.compute_combo)
        note = QLabel("small.en with int8 runs comfortably on a laptop CPU with 8 GB of RAM. "
                      "The .en models transcribe English only.")
        note.setObjectName("noteText")
        note.setWordWrap(True)
        whisper_form.addRow(note)
        layout.addWidget(self.whisper_section)

        self.gemini_section = QWidget()
        gemini_form = self._form()
        self.gemini_section.setLayout(gemini_form)
        self.api_key_entry = QLineEdit()
        self.api_key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        set_key_button = QPushButton("Save")
        set_key_button.setToolTip("Check and store the key, encrypted, on this PC")
        set_key_button.clicked.connect(self._set_api_key)
        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(8)
        key_layout.addWidget(self.api_key_entry, 1)
        key_layout.addWidget(set_key_button)
        self.gemini_model_entry = QLineEdit()
        self.language_combo = QComboBox()
        self.language_combo.addItems(SUPPORTED_LANGUAGES)
        self.speakers_combo = QComboBox()
        self.speakers_combo.addItems(SPEAKER_CHOICES)
        self.noise_combo = QComboBox()
        self.noise_combo.addItems(NOISE_CHOICES)
        gemini_form.addRow(self._field_label("API key"), key_row)
        gemini_form.addRow(self._field_label("Gemini model"), self.gemini_model_entry)
        gemini_form.addRow(self._field_label("Language"), self.language_combo)
        gemini_form.addRow(self._field_label("Speakers"), self.speakers_combo)
        gemini_form.addRow(self._field_label("Background noise"), self.noise_combo)
        layout.addWidget(self.gemini_section)

        layout.addSpacing(24)
        layout.addWidget(self._hairline())
        layout.addWidget(self._section_label("Audio and sessions"))
        audio_form = self._form()
        self.mic_combo = QComboBox()
        self.autosave_checkbox = QCheckBox("Auto-save finished sessions")
        audio_form.addRow(self._field_label("Microphone"), self.mic_combo)
        audio_form.addRow(self.autosave_checkbox)
        layout.addWidget(self._wrap(audio_form))
        layout.addStretch(1)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    def _hairline(self) -> QFrame:
        line = QFrame()
        line.setObjectName("hairline")
        line.setFixedHeight(1)
        return line

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        font = QFont("Segoe UI", 8)
        font.setWeight(QFont.Weight.DemiBold)
        font.setCapitalization(QFont.Capitalization.AllUppercase)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        label.setFont(font)
        label.setContentsMargins(0, 18, 0, 12)
        return label

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        label.setFixedWidth(116)
        return label

    def _form(self) -> QFormLayout:
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 14)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return form

    def _wrap(self, form: QFormLayout) -> QWidget:
        widget = QWidget()
        widget.setLayout(form)
        return widget

    def _load(self):
        provider = settings_manager.get("TRANSCRIPTION_PROVIDER") or WHISPER_PROVIDER
        (self.gemini_button if "gemini" in provider.lower() else self.whisper_button).setChecked(True)
        self._sync_engine_sections()

        model = settings_manager.get("WHISPER_MODEL") or WHISPER_MODEL_CHOICES[0][0]
        index = self.model_combo.findData(model)
        if index < 0:
            self.model_combo.addItem(model, model)
            index = self.model_combo.count() - 1
        self.model_combo.setCurrentIndex(index)

        device = settings_manager.get("WHISPER_DEVICE") or "cpu"
        compute = settings_manager.get("WHISPER_COMPUTE_TYPE") or "int8"
        index = self.compute_combo.findData(f"{device}|{compute}")
        if index < 0:
            self.compute_combo.addItem(f"{device} · {compute}", f"{device}|{compute}")
            index = self.compute_combo.count() - 1
        self.compute_combo.setCurrentIndex(index)

        if self.api_key_exists:
            self.api_key_entry.setText(MASKED_KEY_DISPLAY)
        else:
            self.api_key_entry.setPlaceholderText("Paste a Google Gemini API key")
        self.gemini_model_entry.setText(settings_manager.get("GEMINI_MODEL_NAME") or "")
        self._set_combo_text(self.language_combo, settings_manager.get("LAST_TRANSCRIPTION_LANGUAGE", "English"))
        self._set_combo_text(self.speakers_combo, settings_manager.get("LAST_TRANSCRIPTION_SPEAKERS", "1 Speaker"))
        self._set_combo_text(self.noise_combo, settings_manager.get("LAST_TRANSCRIPTION_NOISE", "Low"))
        self.context_edit.setPlainText(settings_manager.get("LAST_CONTEXT_NOTES") or "")
        self.autosave_checkbox.setChecked(settings_manager.get_bool("SESSION_AUTO_SAVE"))
        self._populate_microphones()

        self.engine_group.buttonClicked.connect(self._on_engine_changed)
        self.model_combo.currentIndexChanged.connect(self._on_whisper_changed)
        self.compute_combo.currentIndexChanged.connect(self._on_whisper_changed)
        self.gemini_model_entry.editingFinished.connect(self._on_gemini_model_changed)
        self.language_combo.currentTextChanged.connect(lambda v: self._store("LAST_TRANSCRIPTION_LANGUAGE", v))
        self.speakers_combo.currentTextChanged.connect(lambda v: self._store("LAST_TRANSCRIPTION_SPEAKERS", v))
        self.noise_combo.currentTextChanged.connect(lambda v: self._store("LAST_TRANSCRIPTION_NOISE", v))
        self.autosave_checkbox.toggled.connect(lambda v: self._store("SESSION_AUTO_SAVE", v))
        self.mic_combo.currentIndexChanged.connect(self._on_mic_changed)

    def _set_combo_text(self, combo: QComboBox, text: Optional[str]):
        if text and combo.findText(text) >= 0:
            combo.setCurrentText(text)

    def _populate_microphones(self):
        current = settings_manager.get("AUDIO_INPUT_DEVICE_ID")
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItem("System default", None)
        for device in get_audio_input_devices():
            self.mic_combo.addItem(device["name"], device["id"])
        index = self.mic_combo.findData(current)
        self.mic_combo.setCurrentIndex(index if index >= 0 else 0)
        self.mic_combo.blockSignals(False)

    def _store(self, key: str, value: Any):
        settings_manager.set(key, value)
        settings_manager.save()

    def provider(self) -> str:
        return GEMINI_PROVIDER if self.gemini_button.isChecked() else WHISPER_PROVIDER

    def _sync_engine_sections(self):
        gemini = self.gemini_button.isChecked()
        self.whisper_section.setVisible(not gemini)
        self.gemini_section.setVisible(gemini)

    def _on_engine_changed(self):
        self._sync_engine_sections()
        provider = self.provider()
        self._store("TRANSCRIPTION_PROVIDER", provider)
        self.provider_changed.emit(provider)
        self.summary_changed.emit(model_summary())

    def _on_whisper_changed(self):
        device, compute = self.compute_combo.currentData().split("|", 1)
        settings_manager.set("WHISPER_MODEL", self.model_combo.currentData())
        settings_manager.set("WHISPER_DEVICE", device)
        settings_manager.set("WHISPER_COMPUTE_TYPE", compute)
        settings_manager.save()
        self.whisper_config_changed.emit()
        self.summary_changed.emit(model_summary())

    def _on_gemini_model_changed(self):
        name = self.gemini_model_entry.text().strip()
        if name and name != settings_manager.get("GEMINI_MODEL_NAME"):
            self._store("GEMINI_MODEL_NAME", name)
            self.summary_changed.emit(model_summary())

    def _on_mic_changed(self):
        device_id = self.mic_combo.currentData()
        self._store("AUDIO_INPUT_DEVICE_ID", device_id)
        self.audio_device_changed.emit(device_id)

    def _set_api_key(self):
        new_key = self.api_key_entry.text().strip()
        if not new_key or new_key == MASKED_KEY_DISPLAY:
            dialogs.inform(self, "No key entered", "Paste a Google Gemini API key first.", "warning")
            return
        result = validate_api_key(new_key)
        if result is True:
            if not save_api_key(new_key):
                return
            self.api_key_entry.setText(MASKED_KEY_DISPLAY)
            self.api_key_exists = True
            dialogs.inform(self, "API key saved", "Restart Tasjeel to start using Gemini.", "success")
        else:
            dialogs.inform(self, "Key not accepted", str(result), "error")

    def get_transcription_parameters(self) -> Dict[str, Any]:
        return {
            "provider": self.provider(),
            "language": self.language_combo.currentText(),
            "speakers": self.speakers_combo.currentText(),
            "noise": self.noise_combo.currentText(),
            "user_notes": self.context_edit.toPlainText(),
        }

    def open_sheet(self):
        parent = self.parentWidget()
        self.setGeometry(parent.rect().adjusted(1, 1, -1, -1))
        self.panel.setFixedSize(SHEET_WIDTH, self.height())
        self._populate_microphones()
        self.show()
        self.raise_()
        self.setFocus()
        self._animation.stop()
        self._animation.setStartValue(QPoint(self.width(), 0))
        self._animation.setEndValue(QPoint(self.width() - SHEET_WIDTH, 0))
        self._animation.start()

    def close_sheet(self):
        self._on_gemini_model_changed()
        self._store("LAST_CONTEXT_NOTES", self.context_edit.toPlainText())
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event):
        if not self.panel.geometry().contains(event.position().toPoint()):
            self.close_sheet()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_sheet()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), WINDOW_RADIUS, WINDOW_RADIUS)
        painter.fillPath(path, QColor(0, 0, 0, 180))
