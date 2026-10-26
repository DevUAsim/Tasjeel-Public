import threading
from typing import Any, Callable, Dict

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from tasjeel.audio.handler import AudioFileLoader, AudioRecorder
from tasjeel.config.settings import settings_manager
from tasjeel.core.transcriber import Transcriber, TranscriptionResult
from tasjeel.managers.api_manager import APIManager
from tasjeel.managers.export_manager import ExportManager
from tasjeel.managers.session_manager import SessionManager
from tasjeel.ui import dialogs
from tasjeel.ui.components import MainContentPanel
from tasjeel.ui.settings import SettingsSheet, model_summary
from tasjeel.ui.styles import get_stylesheet
from tasjeel.utils.recording_controller import RecordingController

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
WINDOW_RADIUS = 24
TIMER_INTERVAL_MS = 1000
UNDO_STACK_MAX_SIZE = 50
AUTO_SAVE_MIN_TEXT_LENGTH = 100


class RootFrame(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), WINDOW_RADIUS, WINDOW_RADIUS)
        painter.fillPath(path, QColor("#000000"))
        painter.setPen(QPen(QColor("#1c1c1c"), 1))
        painter.drawPath(path)


class VoiceTranscriptionApp(QMainWindow):
    intermediate_transcription_ready = pyqtSignal(str)
    final_transcription_ready = pyqtSignal(TranscriptionResult)
    status_updated = pyqtSignal(str)
    vu_meter_updated = pyqtSignal(float)
    stats_update_requested = pyqtSignal(dict)
    chunk_count_updated = pyqtSignal(int)
    download_requested = pyqtSignal(str)
    download_progress = pyqtSignal(int, int, str)
    download_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tasjeel")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._center_on_screen()
        QApplication.instance().setStyleSheet(get_stylesheet())
        self._ui_state = "idle"
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(TIMER_INTERVAL_MS)
        
        self.download_event = threading.Event()
        self.download_response = False
        self.progress_dialog = None
        self.download_requested.connect(self._show_download_dialog)
        self.download_progress.connect(self._update_progress_dialog)
        self.download_finished.connect(self._close_progress_dialog)

        if not self._init_backend():
            self._show_api_error()
            return
        self._create_ui()
        self._init_managers_with_ui()
        self._connect_signals()
        self._init_undo_redo()
        self._set_ui_state("idle")
        if "whisper" in settings_manager.get("TRANSCRIPTION_PROVIDER", "").lower():
            self._set_status("Preparing Whisper model...")
            self.transcriber.preload_whisper()
        self.show()
        self.main_panel.record_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.center().x() - WINDOW_WIDTH // 2, area.center().y() - WINDOW_HEIGHT // 2)

    def _init_backend(self) -> bool:
        self.api_manager = APIManager()
        if not self.api_manager.initialize_api():
            print("Could not initialize Google API. Only local transcription will be available.")

        self.session_manager = SessionManager(api_manager=self.api_manager)
        sample_rate = settings_manager.get_int("SAMPLE_RATE")
        device_id = settings_manager.get("AUDIO_INPUT_DEVICE_ID")

        self.recorder = AudioRecorder(
            sample_rate=sample_rate, vu_update_callback=self._update_vu_meter, device_id=device_id
        )
        self.audio_loader = AudioFileLoader(target_sample_rate=sample_rate)

        self.transcriber = Transcriber(
            gemini_model=self.api_manager.get_model(),
            status_callback=self._set_status,
            intermediate_callback=self._update_intermediate_transcription,
            final_callback=self._on_transcription_finished,
            chunk_count_callback=self._emit_chunk_count,
            download_confirmation_callback=self._ask_download_permission,
            download_progress_callback=self._report_download_progress,
            download_completed_callback=self._report_download_finished,
        )
        return True

    def _show_api_error(self):
        dialogs.inform(self, "Tasjeel could not start",
                       "The transcription backend failed to initialise. Check your configuration and try again.",
                       "error")

    def _ask_download_permission(self, model_name: str) -> bool:
        self.download_response = False
        self.download_event.clear()
        self.download_requested.emit(model_name)
        self.download_event.wait()
        return self.download_response

    def _report_download_progress(self, current: int, total: int, desc: str):
        self.download_progress.emit(current, total, desc)

    def _report_download_finished(self):
        self.download_finished.emit()

    def _show_download_dialog(self, model_name: str):
        self.download_response = dialogs.confirm(
            self,
            "Download speech model",
            f"Whisper '{model_name}' is not on this PC yet. It will be downloaded once from Hugging Face "
            "and then work offline.",
            confirm_text="Download",
            cancel_text="Not now",
        )
        self.download_event.set()

    def _update_progress_dialog(self, current: int, total: int, desc: str):
        if not self.progress_dialog:
            self.progress_dialog = dialogs.ProgressDialog(
                self, "Downloading speech model", "This happens once. Tasjeel works offline afterwards."
            )
            self.progress_dialog.show()
        self.progress_dialog.set_progress(current, total, desc)

    def _close_progress_dialog(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    def _create_ui(self):
        root = RootFrame()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self.main_panel = MainContentPanel()
        layout.addWidget(self.main_panel)
        self.settings_sheet = SettingsSheet(root, self.api_manager.get_api_key() is not None)
        self.main_panel.set_model_label(model_summary())

    def _init_managers_with_ui(self):
        self.recording_controller = RecordingController(
            self, self.recorder, self.transcriber, self.audio_loader
        )
        self.export_manager = ExportManager(
            self, self.main_panel.get_transcription_text
        )

    def _connect_signals(self):
        self.main_panel.toggle_recording.connect(
            self.recording_controller.toggle_recording
        )
        self.main_panel.toggle_pause.connect(self.recording_controller.toggle_pause)
        self.main_panel.upload_audio_file.connect(
            self.recording_controller.upload_audio_file
        )
        self.main_panel.copy_transcription.connect(self._copy_transcription)
        self.main_panel.clear_transcription.connect(self._clear_transcription)
        self.main_panel.show_export_context_menu.connect(self._show_export_context_menu)
        self.main_panel.open_settings_window.connect(self._open_settings_window)
        self.main_panel.new_session_requested.connect(self._new_session)
        self.main_panel.minimize_requested.connect(self.showMinimized)
        self.main_panel.close_requested.connect(self.close)
        self.settings_sheet.provider_changed.connect(self._on_provider_selection)
        self.settings_sheet.whisper_config_changed.connect(self._on_whisper_config_changed)
        self.settings_sheet.audio_device_changed.connect(self._on_audio_device_changed)
        self.settings_sheet.summary_changed.connect(self.main_panel.set_model_label)
        self.settings_sheet.closed.connect(
            lambda: self.main_panel.record_button.setFocus(Qt.FocusReason.OtherFocusReason)
        )
        self.intermediate_transcription_ready.connect(self._handle_intermediate_update)
        self.final_transcription_ready.connect(self._handle_final_update)
        self.status_updated.connect(self.main_panel.update_status)
        self.vu_meter_updated.connect(self.main_panel.update_vu_meter)
        self.stats_update_requested.connect(self._handle_stats_update_request)
        self.chunk_count_updated.connect(self._handle_chunk_count_update)
        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self._undo_transcription)
        QShortcut(QKeySequence.StandardKey.Redo, self, activated=self._redo_transcription)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self._open_settings_window)

    def _update_intermediate_transcription(self, text: str):
        self.intermediate_transcription_ready.emit(text)

    def _emit_chunk_count(self, count: int):
        self.chunk_count_updated.emit(count)

    def _on_provider_selection(self, provider: str):
        if "whisper" in provider.lower():
            if not self.transcriber.whisper_model:
                self._set_status("Preparing Whisper model...")
                self.transcriber.preload_whisper()
        elif self.api_manager.get_model() is None:
            self._set_status("Gemini needs an API key. Add one in Settings, then restart.")

    def _on_whisper_config_changed(self):
        self.transcriber.whisper_model = None
        if "whisper" in self.settings_sheet.provider().lower():
            self._set_status("Preparing Whisper model...")
            self.transcriber.preload_whisper()

    def _on_audio_device_changed(self, device_id):
        self.recorder.device_id = device_id

    def get_transcription_parameters(self) -> Dict[str, Any]:
        return self.settings_sheet.get_transcription_parameters()

    def _on_transcription_finished(self, result: TranscriptionResult):
        self.download_finished.emit()
        self.final_transcription_ready.emit(result)

    def _handle_intermediate_update(self, text: str):
        self.main_panel.set_transcription_text(text)

    def _handle_final_update(self, result: TranscriptionResult):
        self._set_ui_state("idle")
        if result.error:
            self._set_status(f"Error: {result.error}")
            dialogs.inform(self, "Transcription failed", str(result.error), "error")
        else:
            self._set_status("Transcription finished.")
        self.main_panel.set_transcription_text(result.full_text)
        self._push_undo_state()
        has_content = bool(result.full_text.strip())
        if has_content and settings_manager.get_bool("SESSION_AUTO_SAVE"):
            self._auto_save_with_ai_naming(result.full_text)

    def _init_undo_redo(self):
        self._undo_stack = []
        self._redo_stack = []

    def _push_undo_state(self):
        current_text = self.main_panel.get_transcription_text()
        if not self._undo_stack or self._undo_stack[-1] != current_text:
            self._undo_stack.append(current_text)
            if len(self._undo_stack) > UNDO_STACK_MAX_SIZE:
                self._undo_stack.pop(0)
            self._redo_stack.clear()

    def _undo_transcription(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self.main_panel.get_transcription_text())
        self.main_panel.set_transcription_text(self._undo_stack.pop())

    def _redo_transcription(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self.main_panel.get_transcription_text())
        self.main_panel.set_transcription_text(self._redo_stack.pop())

    def _copy_transcription(self):
        QApplication.clipboard().setText(self.main_panel.get_transcription_text())
        self._set_status("Transcription copied to clipboard.")

    def _clear_transcription(self):
        self._push_undo_state()
        self.main_panel.set_transcription_text("")
        self.recording_controller.reset_state()
        self._set_ui_state("idle")

    def _show_export_context_menu(self):
        self.export_manager.show_export_context_menu(self.main_panel.export_button)

    def _open_settings_window(self):
        if self._ui_state != "idle":
            return
        if self.settings_sheet.isVisible():
            self.settings_sheet.close_sheet()
        else:
            self.settings_sheet.open_sheet()

    def _set_status(self, message: str):
        self.status_updated.emit(message)

    def _update_vu_meter(self, level: float):
        self.vu_meter_updated.emit(level)

    def _handle_stats_update_request(self, update: Dict[str, str]):
        self.main_panel.update_stats(
            time_str=update.get("time_str"),
            size_str=update.get("size_str"),
            chunks_str=update.get("chunks_str"),
        )

    def _handle_chunk_count_update(self, count: int):
        self.main_panel.update_stats(chunks_str=str(count))

    def _request_stats_update(
        self,
        time_str: str | None = None,
        size_str: str | None = None,
        chunks_str: str | None = None,
    ):
        update: Dict[str, str] = {}
        if time_str is not None:
            update["time_str"] = time_str
        if size_str is not None:
            update["size_str"] = size_str
        if chunks_str is not None:
            update["chunks_str"] = chunks_str
        if update:
            self.stats_update_requested.emit(update)

    def _set_ui_state(self, state: str):
        self._ui_state = state
        self.main_panel.set_ui_state(state)

    def _new_session(self):
        text = self.main_panel.get_transcription_text()
        if text.strip() and self.session_manager.is_unsaved(
            self.session_manager.current_session_id, text
        ):
            choice = dialogs.choose(
                self,
                "Save this session first?",
                "The current transcript has not been saved yet.",
                ["Cancel", "Discard", "Save"],
                "warning",
            )
            if choice in (None, 0):
                return
            if choice == 2:
                self._save_current_session()
        self._clear_transcription()
        self.session_manager.current_session_id = None
        self._set_status("New session started.")
        self._push_undo_state()

    def _save_current_session(self):
        text = self.main_panel.get_transcription_text()
        if not text.strip():
            self._set_status("Nothing to save.")
            return
        session_name = None
        if (
            not settings_manager.get_bool("AI_GENERATE_SESSION_NAMES")
            or self.session_manager.current_session_id
        ):
            current_session = self.session_manager.load_session(
                self.session_manager.current_session_id
            )
            fallback_name = (
                current_session.get("name")
                if current_session
                else self.session_manager._generate_fallback_name(text)
            )
            name = dialogs.ask_text(self, "Save session", "Give this session a name.",
                                    default=fallback_name, confirm_text="Save")
            if not name:
                self._set_status("Save cancelled.")
                return
            session_name = name.strip()
        session_id = self.session_manager.save_session(
            transcription_text=text,
            metadata=self.get_transcription_parameters(),
            session_id=self.session_manager.current_session_id,
            session_name=session_name,
        )
        if session_id:
            self.session_manager.current_session_id = session_id
            saved = self.session_manager.load_session(session_id)
            self._set_status(f"Session saved as '{saved['name']}'.")
        else:
            self._set_status("Failed to save session.")
            dialogs.inform(self, "Could not save", "The session could not be written to disk.", "error")

    def _auto_save_with_ai_naming(self, text: str):
        if self.session_manager.current_session_id or len(text.strip()) < AUTO_SAVE_MIN_TEXT_LENGTH:
            return
        self._set_status("Auto-saving session...")
        session_id = self.session_manager.save_session(
            transcription_text=text,
            metadata=self.get_transcription_parameters(),
            session_name=None,
        )
        if session_id:
            self.session_manager.current_session_id = session_id
            saved = self.session_manager.load_session(session_id)
            if saved:
                self._set_status(f"Auto-saved as '{saved['name']}'.")

    def start_elapsed_timer(self, time_provider_callback: Callable[[], str]):
        try:
            self.elapsed_timer.timeout.disconnect()
        except TypeError:
            pass
        self.elapsed_timer.timeout.connect(
            lambda: self.main_panel.update_stats(time_str=time_provider_callback())
        )
        self.elapsed_timer.start()

    def stop_elapsed_timer(self):
        if self.elapsed_timer.isActive():
            self.elapsed_timer.stop()

    def closeEvent(self, event):
        self.recording_controller.reset_state()
        super().closeEvent(event)
