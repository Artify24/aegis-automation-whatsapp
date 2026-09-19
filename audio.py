"""Voice Note and Audio Transcription Engine powered by Groq Whisper.

Transcribes incoming customer WhatsApp voice notes in real-time (~200ms),
supporting English, Hindi, Hinglish, Spanish, Arabic, and 90+ languages.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

from groq import Groq
import config

logger = logging.getLogger("aegisbot.audio")

_groq_client: Optional[Groq] = None


def _get_groq() -> Optional[Groq]:
    global _groq_client
    if _groq_client is None and config.GROQ_API_KEY:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "voice_note.ogg") -> Optional[str]:
    """Transcribe raw audio bytes using Groq whisper-large-v3-turbo."""
    client = _get_groq()
    if not client or not audio_bytes:
        return None

    try:
        audio_stream = io.BytesIO(audio_bytes)
        audio_stream.name = filename

        transcription = client.audio.transcriptions.create(
            file=audio_stream,
            model="whisper-large-v3-turbo",
            response_format="text",
            temperature=0.0,
        )
        result = str(transcription).strip()
        logger.info("Voice note transcribed (%d bytes) -> '%s'", len(audio_bytes), result[:80])
        return result
    except Exception as e:
        logger.error("Whisper voice transcription failed: %s", e)
        return None
