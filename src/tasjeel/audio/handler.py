import os
import queue
import tempfile
import threading
import wave
from pathlib import Path
from typing import Callable, Optional, Tuple, List, Dict

import numpy as np
import sounddevice as sd
from pydub import AudioSegment

VU_SMOOTHING_FACTOR = 0.7
VU_NEW_SIGNAL_WEIGHT = 0.3
STREAM_SLEEP_INTERVAL_MS = 100
THREAD_JOIN_TIMEOUT_SECONDS = 1.0
DEFAULT_SAMPLE_RATE = 44100
BYTES_PER_MB = 1024 * 1024
AUDIO_CHANNELS = 1
AUDIO_DTYPE = "float32"
AUDIO_INT16_MAX = 32767


def get_audio_input_devices() -> List[Dict[str, any]]:
    devices = []
    try:
        device_info = sd.query_devices()
        for i, device in enumerate(device_info):
            if device['max_input_channels'] > 0:
                devices.append({
                    'id': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
    except Exception as e:
        print(f"Error querying audio devices: {e}")
    return devices


def get_default_input_device() -> Optional[int]:
    try:
        return sd.default.device[0]
    except Exception:
        return None

class AudioRecorder:
    def __init__(self, sample_rate, vu_update_callback: Callable[[float], None], device_id: Optional[int] = None):
        try:
            self.sample_rate = int(sample_rate)
        except (ValueError, TypeError):
            print(
                f"[FATAL] Invalid sample_rate provided: '{sample_rate}'. Must be a number. Falling back to {DEFAULT_SAMPLE_RATE}.",
                flush=True,
            )
            self.sample_rate = DEFAULT_SAMPLE_RATE

        self.vu_update_callback = vu_update_callback
        self.device_id = device_id
        self.is_recording = False
        self.is_paused = False
        self._buffer = None
        self._vu_level = 0.0
        self._record_thread = None
        self._last_audio = None
        self._writer_thread = None
        self._temp_dir: Optional[Path] = None
        self._temp_wav_path: Optional[Path] = None

    def _recording_thread_target(self):
        def stream_callback(indata: np.ndarray, frames: int, time, status):
            if status:
                print(f"Audio stream status change: {status}", flush=True)

            if self.is_paused:
                self._vu_level = 0.0
                return

            if self._buffer is not None:
                self._buffer.put(indata.copy())

            if self.is_recording:
                rms = np.sqrt(np.mean(indata**2))
                self._vu_level = (VU_SMOOTHING_FACTOR * self._vu_level) + (VU_NEW_SIGNAL_WEIGHT * rms)
                self.vu_update_callback(self._vu_level)

        try:
            with sd.InputStream(
                callback=stream_callback,
                channels=AUDIO_CHANNELS,
                samplerate=self.sample_rate,
                dtype=AUDIO_DTYPE,
                device=self.device_id,
            ):
                while self.is_recording:
                    sd.sleep(STREAM_SLEEP_INTERVAL_MS)
        except Exception as e:
            print(f"FATAL: Error during audio recording stream: {e}", flush=True)
        finally:
            self.vu_update_callback(0)

    def start(self):
        if self.is_recording:
            print("[WARN] Start called while already recording.", flush=True)
            return

        self.is_recording = True
        self.is_paused = False
        self._buffer = queue.Queue()
        self._last_audio = None
        self._prepare_temp_storage()
        self._writer_thread = threading.Thread(target=self._buffer_consumer_target, daemon=True)
        self._writer_thread.start()
        self._record_thread = threading.Thread(
            target=self._recording_thread_target, daemon=True
        )
        self._record_thread.start()
        print("Audio recording started.", flush=True)

    def pause(self):
        if self.is_recording:
            self.is_paused = True
            self.vu_update_callback(0)

    def resume(self):
        if self.is_recording:
            self.is_paused = False

    def stop(self) -> Optional[np.ndarray]:
        if not self.is_recording:
            return None

        self.is_recording = False
        self.is_paused = False
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
        self._record_thread = None

        print("Audio recording stopped.", flush=True)

        if self._buffer is not None:
            self._buffer.put(None)

        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)

        audio_data = self._load_temp_recording()
        self._cleanup_temp_storage()
        self._buffer = None
        self._writer_thread = None
        return audio_data

    def _prepare_temp_storage(self):
        if self._temp_dir:
            self._cleanup_temp_storage()
        self._temp_dir = Path(tempfile.mkdtemp(prefix="tasjeel_audio_"))
        self._temp_wav_path = self._temp_dir / "recording.wav"

    def _buffer_consumer_target(self):
        if not self._temp_wav_path:
            return
        try:
            with wave.open(str(self._temp_wav_path), "wb") as wf:
                wf.setnchannels(AUDIO_CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                while True:
                    if self._buffer is None:
                        break
                    try:
                        chunk = self._buffer.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if chunk is None:
                        break
                    scaled = np.clip(chunk, -1.0, 1.0)
                    int16_chunk = (scaled * AUDIO_INT16_MAX).astype(np.int16)
                    wf.writeframes(int16_chunk.tobytes())
        except Exception as e:
            print(f"FATAL: Error while writing audio buffer: {e}", flush=True)

    def _load_temp_recording(self) -> Optional[np.ndarray]:
        if not self._temp_wav_path or not self._temp_wav_path.exists():
            self._last_audio = None
            return None
        try:
            with wave.open(str(self._temp_wav_path), "rb") as wf:
                frames = wf.getnframes()
                if frames == 0:
                    self._last_audio = None
                    return None
                audio_bytes = wf.readframes(frames)
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            if audio_int16.size == 0:
                self._last_audio = None
                return None
            self._last_audio = (audio_int16.astype(np.float32) / AUDIO_INT16_MAX).copy()
            return self._last_audio
        except Exception as e:
            print(f"FATAL: Failed to load temporary recording: {e}", flush=True)
            self._last_audio = None
            return None

    def _cleanup_temp_storage(self):
        if self._temp_wav_path and self._temp_wav_path.exists():
            try:
                os.remove(self._temp_wav_path)
            except OSError:
                pass
        if self._temp_dir and self._temp_dir.exists():
            try:
                self._temp_dir.rmdir()
            except OSError:
                pass
        self._temp_dir = None
        self._temp_wav_path = None

class AudioFileLoader:
    def __init__(self, target_sample_rate):
        try:
            self.target_sample_rate = int(target_sample_rate)
        except (ValueError, TypeError):
            print(
                f"[FATAL] Invalid target_sample_rate provided: '{target_sample_rate}'. Must be a number. Falling back to {DEFAULT_SAMPLE_RATE}.",
                flush=True,
            )
            self.target_sample_rate = DEFAULT_SAMPLE_RATE

    def load_audio_file(self, file_path: str) -> Tuple[np.ndarray, float, float]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found at path: {file_path}")

        try:
            file_size_mb = os.path.getsize(file_path) / BYTES_PER_MB
            audio = AudioSegment.from_file(file_path)

            audio = audio.set_channels(AUDIO_CHANNELS)
            audio = audio.set_frame_rate(self.target_sample_rate)

            raw_samples = np.array(audio.get_array_of_samples())

            normalization_factor = 2 ** (audio.sample_width * 8 - 1)
            audio_data = raw_samples.astype(np.float32) / normalization_factor

            duration_seconds = len(audio_data) / self.target_sample_rate

            print(
                f"Successfully loaded '{os.path.basename(file_path)}'. Duration: {duration_seconds:.2f}s",
                flush=True,
            )
            return audio_data, duration_seconds, file_size_mb
        except Exception as e:
            raise IOError(f"Failed to load or process audio file '{file_path}': {e}")
