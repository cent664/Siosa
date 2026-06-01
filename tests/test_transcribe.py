# Tests for speech-to-text transcription.

from unittest.mock import patch

from fastapi.testclient import TestClient

from poe_agent.harness.api.app import app
from poe_agent.harness.speech.transcribe import TranscriptionError, transcribe_wav


def test_transcribe_wav_rejects_empty():
    try:
        transcribe_wav(b"")
    except TranscriptionError as exc:
        assert "No audio" in str(exc)
    else:
        raise AssertionError("expected TranscriptionError")


def test_transcribe_endpoint_returns_text():
    with patch(
        "poe_agent.harness.api.app.transcribe_wav",
        return_value="How does poison scale?",
    ):
        client = TestClient(app)
        response = client.post(
            "/transcribe",
            files={"audio": ("question.wav", b"RIFFfake", "audio/wav")},
        )
    assert response.status_code == 200
    assert response.json()["text"] == "How does poison scale?"


def test_transcribe_endpoint_maps_errors():
    with patch(
        "poe_agent.harness.api.app.transcribe_wav",
        side_effect=TranscriptionError("missing dependency"),
    ):
        client = TestClient(app)
        response = client.post(
            "/transcribe",
            files={"audio": ("question.wav", b"RIFFfake", "audio/wav")},
        )
    assert response.status_code == 400
    assert "missing dependency" in response.json()["detail"]
