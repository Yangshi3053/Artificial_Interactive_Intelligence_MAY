import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "knowledge_base" / "index.json"

MAX_SEARCH_RESULTS = 3


def load_index():
    """Load the local knowledge index if it exists."""
    if not INDEX_FILE.exists():
        return []

    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def get_keywords(question):
    """
    Extract simple search keywords from the user's question.

    This simple method works for English words and also keeps Chinese text
    pieces. It is not as powerful as vector search, but it is easy to debug.
    """
    return re.findall(r"[\w\u4e00-\u9fff]+", question.lower())


def score_text(text, keywords):
    """Give a text chunk a simple score based on keyword matches."""
    lower_text = text.lower()
    score = 0

    for keyword in keywords:
        if keyword in lower_text:
            score += lower_text.count(keyword)

    return score


def search_knowledge_base(question):
    """
    Search indexed local documents and return the most relevant text chunks.

    If no index exists yet, or nothing matches, this returns an empty list.
    """
    documents = load_index()
    keywords = get_keywords(question)

    if not documents or not keywords:
        return []

    scored_results = []

    for document in documents:
        score = score_text(document["text"], keywords)

        if score > 0:
            scored_results.append((score, document))

    scored_results.sort(key=lambda item: item[0], reverse=True)

    return [document for score, document in scored_results[:MAX_SEARCH_RESULTS]]


def format_search_results(results):
    """Format search results so they can be included in the model prompt."""
    if not results:
        return ""

    formatted_parts = []

    for result in results:
        formatted_parts.append(
            f"Source: {result['source']} (chunk {result['chunk']})\n"
            f"{result['text']}"
        )

    return "\n\n".join(formatted_parts)
