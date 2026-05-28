import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests


SEARCH_URL = "https://duckduckgo.com/html/?q="
MAX_SEARCH_RESULTS = 3
MAX_RESULTS_PER_QUERY = 6
MAX_QUERY_VARIANTS = 4
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

OFFICIAL_DOMAINS = [
    ".gc.ca",
    ".gov",
    ".gov.ca",
    ".gov.uk",
    ".edu",
    "canada.ca",
    "bankofcanada.ca",
    "nvidia.com",
    "raspberrypi.com",
    "github.com",
    "docs.github.com",
    "ollama.com",
    "openai.com",
    "eia.gov",
    "iea.org",
]

AUTHORITY_DOMAINS = [
    "tradingeconomics.com",
    "globalpetrolprices.com",
    "statcan.gc.ca",
    "150.statcan.gc.ca",
    "worldbank.org",
    "imf.org",
    "oecd.org",
    "st.com",
]

MAINSTREAM_MEDIA_DOMAINS = [
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "cbc.ca",
    "cnbc.com",
    "bloomberg.com",
    "theverge.com",
    "tomshardware.com",
]

LOW_QUALITY_HINTS = [
    "mirror",
    "repost",
    "scrape",
    "download",
    "freepdf",
]


class SimpleHTMLTextParser(HTMLParser):
    """Convert HTML into readable text."""

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


def detect_search_language_plan(question):
    """
    Pick useful search languages for the topic.

    For country-specific questions, search in the country's main source
    languages instead of only using the user's input language.
    """
    lower_question = question.lower()

    if "canada" in lower_question or "加拿大" in lower_question:
        return [
            ("en", "English sources for Canada"),
            ("fr", "French sources for Canada"),
            ("original", "Original user wording"),
        ]

    if "china" in lower_question or "中国" in lower_question or "中國" in lower_question:
        return [
            ("zh", "Chinese sources for China"),
            ("en", "English international sources"),
            ("original", "Original user wording"),
        ]

    return [("original", "Original user wording"), ("en", "English sources")]


def build_localized_query(question, language):
    """Build one search query for a target language."""
    base_query = clean_query(question)
    lower_query = base_query.lower()
    is_oil_price = any(
        word in lower_query
        for word in ["oil", "gas", "gasoline", "fuel", "petrol", "油价", "汽油", "燃油"]
    )
    is_canada = "canada" in lower_query or "加拿大" in lower_query

    if is_canada and is_oil_price and language == "en":
        return "Canada gasoline prices today official government data"

    if is_canada and is_oil_price and language == "fr":
        return "prix essence Canada aujourd'hui donnees officielles gouvernement"

    if language == "en" and base_query != lower_query:
        return f"{base_query} official source"

    return base_query


def build_query_variants(question):
    """Build a short list of multilingual query variants."""
    variants = []
    seen_queries = set()

    for language, reason in detect_search_language_plan(question):
        query = build_localized_query(question, language)

        if query in seen_queries:
            continue

        variants.append({"query": query, "language": language, "reason": reason})
        seen_queries.add(query)

        if len(variants) >= MAX_QUERY_VARIANTS:
            break

    return variants


def extract_duckduckgo_url(raw_url):
    """DuckDuckGo result links sometimes wrap the real URL in a uddg parameter."""
    parsed = urlparse(raw_url)
    query = parse_qs(parsed.query)

    if "uddg" in query:
        return unquote(query["uddg"][0])

    return raw_url


def get_domain(url):
    """Return a normalized hostname for source ranking."""
    hostname = urlparse(url).hostname or ""

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname.lower()


def source_tier_for_url(url):
    """
    Classify a source using the user's five-level source-quality policy.

    Tier 1: official sources.
    Tier 2: professional databases and authoritative institutions.
    Tier 3: mainstream or professional media.
    Tier 4: blogs, forums, tutorials, personal websites.
    Tier 5: unclear repost or low-quality sources.
    """
    domain = get_domain(url)

    if any(hint in domain for hint in LOW_QUALITY_HINTS):
        return 5, "unclear or repost-like source"

    if any(domain.endswith(item) or item in domain for item in OFFICIAL_DOMAINS):
        return 1, "official source"

    if any(item in domain for item in AUTHORITY_DOMAINS):
        return 2, "authoritative database or institution"

    if any(item in domain for item in MAINSTREAM_MEDIA_DOMAINS):
        return 3, "mainstream or professional media"

    return 4, "blog, forum, tutorial, or general website"


