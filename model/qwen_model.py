import json

import requests

from knowledge_base.search import (
    format_indexed_sources,
    format_search_results,
    search_knowledge_base,
)
from online_search.web_search import format_web_sources, get_web_context


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


def build_prompt(
    conversation_history,
    user_message,
    indexed_sources,
    knowledge_text,
    web_context,
):
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
        "Use the local knowledge base when it is relevant.\n"
        "If the knowledge base is empty or not relevant, answer normally.\n\n"
        "Important rules for the local knowledge base:\n"
        "- Only describe files and facts that are shown below.\n"
        "- Do not invent file names, document purposes, summaries, or contents.\n"
        "- If the user asks what is in the folder, list only the indexed files below.\n"
        "- If a file is not listed below, say it is not currently indexed.\n\n"
        f"Indexed local files:\n{indexed_sources}\n\n"
        f"Relevant local knowledge excerpts:\n{knowledge_text}\n\n"
        "Web search rules:\n"
        "- Use web excerpts only when web search results are provided below.\n"
        "- When using web information, mention the source numbers like [1] or [2].\n"
        "- If web search failed, say that live web information was not available.\n\n"
        f"Web sources:\n{web_context['sources']}\n\n"
        f"Web excerpts:\n{web_context['text']}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"User: {user_message}\n"
        "AI:"
    )


def stream_ollama_response(conversation_history, user_message):
    """
    Send the user's message to Ollama and yield text pieces as they arrive.

    The main program prints each piece immediately. This keeps model logic here
    while keeping terminal input and output in main.py.
    """
    search_results = search_knowledge_base(user_message)
    indexed_sources = format_indexed_sources()
    knowledge_text = format_search_results(search_results)
    raw_web_context = get_web_context(user_message)
    web_context = {
        "sources": format_web_sources(raw_web_context["sources"]),
        "text": raw_web_context["text"],
    }
    prompt = build_prompt(
        conversation_history,
        user_message,
        indexed_sources,
        knowledge_text,
        web_context,
    )

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
        yield (
            "Error: Could not connect to Ollama.\n"
            "Please make sure Ollama is installed and running."
        )
        return
    except requests.exceptions.Timeout:
        yield (
            "Error: Ollama took too long to respond.\n"
            "The model may still be loading. Please try again."
        )
        return
    except requests.exceptions.HTTPError as error:
        yield (
            "Error: Ollama returned an HTTP error.\n"
            f"Details: {error}"
        )
        return
    except requests.exceptions.RequestException as error:
        yield (
            "Error: Something went wrong while talking to Ollama.\n"
            f"Details: {error}"
        )
        return

    for line in response.iter_lines():
        if not line:
            continue

        try:
            data = line.decode("utf-8")
            json_data = json.loads(data)
        except ValueError:
            yield "\nError: Ollama returned a response that was not valid JSON."
            return

        # If the model is not installed, Ollama usually sends an error here.
        if "error" in json_data:
            yield (
                "\nError: Ollama could not generate a response.\n"
                f"Details: {json_data['error']}\n"
                f"Tip: Try running this command first: ollama pull {MODEL_NAME}"
            )
            return

        yield json_data.get("response", "")

        if json_data.get("done", False):
            break


def is_successful_response(response_text):
    """Return True when the response should be saved in conversation history."""
    return bool(response_text.strip()) and not response_text.lstrip().startswith("Error:")
