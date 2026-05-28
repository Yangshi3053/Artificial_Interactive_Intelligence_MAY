import wave
from datetime import datetime
from pathlib import Path

import requests

from app_config import (
    COSYVOICE_MAX_TEXT_CHARACTERS,
    COSYVOICE_SAMPLE_RATE,
    COSYVOICE_SPK_ID,
    COSYVOICE_URL,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VOICE_OUTPUT_FOLDER = PROJECT_ROOT / "voice_output"


def build_output_path():
    """Create a unique local WAV path for one generated voice response."""
    VOICE_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return VOICE_OUTPUT_FOLDER / f"cosyvoice_{timestamp}.wav"


def write_pcm_to_wav(pcm_audio, output_path):
    """Wrap CosyVoice raw int16 PCM bytes in a standard WAV container."""
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(COSYVOICE_SAMPLE_RATE)
        wav_file.writeframes(pcm_audio)


def synthesize_to_wav(text, output_path=None):
    """
    Send text to the CosyVoice FastAPI server and save the returned WAV file.

    The official CosyVoice FastAPI server streams raw int16 PCM audio for
    /inference_sft. This client stores it as a normal .wav file so Windows can
    play it directly.
    """
    cleaned_text = " ".join(text.split())

    if not cleaned_text:
        raise ValueError("No text was provided for speech synthesis.")

    if len(cleaned_text) > COSYVOICE_MAX_TEXT_CHARACTERS:
        cleaned_text = cleaned_text[:COSYVOICE_MAX_TEXT_CHARACTERS].rstrip() + "..."

    output_path = Path(output_path) if output_path else build_output_path()
    payload = {
        "tts_text": cleaned_text,
        "spk_id": COSYVOICE_SPK_ID,
    }

    try:
        response = requests.post(COSYVOICE_URL, data=payload, timeout=(10, 300))
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Could not connect to CosyVoice. Start the CosyVoice FastAPI server first."
        ) from error
    except requests.exceptions.Timeout as error:
        raise RuntimeError("CosyVoice took too long to generate speech.") from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"CosyVoice request failed: {error}") from error

    if not response.content:
        raise RuntimeError("CosyVoice returned empty audio.")

    write_pcm_to_wav(response.content, output_path)
    return output_path