def search_one_query(query_info):
    """Search DuckDuckGo's HTML page for one query variant."""
    url = SEARCH_URL + quote_plus(query_info["query"])
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LocalQwenAssistant/1.0)"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    results = []

    for position, match in enumerate(pattern.finditer(response.text), start=1):
        raw_url = unescape(match.group(1))
        title_html = match.group(2)
        title = re.sub(r"<.*?>", "", title_html)
        title = unescape(" ".join(title.split()))
        result_url = extract_duckduckgo_url(raw_url)

        if title and result_url:
            tier, tier_reason = source_tier_for_url(result_url)
            results.append(
                {
                    "title": title,
                    "url": result_url,
                    "domain": get_domain(result_url),
                    "tier": tier,
                    "tier_reason": tier_reason,
                    "query": query_info["query"],
                    "language": query_info["language"],
                    "query_reason": query_info["reason"],
                    "search_position": position,
                }
            )

        if len(results) >= MAX_RESULTS_PER_QUERY:
            break

    return results


def result_rank_key(result):
    """Sort by source tier first, then original search position."""
    return (result["tier"], result["search_position"])


def search_web(question):
    """Search with multilingual query variants and return ranked sources."""
    all_results = []
    seen_urls = set()

    for query_info in build_query_variants(question):
        for result in search_one_query(query_info):
            if result["url"] in seen_urls:
                continue

            all_results.append(result)
            seen_urls.add(result["url"])

    all_results.sort(key=result_rank_key)

    return all_results[:MAX_SEARCH_RESULTS]


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
    Search the web and fetch readable text from the top ranked results.

    Returns:
    - used: whether web search was attempted
    - query_variants: multilingual search queries used
    - sources: ranked source title and URL list
    - text: webpage excerpts or an error message
    """
    if not needs_web_search(question):
        return {"used": False, "query_variants": [], "sources": [], "text": ""}

    query_variants = build_query_variants(question)

    try:
        results = search_web(question)
    except requests.exceptions.RequestException as error:
        return {
            "used": True,
            "query_variants": query_variants,
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
                f"Source tier: {result['tier']} ({result['tier_reason']})\n"
                f"Search language: {result['language']}\n"
                f"Search query: {result['query']}\n"
                f"Excerpt: {page_text}"
            )

    if not text_parts and sources:
        text_parts.append("Search found sources, but page text could not be read.")

    return {
        "used": True,
        "query_variants": query_variants,
        "sources": sources,
        "text": "\n\n".join(text_parts),
    }


def format_web_sources(sources):
    """Format source links for the model prompt."""
    if not sources:
        return "No web sources were found."

    lines = []

    for index, source in enumerate(sources, start=1):
        lines.append(
            f"[{index}] Tier {source['tier']} ({source['tier_reason']}), "
            f"{source['title']} - {source['url']}"
        )

    return "\n".join(lines)


def format_query_variants(query_variants):
    """Format the multilingual query plan for logs and prompt context."""
    if not query_variants:
        return "No web queries were used."

    lines = []

    for item in query_variants:
        lines.append(
            f"- {item['language']}: {item['query']} ({item['reason']})"
        )

    return "\n".join(lines)


def format_web_status(web_context):
    """Format a short web-search status line for the terminal."""
    if not web_context["used"]:
        return "Web search: not used"

    if not web_context["sources"]:
        return "Web search: used, but no sources were found"

    tier_counts = {}

    for source in web_context["sources"]:
        tier = source["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    tier_text = ", ".join(
        f"tier {tier}: {count}" for tier, count in sorted(tier_counts.items())
    )

    return f"Web search: used, {len(web_context['sources'])} source(s), {tier_text}"
