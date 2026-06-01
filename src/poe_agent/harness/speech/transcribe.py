# ROLE: harness — WAV transcription (local faster-whisper or OpenAI Whisper API).

from __future__ import annotations

import io
import tempfile
from functools import lru_cache
from pathlib import Path

from poe_agent.harness.config import Settings, get_settings


class TranscriptionError(Exception):
    """User-facing transcription failure (missing deps, empty audio, etc.)."""


def _effective_model(settings: Settings) -> str:
    if settings.transcribe_model.strip():
        return settings.transcribe_model.strip()
    if settings.transcribe_provider.lower() == "openai":
        return "whisper-1"
    return "base"


def transcribe_wav(audio_bytes: bytes, *, sample_rate: int | None = None) -> str:
    """Transcribe WAV bytes to text using TRANSCRIBE_PROVIDER from settings."""
    if not audio_bytes:
        raise TranscriptionError("No audio data to transcribe.")

    settings = get_settings()
    provider = settings.transcribe_provider.lower().strip()
    model = _effective_model(settings)

    if provider == "local":
        return _transcribe_local(audio_bytes, model, sample_rate)
    if provider == "openai":
        return _transcribe_openai(audio_bytes, settings, model)
    raise TranscriptionError(
        f"Unknown TRANSCRIBE_PROVIDER: {provider!r}. Use 'local' or 'openai'."
    )


@lru_cache(maxsize=4)
def _get_whisper_model(model_name: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionError(
            'Local transcription requires faster-whisper. '
            'Install with: pip install -e ".[speech]"'
        ) from exc
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def _transcribe_local(audio_bytes: bytes, model_name: str, sample_rate: int | None) -> str:
    _ = sample_rate
    whisper = _get_whisper_model(model_name)
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        segments, _info = whisper.transcribe(tmp_path)
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

    text = " ".join(parts).strip()
    if not text:
        raise TranscriptionError("Transcription produced no text. Try speaking louder or longer.")
    return text


def _transcribe_openai(audio_bytes: bytes, settings: Settings, model_name: str) -> str:
    if not settings.openai_api_key:
        raise TranscriptionError(
            "OPENAI_API_KEY is required when TRANSCRIBE_PROVIDER=openai."
        )
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    buf = io.BytesIO(audio_bytes)
    buf.name = "audio.wav"
    result = client.audio.transcriptions.create(model=model_name, file=buf)
    text = (result.text or "").strip()
    if not text:
        raise TranscriptionError("Transcription produced no text. Try speaking louder or longer.")
    return text
