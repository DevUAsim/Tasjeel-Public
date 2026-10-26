import os
import tempfile
import time
import wave
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import google.generativeai as genai
import numpy as np
import librosa
import tqdm.auto as tqdm_auto
from faster_whisper import WhisperModel, download_model
from tqdm import tqdm

from tasjeel.config.settings import settings_manager

AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2
AUDIO_DTYPE_SCALE_FACTOR = 32767
WAVE_FILE_SUFFIX = ".wav"
DEFAULT_CHUNK_DURATION_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
API_TIMEOUT_SECONDS = 120
RETRY_DELAY_BASE = 2
WHISPER_SAMPLE_RATE = 16000
WHISPER_CHUNK_LENGTH = 30
LANGUAGE_OVERRIDES = {"English": "en", "Urdu": "ur", "Roman Urdu": "ur", "Arabic": "ar", "Persian": "fa"}

_global_progress_callback = None

@dataclass
class TranscriptionResult:
    full_text: str = ""
    error: Optional[str] = None
    was_successful: bool = True


@dataclass
class TranscriptionParams:
    provider: str = "Gemini (Cloud)"
    user_notes: str = ""
    language: str = "English"
    speakers: str = "Multiple Speakers"
    noise: str = "Low"


class Transcriber:
    def __init__(
        self,
        gemini_model: genai.GenerativeModel,
        status_callback: Callable[[str], None],
        intermediate_callback: Callable[[str], None],
        final_callback: Callable[[TranscriptionResult], None],
        chunk_count_callback: Callable[[int], None],
        download_confirmation_callback: Optional[Callable[[str], bool]] = None,
        download_progress_callback: Optional[Callable[[int, int, str], None]] = None,
        download_completed_callback: Optional[Callable[[], None]] = None,
    ):
        self.gemini_model = gemini_model
        self.status_callback = status_callback
        self.intermediate_callback = intermediate_callback
        self.final_callback = final_callback
        self.chunk_count_callback = chunk_count_callback
        self.download_confirmation_callback = download_confirmation_callback
        self.download_progress_callback = download_progress_callback
        self.download_completed_callback = download_completed_callback
        self.whisper_model: Optional[WhisperModel] = None

    def _initialize_whisper(self):
        if self.whisper_model:
            return True
        try:
            model_size = settings_manager.get("WHISPER_MODEL")
            device = settings_manager.get("WHISPER_DEVICE")
            quantization = self._extract_quantization(model_size)
            compute_type = settings_manager.get("WHISPER_COMPUTE_TYPE") or self._map_quantization_to_compute_type(quantization, device)
            if device == "cuda" and not self._cuda_available():
                device = "cpu"
                compute_type = "int8"
                self.status_callback("No NVIDIA GPU found, using CPU (int8).")

            resolved_model = model_size
            if model_size.startswith("models--") and not os.path.exists(model_size):
                fallback_repo = self._convert_cache_path_to_repo(model_size)
                self.status_callback(f"Cached model not found locally. Falling back to '{fallback_repo}'.")
                resolved_model = fallback_repo

            needs_download = False
            try:
                if not os.path.exists(resolved_model):
                    download_model(resolved_model, local_files_only=True)
            except Exception:
                needs_download = True

            if needs_download:
                if self.download_confirmation_callback:
                    if not self.download_confirmation_callback(resolved_model):
                        self.status_callback("Model download cancelled by user.")
                        return False

                self.status_callback(f"Downloading Whisper model '{resolved_model}'...")
                
                global _global_progress_callback
                _global_progress_callback = self.download_progress_callback
                
                class CustomTqdm(tqdm):
                    def update(self, n=1):
                        super().update(n)
                        if _global_progress_callback:
                            _global_progress_callback(self.n, self.total, self.desc)
                
                original_tqdm = tqdm_auto.tqdm
                tqdm_auto.tqdm = CustomTqdm
                
                try:
                    resolved_model = download_model(resolved_model)
                finally:
                    tqdm_auto.tqdm = original_tqdm
                    _global_progress_callback = None
                
                if self.download_completed_callback:
                    self.download_completed_callback()

            self.status_callback(f"Initializing Whisper... (Source: '{resolved_model}')")
            self.whisper_model = WhisperModel(resolved_model, device=device, compute_type=compute_type)
            normalized_identifier = self._normalize_model_identifier(resolved_model)
            self.status_callback(f"Ready  ·  {normalized_identifier} loaded")
            return True
        except Exception as e:
            error_message = f"Failed to load Whisper model: {e}"
            self.status_callback(error_message)
            self.final_callback(TranscriptionResult(error=error_message, was_successful=False))
            return False

    def preload_whisper(self):
        if self.whisper_model:
            return
        def _load():
            self._initialize_whisper()
        threading.Thread(target=_load, daemon=True).start()

    def process_audio(
        self, audio_np: np.ndarray, sample_rate: int, params: TranscriptionParams
    ):
        if not isinstance(audio_np, np.ndarray) or audio_np.size == 0:
            self.status_callback("No audio data to process.")
            self.final_callback(TranscriptionResult(error="No audio data provided.", was_successful=False))
            return

        provider = params.provider.lower()
        if "whisper" in provider:
            self._process_audio_whisper(audio_np, sample_rate, params)
        else:
            self._process_audio_gemini(audio_np, sample_rate, params)

    def _process_audio_whisper(self, audio_np: np.ndarray, sample_rate: int, params: TranscriptionParams):
        if not self._initialize_whisper():
            return
        whisper_language = "en"
        prompt_parts = []
        if params.user_notes.strip():
            prompt_parts.append(params.user_notes.strip())
        initial_prompt = " ".join(prompt_parts) if prompt_parts else None

        try:
            self.status_callback("Transcribing with Whisper...")
            self.chunk_count_callback(1)

            if sample_rate != WHISPER_SAMPLE_RATE:
                self.status_callback(f"Resampling audio from {sample_rate}Hz to {WHISPER_SAMPLE_RATE}Hz...")
                audio_np = librosa.resample(audio_np, orig_sr=sample_rate, target_sr=WHISPER_SAMPLE_RATE)

            try:
                segments, _ = self.whisper_model.transcribe(
                    audio_np,
                    language=whisper_language,
                    initial_prompt=initial_prompt,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                    chunk_length=WHISPER_CHUNK_LENGTH,
                )
            except RuntimeError as e:
                if "onnxruntime" in str(e).lower():
                    self.status_callback("onnxruntime unavailable, running Whisper without VAD filter.")
                    segments, _ = self.whisper_model.transcribe(
                        audio_np,
                        language=whisper_language,
                        initial_prompt=initial_prompt,
                        vad_filter=False,
                        chunk_length=WHISPER_CHUNK_LENGTH,
                    )
                else:
                    raise
            except Exception as e:
                if "Unable to allocate" in str(e):
                    self.status_callback("Memory pressure detected. Retrying with smaller chunk length and without VAD...")
                    segments, _ = self.whisper_model.transcribe(
                        audio_np,
                        language=whisper_language,
                        initial_prompt=initial_prompt,
                        vad_filter=False,
                        chunk_length=10,
                        condition_on_previous_text=False,
                    )
                else:
                    raise

            full_transcription_parts: List[str] = []
            for segment in segments:
                full_transcription_parts.append(segment.text)
                self.intermediate_callback("".join(full_transcription_parts))

            final_text = "".join(full_transcription_parts).strip()
            self.final_callback(TranscriptionResult(full_text=final_text, was_successful=True))

        except Exception as e:
            error_msg = f"Whisper transcription failed: {e}"
            print(f"[ERROR] {error_msg}")
            self.final_callback(TranscriptionResult(error=error_msg, was_successful=False))

    def _process_audio_gemini(self, audio_np: np.ndarray, sample_rate: int, params: TranscriptionParams):
        if not self.gemini_model:
            error_msg = "Gemini model unavailable. Please check your API configuration."
            self.status_callback(error_msg)
            self.final_callback(TranscriptionResult(error=error_msg, was_successful=False))
            return
        chunk_duration = settings_manager.get_int("CHUNK_DURATION_SECONDS", DEFAULT_CHUNK_DURATION_SECONDS)
        frames_per_chunk = int(chunk_duration * sample_rate)
        num_chunks = (int(np.ceil(len(audio_np) / frames_per_chunk)) if frames_per_chunk > 0 else 1)
        self.chunk_count_callback(num_chunks)

        full_transcription_parts: List[str] = []
        errors: List[str] = []
        temp_file_paths: List[str] = []
        try:
            for i in range(num_chunks):
                start = i * frames_per_chunk
                end = min(start + frames_per_chunk, len(audio_np))
                chunk_audio_np = audio_np[start:end]
                if chunk_audio_np.size == 0:
                    continue
                chunk_text, chunk_error, temp_file_path = self._process_single_gemini_chunk(
                    chunk_audio_np, sample_rate, i, num_chunks, params
                )
                if temp_file_path:
                    temp_file_paths.append(temp_file_path)
                if chunk_error:
                    errors.append(f"Chunk {i+1}: {chunk_error}")
                if chunk_text:
                    full_transcription_parts.append(chunk_text)
                self.intermediate_callback(" ".join(full_transcription_parts))
        finally:
            self._cleanup_temp_files(temp_file_paths)
            final_text = " ".join(full_transcription_parts)
            final_error = "; ".join(errors) if errors else None
            result = TranscriptionResult(full_text=final_text, error=final_error, was_successful=(not errors))
            self.final_callback(result)

    def _process_single_gemini_chunk(
        self, chunk_np: np.ndarray, sample_rate: int, chunk_idx: int, total_chunks: int, params: TranscriptionParams
    ) -> Tuple[str, Optional[str], Optional[str]]:
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=WAVE_FILE_SUFFIX, delete=False) as tmp_file:
                temp_file_path = tmp_file.name
            audio_int16 = (chunk_np * AUDIO_DTYPE_SCALE_FACTOR).astype(np.int16)
            with wave.open(temp_file_path, "wb") as wf:
                wf.setnchannels(AUDIO_CHANNELS)
                wf.setsampwidth(AUDIO_SAMPLE_WIDTH)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
        except Exception as e:
            error_msg = f"Failed to create temp audio file: {e}"
            print(f"[ERROR] {error_msg}")
            return "", error_msg, temp_file_path

        max_retries = settings_manager.get_int("MAX_RETRIES_STANDARD", DEFAULT_MAX_RETRIES)
        for attempt in range(max_retries):
            uploaded_file = None
            try:
                self.status_callback(f"Chunk {chunk_idx + 1}/{total_chunks} (Attempt {attempt + 1}): Uploading...")
                uploaded_file = genai.upload_file(path=temp_file_path)
                self.status_callback(f"Chunk {chunk_idx + 1}/{total_chunks}: Transcribing...")
                prompt_parts = self._build_gemini_prompt(params, uploaded_file)
                response = self.gemini_model.generate_content(
                    prompt_parts, request_options={"timeout": API_TIMEOUT_SECONDS}
                )
                if uploaded_file:
                    genai.delete_file(uploaded_file.name)
                if response and response.text:
                    return response.text.strip(), None, temp_file_path
                else:
                    if attempt == max_retries - 1:
                        return "", "API returned empty response.", temp_file_path
            except Exception as e:
                print(f"[ERROR] Chunk {chunk_idx + 1} attempt {attempt + 1} failed: {e}")
                if uploaded_file:
                    try:
                        genai.delete_file(uploaded_file.name)
                    except Exception as del_e:
                        print(f"[WARN] Failed to delete uploaded file on error: {del_e}")
                if attempt == max_retries - 1:
                    return "", f"API Error: {e}", temp_file_path
                time.sleep(RETRY_DELAY_BASE**attempt)
        return "", "Max retries exceeded.", temp_file_path

    def _build_gemini_prompt(self, params: TranscriptionParams, uploaded_file) -> list:
        instruction = f"Transcribe this audio in {params.language}."
        speaker_text = {"1 Speaker": "There is a single speaker.", "2 Speakers": "There are two speakers.", "Multiple Speakers": "There are multiple speakers."}.get(params.speakers, "There are multiple speakers.")
        noise_text = f"There is a {params.noise.lower()} level of background noise."
        final_prompt = [f"{instruction} {speaker_text} {noise_text}", "Please provide only the transcribed text.", uploaded_file]
        if params.user_notes:
            final_prompt.insert(0, f"User-provided context: {params.user_notes}")
        return final_prompt

    def _cleanup_temp_files(self, file_paths: List[str]):
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                print(f"[WARN] Could not remove temp file {path}: {e}")

    def _cuda_available(self) -> bool:
        try:
            import ctranslate2
            return ctranslate2.get_cuda_device_count() > 0
        except Exception:
            return False

    def _convert_cache_path_to_repo(self, cache_path: str) -> str:
        parts = cache_path.split("--")
        if len(parts) >= 3:
            owner = parts[1]
            remainder = "--".join(parts[2:])
            return f"{owner}/{remainder}"
        return cache_path

    def _normalize_model_identifier(self, identifier: str) -> str:
        if identifier.startswith("models--"):
            return self._convert_cache_path_to_repo(identifier)
        return identifier

    def _extract_quantization(self, identifier: str) -> Optional[str]:
        normalized = self._normalize_model_identifier(identifier)
        if "-ct2-" in normalized:
            return normalized.rsplit("-ct2-", 1)[1]
        return None

    def _map_quantization_to_compute_type(self, quantization: Optional[str], device: str) -> str:
        mapping = {
            "float32": "float32",
            "float16": "float16",
            "bfloat16": "bfloat16",
            "int8": "int8",
            "int8_float16": "int8_float16",
            "int8_float32": "int8_float32",
        }
        if quantization:
            return mapping.get(quantization, mapping["float16"] if device == "cuda" else mapping["int8"])
        return mapping["float16"] if device == "cuda" else mapping["int8"]
