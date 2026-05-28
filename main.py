from model.qwen_model import MODEL_NAME, is_successful_response, stream_ollama_response
from monitor.resource_monitor import start_monitor_window, stop_monitor_window
from knowledge_base.index_documents import build_index
from memory.long_term_memory import (
    format_memory_context,
    get_memory_stats,
    init_database,
    save_memories_from_turn,
    save_message,
    search_long_term_memory,
)
from online_search.web_search import format_web_status, get_web_context


def main():
    """
    Run the terminal chat program.

    This file is intentionally small so it is easy to debug:
    - It handles user input.
    - It starts and stops the monitor window.
    - It prints the model response.
    """
    print("Welcome to the local Qwen chat assistant!")
    print(f"Using Ollama model: {MODEL_NAME}")
    print("Type exit, quit, or q to stop.\n")
    print("Type reindex to reread files in knowledge_base/documents.\n")
    print("Type memory to see long-term memory status.\n")

    init_database()
    monitor_process = start_monitor_window()
    conversation_history = []

    try:
        while True:
            user_message = input("You: ").strip()

            if user_message.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            if user_message.lower() in ["reindex", "/reindex"]:
                chunk_count = build_index()
                print(f"Knowledge base reindexed: {chunk_count} text chunks.\n")
                continue

            if user_message.lower() in ["memory", "/memory"]:
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

                continue

            if not user_message:
                print("Please type a message before pressing Enter.\n")
                continue

            full_response = ""
            memory_results = search_long_term_memory(user_message)
            memory_context = format_memory_context(memory_results)
            raw_web_context = get_web_context(user_message)

            print(format_web_status(raw_web_context))

            if raw_web_context["sources"]:
                for index, source in enumerate(raw_web_context["sources"], start=1):
                    print(f"[{index}] {source['title']} - {source['url']}")

            print("AI: ", end="", flush=True)

            for text_piece in stream_ollama_response(
                conversation_history,
                user_message,
                memory_context,
                raw_web_context,
            ):
                full_response += text_piece
                print(text_piece, end="", flush=True)

            print("\n")

            if is_successful_response(full_response):
                conversation_history.append(f"User: {user_message}")
                conversation_history.append(f"AI: {full_response.strip()}")
                save_message("user", user_message)
                save_message("assistant", full_response.strip())
                save_memories_from_turn(user_message, full_response)
    finally:
        stop_monitor_window(monitor_process)


if __name__ == "__main__":
    main()
