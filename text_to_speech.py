"""
text_to_speech.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.
─────────────────
Converts text into an MP3 audio file using Google Text-to-Speech (gTTS).
No pydub or ffmpeg needed — modern browsers play MP3 natively.

Flow:
  text  →  gTTS generates .mp3  →  base64 encoded  →  browser plays it
"""

import os
import logging
import hashlib
from gtts import gTTS

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Directory for temporary audio output files.
# ──────────────────────────────────────────────────────────────
_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio_output")
os.makedirs(_AUDIO_DIR, exist_ok=True)


def _unique_path(text: str) -> str:
    """Generates a unique MP3 file path based on a hash of the text."""
    text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
    return os.path.join(_AUDIO_DIR, f"response_{text_hash}.mp3")


def synthesize(text: str, lang: str = "en") -> str | None:
    """
    Converts text to an MP3 file using gTTS.
    Browsers natively support MP3 — no conversion needed.

    Args:
        text: The text to synthesize.
        lang: Language code (default 'en' for English).

    Returns:
        Absolute path to the .mp3 file, or None on failure.
    """
    try:
        mp3_path = _unique_path(text)
        logger.info(f"Synthesizing TTS for text: '{text[:60]}...'")
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(mp3_path)
        logger.debug(f"MP3 saved: {mp3_path}")
        return mp3_path

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}", exc_info=True)
        return None


def cleanup(file_path: str) -> None:
    """Deletes a temporary audio file after it has been sent."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up: {file_path}")
    except OSError as e:
        logger.warning(f"Could not delete {file_path}: {e}")
