import os


# Model and Ollama settings
MODEL_NAME = "qwen3:14b"
OLLAMA_URL = "http://localhost:11434/api/generate"
MAX_RESPONSE_TOKENS = 4096
MAX_HISTORY_CHARACTERS = 12000
OLLAMA_CONTEXT_TOKENS = 32768

# Terminal commands
EXIT_COMMANDS = ["exit", "quit", "q"]
REINDEX_COMMANDS = ["reindex", "/reindex"]
MEMORY_COMMANDS = ["memory", "/memory"]
SYSTEM_COMMANDS = ["system", "/system"]
VOICE_STATUS_COMMANDS = ["voice", "/voice", "voice status", "/voice status"]
VOICE_ON_COMMANDS = ["voice on", "/voice on"]
VOICE_OFF_COMMANDS = ["voice off", "/voice off"]
SPEAK_PREFIXES = ["speak ", "/speak "]

# Debugging
# Set LOCAL_AI_DEBUG=1 before running python main.py to print debug messages.
DEBUG_ENABLED = os.environ.get("LOCAL_AI_DEBUG", "").lower() in ["1", "true", "yes"]

# CosyVoice text-to-speech settings
# Start the official CosyVoice FastAPI server separately, then set
# LOCAL_AI_TTS=1 or type "voice on" in the chat program.
COSYVOICE_AUTO_SPEAK = os.environ.get("LOCAL_AI_TTS", "").lower() in ["1", "true", "yes"]
COSYVOICE_URL = os.environ.get(
    "COSYVOICE_URL",
    "http://localhost:50000/inference_sft",
)
COSYVOICE_SPK_ID = os.environ.get("COSYVOICE_SPK_ID", "\u4e2d\u6587\u5973")
COSYVOICE_SAMPLE_RATE = int(os.environ.get("COSYVOICE_SAMPLE_RATE", "22050"))
COSYVOICE_MAX_TEXT_CHARACTERS = int(
    os.environ.get("COSYVOICE_MAX_TEXT_CHARACTERS", "800")
)
