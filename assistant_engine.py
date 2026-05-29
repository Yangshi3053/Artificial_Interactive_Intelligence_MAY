from app_config import (
    COSYVOICE_AUTO_SPEAK,
    COSYVOICE_MODE,
    COSYVOICE_PROMPT_TEXT_FILE,
    COSYVOICE_PROMPT_WAV,
    COSYVOICE_SAMPLE_RATE,
    COSYVOICE_SPK_ID,
    COSYVOICE_SFT_URL,
    COSYVOICE_ZERO_SHOT_URL,
    EXIT_COMMANDS,
    MEMORY_COMMANDS,
    MODEL_NAME,
    REINDEX_COMMANDS,
    SPEAK_PREFIXES,
    SYSTEM_COMMANDS,
    VOICE_OFF_COMMANDS,
    VOICE_ON_COMMANDS,
    VOICE_STATUS_COMMANDS,
)
from knowledge_base.index_documents import build_index
from memory.long_term_memory import (
    format_memory_context,
    get_memory_stats,
    init_database,
    save_memories_from_turn,
    save_message,
    search_long_term_memory,
)
from model.qwen_model import is_successful_response, stream_ollama_response
from monitor.resource_monitor import start_monitor_window, stop_monitor_window
from online_search.web_search import (
    format_query_variants,
    format_web_status,
    get_web_context,
)
from system_context.local_info import (
    format_local_system_context,
    get_local_system_context,
)
from tts.audio_player import play_wav
from tts.cosyvoice_client import synthesize_to_wav
from utils.debug import debug_log


