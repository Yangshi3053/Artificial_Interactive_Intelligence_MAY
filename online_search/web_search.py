import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests


SEARCH_URL = "https://duckduckgo.com/html/?q="
MAX_SEARCH_RESULTS = 3
MAX_PAGE_CHARACTERS = 2500

WEB_SEARCH_KEYWORDS = [
    "latest",
    "current",
    "today",
    "now",
    "news",
    "price",
    "weather",
    "release",
    "update",
    "search",
    "web",
    "internet",
    "online",
    "最新",
    "今天",
    "现在",
    "新闻",
    "价格",
    "天气",
    "联网",
    "上网",
    "网上",
    "搜索",
    "查一下",
    "查询",
]


class SimpleHTMLTextParser(HTMLParser):
    """
    Convert HTML into readable text.

    This intentionally stays simple: it removes script-like sections and keeps
    normal page text.
    """

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tag = None

    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style", "noscript"]:
            self.skip_tag = tag

    def handle_endtag(self, tag):
        if tag == self.skip_tag:
            self.skip_tag = None

    def handle_data(self, data):
        if self.skip_tag:
            return

        cleaned = " ".join(data.split())

        if cleaned:
            self.text_parts.append(cleaned)

    def get_text(self):
        return " ".join(self.text_parts)


def needs_web_search(question):
    """Return True when a question probably needs live web information."""
    lower_question = question.lower()

    if lower_question.startswith("web:") or lower_question.startswith("search:"):
        return True

    for keyword in WEB_SEARCH_KEYWORDS:
        if keyword in lower_question:
            return True

    return False


def clean_query(question):
    """Remove optional search prefixes from the user's question."""
    stripped = question.strip()

    for prefix in ["web:", "search:"]:
        if stripped.lower().startswith(prefix):
            return stripped[len(prefix):].strip()

    return stripped


def extract_duckduckgo_url(raw_url):
    """DuckDuckGo result links sometimes wrap the real URL in a uddg parameter."""
    parsed = urlparse(raw_url)
    query = parse_qs(parsed.query)

    if "uddg" in query:
        return unquote(query["uddg"][0])

    return raw_url


def search_web(question):
    """Search DuckDuckGo's HTML page and return result titles and URLs."""
    query = clean_query(question)
    url = SEARCH_URL + quote_plus(query)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LocalQwenAssistant/1.0)"}

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    results = []

    for match in pattern.finditer(response.text):
        raw_url = unescape(match.group(1))
        title_html = match.group(2)
        title = re.sub(r"<.*?>", "", title_html)
        title = unescape(" ".join(title.split()))
        result_url = extract_duckduckgo_url(raw_url)

        if title and result_url:
            results.append({"title": title, "url": result_url})

        if len(results) >= MAX_SEARCH_RESULTS:
            break

    return results


def fetch_page_text(url):
    """Download one web page and return readable text."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LocalQwenAssistant/1.0)"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    parser = SimpleHTMLTextParser()
    parser.feed(response.text)
    text = " ".join(parser.get_text().split())

    return text[:MAX_PAGE_CHARACTERS]


def get_web_context(question):
    """
    Search the web and fetch readable text from the top results.

    Returns a dictionary with:
    - used: whether web search was attempted
    - sources: source title and URL list
    - text: webpage excerpts or an error message
    """
    if not needs_web_search(question):
        return {"used": False, "sources": [], "text": ""}

    try:
        results = search_web(question)
    except requests.exceptions.RequestException as error:
        return {
            "used": True,
            "sources": [],
            "text": f"Web search failed: {error}",
        }

    sources = []
    text_parts = []

    for result in results:
        try:
            page_text = fetch_page_text(result["url"])
        except requests.exceptions.RequestException:
            page_text = ""

        sources.append(result)

        if page_text:
            text_parts.append(
                f"Source: {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Excerpt: {page_text}"
            )

    if not text_parts and sources:
        text_parts.append("Search found sources, but page text could not be read.")

    return {
        "used": True,
        "sources": sources,
        "text": "\n\n".join(text_parts),
    }


def format_web_sources(sources):
    """Format source links for the model prompt."""
    if not sources:
        return "No web sources were found."

    lines = []

    for index, source in enumerate(sources, start=1):
        lines.append(f"[{index}] {source['title']} - {source['url']}")

    return "\n".join(lines)


def format_web_status(web_context):
    """Format a short web-search status line for the terminal."""
    if not web_context["used"]:
        return "Web search: not used"

    if not web_context["sources"]:
        return "Web search: used, but no sources were found"

    return f"Web search: used, {len(web_context['sources'])} source(s)"
