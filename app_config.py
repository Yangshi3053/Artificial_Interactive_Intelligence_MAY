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

# Debugging
# Set LOCAL_AI_DEBUG=1 before running python main.py to print debug messages.
DEBUG_ENABLED = os.environ.get("LOCAL_AI_DEBUG", "").lower() in ["1", "true", "yes"]