class AssistantEngine:
    """Coordinate terminal input, tools, model calls, and persistence."""

    def __init__(self):
        self.conversation_history = []
        self.monitor_process = None
        self.voice_enabled = COSYVOICE_AUTO_SPEAK

    def run(self):
        """Start the assistant and keep the terminal chat loop running."""
        self.print_welcome()
        init_database()
        self.monitor_process = start_monitor_window()

        try:
            while True:
                user_message = input("You: ").strip()

                if self.handle_command(user_message):
                    if user_message.lower() in EXIT_COMMANDS:
                        break

                    continue

                if not user_message:
                    print("Please type a message before pressing Enter.\n")
                    continue

                self.run_chat_turn(user_message)
        finally:
            stop_monitor_window(self.monitor_process)

    def print_welcome(self):
        """Print startup instructions."""
        print("Welcome to the local Qwen chat assistant!")
        print(f"Using Ollama model: {MODEL_NAME}")
        print("Type exit, quit, or q to stop.\n")
        print("Type reindex to reread files in knowledge_base/documents.\n")
        print("Type memory to see long-term memory status.\n")
        print("Type system to see local date, time, region, and location status.\n")
        print("Type voice on, voice off, or voice to control CosyVoice speech.\n")

    def handle_command(self, user_message):
        """Handle built-in terminal commands. Return True when handled."""
        command = user_message.lower()

        if command in EXIT_COMMANDS:
            print("Goodbye!")
            return True

        if command in REINDEX_COMMANDS:
            chunk_count = build_index()
            print(f"Knowledge base reindexed: {chunk_count} text chunks.\n")
            return True

        if command in MEMORY_COMMANDS:
            self.print_memory_status()
            return True

        if command in SYSTEM_COMMANDS:
            self.print_system_status()
            return True

        if command in VOICE_STATUS_COMMANDS:
            self.print_voice_status()
            return True

        if command in VOICE_ON_COMMANDS:
            self.voice_enabled = True
            print("CosyVoice speech is on.\n")
            self.print_voice_status()
            return True

        if command in VOICE_OFF_COMMANDS:
            self.voice_enabled = False
            print("CosyVoice speech is off.\n")
            return True

        speak_text = self.extract_speak_command(user_message)

        if speak_text is not None:
            self.speak_text(speak_text)
            return True

        return False

    def print_memory_status(self):
        """Print long-term memory counts and topic statistics."""
        stats = get_memory_stats()
        print(
            f"Long-term memory: {stats['messages']} saved messages, "
            f"{stats['memories']} durable memories.\n"
            f"Database: {stats['database']}\n"
        )

        if stats["topics"]:
            print("Memory topics:")

            for topic in stats["topics"]:
                print(
                    f"- {topic['topic']}: {topic['count']} memories, "
                    f"importance {topic['avg_importance']:.2f}, "
                    f"confidence {topic['avg_confidence']:.2f}, "
                    f"used {topic['use_count']} times"
                )

            print()

    def print_system_status(self):
        """Print local system context."""
        system_context = get_local_system_context()
        print(format_local_system_context(system_context))
        print()

    def print_voice_status(self):
        """Print current CosyVoice text-to-speech settings."""
        state = "on" if self.voice_enabled else "off"
        print(f"CosyVoice speech: {state}")
        print(f"CosyVoice mode: {COSYVOICE_MODE}")
        print(f"SFT URL: {COSYVOICE_SFT_URL}")
        print(f"Zero-shot URL: {COSYVOICE_ZERO_SHOT_URL}")
        print(f"Speaker ID: {COSYVOICE_SPK_ID}")
        print(f"Prompt wav: {COSYVOICE_PROMPT_WAV}")
        print(f"Prompt text file: {COSYVOICE_PROMPT_TEXT_FILE}")
        print(f"Sample rate: {COSYVOICE_SAMPLE_RATE} Hz\n")

    def extract_speak_command(self, user_message):
        """Return text after a speak command, or None when it is not a command."""
        lower_message = user_message.lower()

        for prefix in SPEAK_PREFIXES:
            if lower_message.startswith(prefix):
                return user_message[len(prefix):].strip()

        return None

    def speak_text(self, text):
        """Generate speech with CosyVoice and play it when possible."""
        if not text:
            print("Please type text after speak.\n")
            return

        try:
            wav_path = synthesize_to_wav(text)
        except RuntimeError as error:
            print(f"Voice error: {error}\n")
            return
        except ValueError as error:
            print(f"Voice error: {error}\n")
            return

        played = play_wav(wav_path)

        if played:
            print(f"Voice saved and played: {wav_path}\n")
        else:
            print(f"Voice saved: {wav_path}\n")

    def run_chat_turn(self, user_message):
        """Collect context, call the model, stream the answer, and save memory."""
        debug_log("Collecting long-term memory context")
        memory_results = search_long_term_memory(user_message)
        memory_context = format_memory_context(memory_results)

        debug_log("Collecting local system context")
        local_system_data = get_local_system_context()
        local_system_context = format_local_system_context(local_system_data)

        debug_log("Collecting web context")
        raw_web_context = get_web_context(user_message, local_system_data)

        self.print_web_status(raw_web_context)

        print("AI: ", end="", flush=True)
        full_response = ""

        for text_piece in stream_ollama_response(
            self.conversation_history,
            user_message,
            memory_context,
            raw_web_context,
            local_system_context,
        ):
            full_response += text_piece
            print(text_piece, end="", flush=True)

        print("\n")
        self.save_successful_turn(user_message, full_response)

    def print_web_status(self, raw_web_context):
        """Print search status and source details before the model answer."""
        print(format_web_status(raw_web_context))

        if raw_web_context["query_variants"]:
            print("Search queries:")
            print(format_query_variants(raw_web_context["query_variants"]))

        if raw_web_context["sources"]:
            for index, source in enumerate(raw_web_context["sources"], start=1):
                print(
                    f"[{index}] Tier {source['tier']} "
                    f"({source['tier_reason']}), {source['title']} - {source['url']}"
                )

    def save_successful_turn(self, user_message, full_response):
        """Save short-term history and long-term memory for successful answers."""
        if not is_successful_response(full_response):
            debug_log("Skipping memory save because response was not successful")
            return

        answer = full_response.strip()
        self.conversation_history.append(f"User: {user_message}")
        self.conversation_history.append(f"AI: {answer}")
        save_message("user", user_message)
        save_message("assistant", answer)
        save_memories_from_turn(user_message, answer)
        debug_log("Saved successful turn to memory")

        if self.voice_enabled:
            self.speak_text(answer)
