from model.qwen_model import MODEL_NAME, is_successful_response, stream_ollama_response
from monitor.resource_monitor import start_monitor_window, stop_monitor_window
from knowledge_base.index_documents import build_index


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

            if not user_message:
                print("Please type a message before pressing Enter.\n")
                continue

            print("AI: ", end="", flush=True)

            full_response = ""
            for text_piece in stream_ollama_response(conversation_history, user_message):
                full_response += text_piece
                print(text_piece, end="", flush=True)

            print("\n")

            if is_successful_response(full_response):
                conversation_history.append(f"User: {user_message}")
                conversation_history.append(f"AI: {full_response.strip()}")
    finally:
        stop_monitor_window(monitor_process)


if __name__ == "__main__":
    main()
