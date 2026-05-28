import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "knowledge_base" / "index.json"

MAX_SEARCH_RESULTS = 6

BROAD_DOCUMENT_KEYWORDS = [
    "knowledge_base",
    "knowledge base",
    "document",
    "documents",
    "folder",
    "file",
    "files",
    "read",
    "reread",
    "explain",
    "summarize",
    "summary",
    "知识库",
    "文档",
    "文件",
    "文件夹",
    "读取",
    "读",
    "解释",
    "总结",
    "内容",
]


def load_index():
    """Load the local knowledge index if it exists."""
    if not INDEX_FILE.exists():
        return []

    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def list_indexed_sources():
    """Return the exact file names currently stored in the local index."""
    documents = load_index()
    sources = []

    for document in documents:
        source = document.get("source", "")

        if source and source not in sources:
            sources.append(source)

    return sources


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


def is_broad_document_question(question):
    """
    Return True when the user asks about the knowledge base in general.

    Example: "读取知识库内的文档，并解释其内容". This kind of question may not
    share keywords with an English PDF, so we should still provide document
    excerpts instead of only passing file names to the model.
    """
    lower_question = question.lower()

    for keyword in BROAD_DOCUMENT_KEYWORDS:
        if keyword in lower_question:
            return True

    return False


def get_first_chunks_by_source(documents):
    """Return early chunks from each indexed file for broad document questions."""
    results = []
    seen_sources = set()

    for document in documents:
        source = document.get("source", "")

        if source not in seen_sources:
            results.append(document)
            seen_sources.add(source)

        if len(results) >= MAX_SEARCH_RESULTS:
            break

    if len(results) < MAX_SEARCH_RESULTS:
        for document in documents:
            if document in results:
                continue

            results.append(document)

            if len(results) >= MAX_SEARCH_RESULTS:
                break

    return results


def search_knowledge_base(question):
    """
    Search indexed local documents and return the most relevant text chunks.

    If no index exists yet, or nothing matches, this returns an empty list.
    """
    documents = load_index()
    keywords = get_keywords(question)

    if not documents:
        return []

    if is_broad_document_question(question):
        return get_first_chunks_by_source(documents)

    if not keywords:
        return []

    scored_results = []

    for document in documents:
        score = score_text(document["text"], keywords)

        if score > 0:
            scored_results.append((score, document))

    scored_results.sort(key=lambda item: item[0], reverse=True)

    return [document for score, document in scored_results[:MAX_SEARCH_RESULTS]]


def format_indexed_sources():
    """Format the exact indexed file list for the model prompt."""
    sources = list_indexed_sources()

    if not sources:
        return "No files are currently indexed."

    lines = []

    for source in sources:
        lines.append(f"- {source}")

    return "\n".join(lines)


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
