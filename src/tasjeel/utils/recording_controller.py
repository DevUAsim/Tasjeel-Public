import os
import threading
import time
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtWidgets import QFileDialog

from tasjeel.config.settings import settings_manager

if TYPE_CHECKING:
    from tasjeel.core.app import VoiceTranscriptionApp

from tasjeel.audio.handler import AudioFileLoader, AudioRecorder
from tasjeel.core.transcriber import (Transcriber, TranscriptionParams,
                                      TranscriptionResult)


class RecordingController:
    def __init__(
        self,
        app: "VoiceTranscriptionApp",
        recorder: AudioRecorder,
        transcriber: Transcriber,
        audio_loader: AudioFileLoader,
    ):
        self.app = app
        self.recorder = recorder
        self.transcriber = transcriber
        self.audio_loader = audio_loader
        self.start_time = 0.0
        self.paused_total = 0.0
        self.pause_started = None

    def toggle_recording(self):
        if not self.recorder.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self.app._clear_transcription()
        self.recorder.start()
        self.app._set_ui_state("recording")
        self.start_time = time.time()
        self.paused_total = 0.0
        self.pause_started = None
        self.app._request_stats_update(time_str="00:00")
        self.app.start_elapsed_timer(self._get_elapsed_time_str)

    def toggle_pause(self):
        if not self.recorder.is_recording:
            return
        if self.recorder.is_paused:
            self.recorder.resume()
            if self.pause_started is not None:
                self.paused_total += time.time() - self.pause_started
            self.pause_started = None
            self.app._set_ui_state("recording")
        else:
            self.recorder.pause()
            self.pause_started = time.time()
            self.app._set_ui_state("paused")

    def _stop_recording(self):
        self.app.stop_elapsed_timer()
        self.app._set_ui_state("processing")
        self.app._set_status("Finalizing recording...")
        self.pause_started = None
        audio_data = self.recorder.stop()
        params = self._capture_transcription_params()
        if audio_data is not None and audio_data.size > 0:
            total_bytes = audio_data.nbytes
            total_mb = total_bytes / (1024 * 1024)
            self.app._request_stats_update(size_str=f"{total_mb:.2f} MB")
            threading.Thread(
                target=self._run_transcription_task,
                args=(audio_data, self.recorder.sample_rate, params),
                daemon=True,
            ).start()
        else:
            self.app._set_status("No audio was recorded.")
            self.app._set_ui_state("idle")

    def upload_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.app,
            "Select Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.ogg *.flac);;All Files (*)",
        )
        if not file_path:
            self.app._set_status("File selection cancelled.")
            return
        self.app._clear_transcription()
        self.app._set_ui_state("processing")
        self.app._set_status(f"Loading file: {os.path.basename(file_path)}...")
        params = self._capture_transcription_params()
        threading.Thread(
            target=self._load_and_process_audio_file, args=(file_path, params), daemon=True
        ).start()

    def _load_and_process_audio_file(self, file_path: str, params: TranscriptionParams):
        try:
            audio_data, duration, size_mb = self.audio_loader.load_audio_file(file_path)
            self.app._request_stats_update(
                time_str=self._format_duration(duration),
                size_str=f"{size_mb:.2f} MB",
            )
            self._run_transcription_task(
                audio_data, self.audio_loader.target_sample_rate, params
            )
        except Exception as e:
            error_msg = f"Error processing file: {e}"
            print(f"[ERROR] {error_msg}")
            self.app.final_transcription_ready.emit(
                TranscriptionResult(error=error_msg, was_successful=False)
            )

    def _run_transcription_task(self, audio_np: np.ndarray, sample_rate: int, params: TranscriptionParams):
        self.transcriber.process_audio(audio_np, sample_rate, params)

    def _get_elapsed_time_str(self) -> str:
        now = time.time()
        paused = self.paused_total + (now - self.pause_started if self.pause_started is not None else 0.0)
        elapsed_seconds = int(now - self.start_time - paused)
        return self._format_duration(elapsed_seconds)

    def _format_duration(self, seconds: float) -> str:
        secs = int(seconds)
        mins = secs // 60
        secs %= 60
        return f"{mins:02d}:{secs:02d}"

    def reset_state(self):
        self.app.stop_elapsed_timer()
        if self.recorder.is_recording:
            self.recorder.stop()

    def _capture_transcription_params(self) -> TranscriptionParams:
        return TranscriptionParams(
            **self.app.get_transcription_parameters()
        )
