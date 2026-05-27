import json
import os
import subprocess
import sys

import requests


# You can change this model name later if you want to use a different model.
MODEL_NAME = "qwen3:14b"

# Ollama's local API endpoint for generating text.
OLLAMA_URL = "http://localhost:11434/api/generate"

# Higher numbers allow longer answers. Lower numbers make answers stop sooner.
MAX_RESPONSE_TOKENS = 4096

# Keep recent conversation text so the model can remember earlier messages.
# A very large history can slow the model down, so this project keeps it simple
# and trims old text when the conversation gets too long.
MAX_HISTORY_CHARACTERS = 12000


def start_monitor_window():
    """
    Open the GPU and memory monitor popup.

    The monitor runs in a separate Python process, so the chat loop can keep
    working normally in this terminal.
    """
    monitor_path = os.path.join(os.path.dirname(__file__), "monitor.py")

    try:
        subprocess.Popen([sys.executable, monitor_path])
    except OSError as error:
        print("Warning: Could not open the monitor window.")
        print(f"Details: {error}\n")


def build_prompt(conversation_history, user_message):
    """
    Build one prompt that includes the recent chat history.

    Ollama's /api/generate endpoint does not automatically remember earlier
    messages for us. We include the recent history in the prompt so the model
    can answer questions like "summarize what you wrote before".
    """
    history_text = "\n".join(conversation_history)

    if len(history_text) > MAX_HISTORY_CHARACTERS:
        history_text = history_text[-MAX_HISTORY_CHARACTERS:]

    return (
        "You are a helpful local AI assistant.\n"
        "Use the conversation history to understand follow-up questions.\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"User: {user_message}\n"
        "AI:"
    )


def print_ollama_response(conversation_history, user_message):
    """
    Send the user's message to Ollama and print the response as it arrives.

    stream=True means the user can see the answer while the model is writing.
    This feels much faster than waiting for the whole answer to finish first.
    """
    prompt = build_prompt(conversation_history, user_message)

    request_data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": MAX_RESPONSE_TOKENS,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=request_data,
            stream=True,
            timeout=(10, 300),
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(
            "Error: Could not connect to Ollama.\n"
            "Please make sure Ollama is installed and running."
        )
        return
    except requests.exceptions.Timeout:
        print(
            "Error: Ollama took too long to respond.\n"
            "The model may still be loading. Please try again."
        )
        return
    except requests.exceptions.HTTPError as error:
        print(
            "Error: Ollama returned an HTTP error.\n"
            f"Details: {error}"
        )
        return
    except requests.exceptions.RequestException as error:
        print(
            "Error: Something went wrong while talking to Ollama.\n"
            f"Details: {error}"
        )
        return

    full_response = ""

    for line in response.iter_lines():
        if not line:
            continue

        try:
            data = line.decode("utf-8")
            json_data = json.loads(data)
        except ValueError:
            print("\nError: Ollama returned a response that was not valid JSON.")
            return

        # If the model is not installed, Ollama usually sends an error here.
        if "error" in json_data:
            print("\nError: Ollama could not generate a response.")
            print(f"Details: {json_data['error']}")
            print(f"Tip: Try running this command first: ollama pull {MODEL_NAME}")
            return

        text_piece = json_data.get("response", "")
        full_response += text_piece
        print(text_piece, end="", flush=True)

        if json_data.get("done", False):
            break

    return full_response.strip()


def main():
    """
    Run a simple terminal chat loop.

    The loop continues until the user types exit, quit, or q.
    """
    print("Welcome to the local Qwen chat assistant!")
    print(f"Using Ollama model: {MODEL_NAME}")
    print("Type exit, quit, or q to stop.\n")
    start_monitor_window()

    conversation_history = []

    while True:
        user_message = input("You: ").strip()

        if user_message.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        if not user_message:
            print("Please type a message before pressing Enter.\n")
            continue

        print("AI: ", end="", flush=True)
        ai_response = print_ollama_response(conversation_history, user_message)
        print("\n")

        if ai_response:
            conversation_history.append(f"User: {user_message}")
            conversation_history.append(f"AI: {ai_response}")


if __name__ == "__main__":
    main()
