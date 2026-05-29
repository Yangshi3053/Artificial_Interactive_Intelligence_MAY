import json

import requests

from app_config import (
    MAX_HISTORY_CHARACTERS,
    MAX_RESPONSE_TOKENS,
    MODEL_NAME,
    OLLAMA_CONTEXT_TOKENS,
    OLLAMA_URL,
)
from knowledge_base.search import (
    format_indexed_sources,
    format_search_results,
    search_knowledge_base,
)
from online_search.web_search import (
    format_query_variants,
    format_web_sources,
    get_web_context,
)
from system_context.local_info import (
    format_local_system_context,
    get_local_system_context,
)


def get_assistant_status_text():
    """Return the real local assistant configuration for the model prompt."""
    return (
        "Assistant runtime status:\n"
        "- Runtime: local Python terminal assistant\n"
        "- Model host: local Ollama HTTP API\n"
        f"- Model name: {MODEL_NAME}\n"
        f"- Approximate Ollama context window: {OLLAMA_CONTEXT_TOKENS} tokens\n"
        f"- Max generated tokens per answer: {MAX_RESPONSE_TOKENS}\n"
        f"- Short-term history limit: {MAX_HISTORY_CHARACTERS} characters\n"
        "- Local knowledge base: enabled\n"
        "- Long-term memory: enabled through local SQLite retrieval\n"
        "- Optional web search: enabled through the Python online_search module\n"
        "- Important: this is not Alibaba Cloud Qwen API.\n"
    )


def build_prompt(
    conversation_history,
    user_message,
    local_system_context,
    memory_context,
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
        "You are running inside this user's local Python project, not as a cloud-hosted Qwen API.\n"
        "When asked about your capabilities, answer from the runtime status below.\n"
        "Do not claim Alibaba Cloud Qwen API limits unless the user explicitly asks about Alibaba Cloud.\n\n"
        f"{get_assistant_status_text()}\n"
        "Use local computer context for date, time, timezone, region, and approximate location questions.\n"
        "If location is approximate IP location, clearly say it is not exact GPS.\n\n"
        f"{local_system_context}\n\n"
        "Use the conversation history to understand follow-up questions.\n\n"
        "Use long-term memory when it is relevant.\n"
        "Long-term memory may contain user preferences, project context, and older chat turns.\n"
        "Do not reveal private memory unless it helps answer the user's current question.\n\n"
        f"Relevant long-term memory:\n{memory_context}\n\n"
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
        "- Prefer lower source tiers. Tier 1 is strongest, tier 5 is weakest.\n"
        "- Tier 1: official sources, official docs, company sites, official GitHub, official announcements.\n"
        "- Tier 2: authoritative institutions or professional databases such as EIA, IEA, Trading Economics, Bank of Canada, NVIDIA, Raspberry Pi docs.\n"
        "- Tier 3: mainstream or professional media such as Reuters, AP, BBC, CBC, CNBC, Bloomberg, The Verge, Tom's Hardware.\n"
        "- Tier 4: blogs, forums, personal sites, tutorials. Use as supporting context only.\n"
        "- Tier 5: unclear reposts or low-quality sources. Avoid unless no better source exists.\n"
        "- Use web excerpts only when web search results are provided below.\n"
        "- If web sources or excerpts are provided, do not say you cannot access live web data.\n"
        "- Do not recommend unrelated websites when relevant sources are already provided.\n"
        "- Do not invent numbers. If a number is not present in the excerpts, say the searched excerpts do not provide it.\n"
        "- When using web information, mention source numbers like [1] or [2].\n"
        "- If web search failed, say that live web information was not available.\n\n"
        "Weather answer rules:\n"
        "- For weather questions, answer from the provided weather sources and excerpts.\n"
        "- If a structured local forecast is provided, use its temperature and precipitation values.\n"
        "- If location is approximate IP location, say it is approximate, not exact GPS.\n"
        "- Do not switch to another city, country, or weather service unless the user asks for it.\n\n"
        f"Web query plan:\n{web_context['queries']}\n\n"
        f"Web sources:\n{web_context['sources']}\n\n"
        f"Web excerpts:\n{web_context['text']}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"User: {user_message}\n"
        "AI:"
    )


def stream_ollama_response(
    conversation_history,
    user_message,
    memory_context,
    raw_web_context=None,
    local_system_context=None,
):
    """
    Send the user's message to Ollama and yield text pieces as they arrive.

    The main program prints each piece immediately. This keeps model logic here
    while keeping terminal input and output in main.py.
    """
    search_results = search_knowledge_base(user_message)
    indexed_sources = format_indexed_sources()
    knowledge_text = format_search_results(search_results)
    if raw_web_context is None:
        raw_web_context = get_web_context(user_message)
    if local_system_context is None:
        local_system_context = format_local_system_context(get_local_system_context())
    web_context = {
        "queries": format_query_variants(raw_web_context["query_variants"]),
        "sources": format_web_sources(raw_web_context["sources"]),
        "text": raw_web_context["text"],
    }
    prompt = build_prompt(
        conversation_history,
        user_message,
        local_system_context,
        memory_context,
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
