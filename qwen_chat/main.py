import os
import subprocess
import sys

import requests


# You can change this model name later if you want to use a different model.
MODEL_NAME = "qwen3:14b"

# Ollama's local API endpoint for generating text.
OLLAMA_URL = "http://localhost:11434/api/generate"


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


def ask_ollama(user_message):
    """
    Send the user's message to Ollama and return the AI's response.

    This function uses stream=False so Ollama sends one complete response
    instead of sending small pieces one by one.
    """
    request_data = {
        "model": MODEL_NAME,
        "prompt": user_message,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=request_data, timeout=120)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return (
            "Error: Could not connect to Ollama.\n"
            "Please make sure Ollama is installed and running."
        )
    except requests.exceptions.Timeout:
        return (
            "Error: Ollama took too long to respond.\n"
            "The model may still be loading. Please try again."
        )
    except requests.exceptions.HTTPError as error:
        return (
            "Error: Ollama returned an HTTP error.\n"
            f"Details: {error}"
        )
    except requests.exceptions.RequestException as error:
        return (
            "Error: Something went wrong while talking to Ollama.\n"
            f"Details: {error}"
        )

    try:
        data = response.json()
    except ValueError:
        return "Error: Ollama returned a response that was not valid JSON."

    # If the model is not installed, Ollama usually sends an error message here.
    if "error" in data:
        return (
            "Error: Ollama could not generate a response.\n"
            f"Details: {data['error']}\n"
            f"Tip: Try running this command first: ollama pull {MODEL_NAME}"
        )

    return data.get("response", "Error: No response text was returned by Ollama.")


def main():
    """
    Run a simple terminal chat loop.

    The loop continues until the user types exit, quit, or q.
    """
    print("Welcome to the local Qwen chat assistant!")
    print(f"Using Ollama model: {MODEL_NAME}")
    print("Type exit, quit, or q to stop.\n")
    start_monitor_window()

    while True:
        user_message = input("You: ").strip()

        if user_message.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        if not user_message:
            print("Please type a message before pressing Enter.\n")
            continue

        print("AI is thinking...\n")
        ai_response = ask_ollama(user_message)
        print(f"AI: {ai_response}\n")


if __name__ == "__main__":
    main()
