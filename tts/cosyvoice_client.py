import wave
from datetime import datetime
from pathlib import Path

import requests

from app_config import (
    COSYVOICE_MAX_TEXT_CHARACTERS,
    COSYVOICE_MODE,
    COSYVOICE_PROMPT_TEXT,
    COSYVOICE_PROMPT_TEXT_FILE,
    COSYVOICE_PROMPT_WAV,
    COSYVOICE_SAMPLE_RATE,
    COSYVOICE_SPK_ID,
    COSYVOICE_SFT_URL,
    COSYVOICE_ZERO_SHOT_URL,
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


def resolve_project_path(path_text):
    """Resolve relative paths from the project root."""
    path = Path(path_text)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def load_prompt_text():
    """Read zero-shot prompt text from env var or local transcript file."""
    if COSYVOICE_PROMPT_TEXT.strip():
        return COSYVOICE_PROMPT_TEXT.strip()

    prompt_text_file = resolve_project_path(COSYVOICE_PROMPT_TEXT_FILE)

    if not prompt_text_file.exists():
        raise RuntimeError(f"CosyVoice prompt text file was not found: {prompt_text_file}")

    return prompt_text_file.read_text(encoding="utf-8-sig").strip()


def build_sft_request(cleaned_text):
    """Build request data for CosyVoice built-in speaker mode."""
    return COSYVOICE_SFT_URL, {"tts_text": cleaned_text, "spk_id": COSYVOICE_SPK_ID}, None


def build_zero_shot_request(cleaned_text):
    """Build request data for CosyVoice zero-shot voice cloning mode."""
    prompt_wav = resolve_project_path(COSYVOICE_PROMPT_WAV)

    if not prompt_wav.exists():
        raise RuntimeError(f"CosyVoice prompt wav was not found: {prompt_wav}")

    prompt_text = load_prompt_text()

    if not prompt_text:
        raise RuntimeError("CosyVoice prompt text is empty.")

    data = {
        "tts_text": cleaned_text,
        "prompt_text": prompt_text,
    }
    files = {
        "prompt_wav": (prompt_wav.name, prompt_wav.open("rb"), "audio/wav"),
    }

    return COSYVOICE_ZERO_SHOT_URL, data, files


def build_cosyvoice_request(cleaned_text):
    """Build the correct CosyVoice request for the selected voice mode."""
    if COSYVOICE_MODE == "sft":
        return build_sft_request(cleaned_text)

    if COSYVOICE_MODE == "zero_shot":
        return build_zero_shot_request(cleaned_text)

    raise RuntimeError("COSYVOICE_MODE must be either 'sft' or 'zero_shot'.")


def synthesize_to_wav(text, output_path=None):
    """
    Send text to the CosyVoice FastAPI server and save the returned WAV file.

    The official CosyVoice FastAPI server streams raw int16 PCM audio. This
    client stores it as a normal .wav file so Windows can play it directly.
    """
    cleaned_text = " ".join(text.split())

    if not cleaned_text:
        raise ValueError("No text was provided for speech synthesis.")

    if len(cleaned_text) > COSYVOICE_MAX_TEXT_CHARACTERS:
        cleaned_text = cleaned_text[:COSYVOICE_MAX_TEXT_CHARACTERS].rstrip() + "..."

    output_path = Path(output_path) if output_path else build_output_path()
    files = None

    try:
        url, payload, files = build_cosyvoice_request(cleaned_text)
        response = requests.post(url, data=payload, files=files, timeout=(10, 300))
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Could not connect to CosyVoice. Start the CosyVoice FastAPI server first."
        ) from error
    except requests.exceptions.Timeout as error:
        raise RuntimeError("CosyVoice took too long to generate speech.") from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"CosyVoice request failed: {error}") from error
    finally:
        if files:
            for file_info in files.values():
                file_info[1].close()

    if not response.content:
        raise RuntimeError("CosyVoice returned empty audio.")

    write_pcm_to_wav(response.content, output_path)
    return output_path
