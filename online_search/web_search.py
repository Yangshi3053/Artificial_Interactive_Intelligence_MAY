import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests


SEARCH_URL = "https://duckduckgo.com/html/?kl=us-en&q="
MAX_SEARCH_RESULTS = 3
MAX_RESULTS_PER_QUERY = 6
MAX_QUERY_VARIANTS = 5
MAX_PAGE_CHARACTERS = 2500

# Chinese words are written with Unicode escapes so this file stays ASCII-safe.
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
    "oil price",
    "gas price",
    "\u6700\u65b0",  # latest
    "\u4eca\u5929",  # today
    "\u73b0\u5728",  # now
    "\u65b0\u95fb",  # news
    "\u4ef7\u683c",  # price
    "\u5929\u6c14",  # weather
    "\u8054\u7f51",  # web access
    "\u4e0a\u7f51",  # go online
    "\u7f51\u4e0a",  # online
    "\u641c\u7d22",  # search
    "\u67e5\u4e00\u4e0b",  # look up
    "\u67e5\u8be2",  # query
    "\u6cb9\u4ef7",  # oil price
    "\u539f\u6cb9",  # crude oil
    "\u6c7d\u6cb9",  # gasoline
    "\u71c3\u6cb9",  # fuel
]

OFFICIAL_DOMAINS = [
    ".gc.ca",
    ".gov",
    ".gov.ca",
    ".gov.uk",
    ".edu",
    "canada.ca",
    "bankofcanada.ca",
    "nrcan.gc.ca",
    "natural-resources.canada.ca",
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
    "oilprice.cc",
    "statcan.gc.ca",
    "150.statcan.gc.ca",
    "www150.statcan.gc.ca",
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

COUNTRY_ALIASES = {
    "canada": ["canada", "\u52a0\u62ff\u5927"],
    "iran": ["iran", "\u4f0a\u6717"],
    "russia": ["russia", "\u4fc4\u7f57\u65af", "\u4fc4\u7f85\u65af"],
    "united_states": [
        "united states",
        "usa",
        "u.s.",
        "us ",
        "\u7f8e\u56fd",
        "\u7f8e\u570b",
    ],
}

ENGLISH_QUERY_REPLACEMENTS = [
    ("\u4eca\u5929", "today"),
    ("\u73b0\u5728", "current"),
    ("\u6700\u65b0", "latest"),
    ("\u5168\u7403", "global"),
    ("\u4e16\u754c", "world"),
    ("\u52a0\u62ff\u5927", "Canada"),
    ("\u4f0a\u6717", "Iran"),
    ("\u4fc4\u7f57\u65af", "Russia"),
    ("\u4fc4\u7f85\u65af", "Russia"),
    ("\u7f8e\u56fd", "United States"),
    ("\u7f8e\u570b", "United States"),
    ("\u4e2d\u56fd", "China"),
    ("\u4e2d\u570b", "China"),
    ("\u6cb9\u4ef7", "oil prices"),
    ("\u539f\u6cb9", "crude oil"),
    ("\u6c7d\u6cb9", "gasoline"),
    ("\u71c3\u6cb9", "fuel"),
    ("\u5929\u6c14", "weather"),
    ("\u65b0\u95fb", "news"),
    ("\u4ef7\u683c", "price"),
    ("\u5b98\u65b9\u6587\u6863", "official documentation"),
    ("\u5b98\u65b9", "official"),
    ("\u5b98\u7f51", "official website"),
    ("\u6587\u6863", "documentation"),
    ("\u624b\u518c", "manual"),
    ("\u62a5\u544a", "report"),
    ("\u8d44\u6599", "documentation"),
    ("\u5f00\u53d1\u8005", "developer"),
    ("\u5f15\u811a", "pinout"),
    ("\u63a5\u53e3", "interface"),
    ("\u6559\u7a0b", "tutorial"),
    ("\u4e0b\u8f7d", "download"),
    ("\u600e\u4e48\u6837", ""),
    ("\u600e\u6837", ""),
    ("\u591a\u5c11", ""),
    ("\u67e5\u4e00\u4e0b", ""),
    ("\u641c\u7d22", ""),
    ("\u5462", ""),
    ("\u5417", ""),
    ("\uff1f", ""),
    ("?", ""),
]

OIL_PRICE_FALLBACK_SOURCES = {
    "iran": [
        {
            "title": "Iran gasoline prices - GlobalPetrolPrices.com",
            "url": "https://www.globalpetrolprices.com/Iran/gasoline_prices/",
            "tier": 2,
            "tier_reason": "authoritative database or institution",
            "language": "en",
            "query": "Iran gasoline prices GlobalPetrolPrices",
            "query_reason": "Fallback authoritative energy price source",
            "search_position": 50,
        },
        {
            "title": "Iran energy profile - U.S. Energy Information Administration",
            "url": "https://www.eia.gov/international/analysis/country/IRN",
            "tier": 1,
            "tier_reason": "official source",
            "language": "en",
            "query": "Iran energy profile EIA",
            "query_reason": "Fallback official energy source",
            "search_position": 51,
        },
    ],
    "russia": [
        {
            "title": "Russia gasoline prices - GlobalPetrolPrices.com",
            "url": "https://www.globalpetrolprices.com/Russia/gasoline_prices/",
            "tier": 2,
            "tier_reason": "authoritative database or institution",
            "language": "en",
            "query": "Russia gasoline prices GlobalPetrolPrices",
            "query_reason": "Fallback authoritative energy price source",
            "search_position": 50,
        },
        {
            "title": "Russia energy profile - U.S. Energy Information Administration",
            "url": "https://www.eia.gov/international/analysis/country/RUS",
            "tier": 1,
            "tier_reason": "official source",
            "language": "en",
            "query": "Russia energy profile EIA",
            "query_reason": "Fallback official energy source",
            "search_position": 51,
        },
    ],
    "united_states": [
        {
            "title": "Gasoline and Diesel Fuel Update - U.S. Energy Information Administration",
            "url": "https://www.eia.gov/petroleum/gasdiesel/",
            "tier": 1,
            "tier_reason": "official source",
            "language": "en",
            "query": "United States gasoline price EIA",
            "query_reason": "Fallback official energy price source",
            "search_position": 50,
        },
    ],
    "canada": [
        {
            "title": "Fuel consumption levies in Canada - Natural Resources Canada",
            "url": "https://natural-resources.canada.ca/energy-efficiency/transportation-alternative-fuels/fuel-consumption-levies-canada",
            "tier": 1,
            "tier_reason": "official source",
            "language": "en",
            "query": "Canada fuel prices Natural Resources Canada",
            "query_reason": "Fallback official Canadian energy source",
            "search_position": 50,
        },
    ],
}


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


def contains_chinese(text):
    """Return True when text contains Chinese characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def build_english_query_text(question):
    """Convert common Chinese search wording into an English-first query."""
    query = clean_query(question)

    for source_text, replacement in ENGLISH_QUERY_REPLACEMENTS:
        query = query.replace(source_text, f" {replacement} ")

    query = " ".join(query.split())

    if contains_chinese(query):
        query = f"{query} English official source"
    else:
        query = f"{query} official source"

    return query.strip()


def detect_country(question):
    """Detect common country names in English or Chinese."""
    lower_question = f" {question.lower()} "

    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if alias in lower_question:
                return country

    return None


def is_oil_price_question(question):
    """Return True for oil, gasoline, fuel, and crude-oil price questions."""
    lower_question = question.lower()
    oil_terms = [
        "oil",
        "gas",
        "gasoline",
        "fuel",
        "petrol",
        "crude",
        "\u6cb9\u4ef7",
        "\u539f\u6cb9",
        "\u6c7d\u6cb9",
        "\u71c3\u6cb9",
    ]

    return any(term in lower_question for term in oil_terms)


def detect_search_language_plan(question):
    """
    Pick useful search languages for the topic.

    Country-specific questions search in the languages most likely to find
    official or authoritative local sources.
    """
    country = detect_country(question)

    if country == "canada":
        return [
            ("en", "English sources for Canada"),
            ("fr", "French sources for Canada"),
            ("original", "Original user wording"),
        ]

    if country == "iran":
        return [
            ("en", "English international energy sources for Iran"),
            ("fa", "Persian local-source wording for Iran"),
            ("original", "Original user wording"),
        ]

    if country == "russia":
        return [
            ("en", "English international energy sources for Russia"),
            ("ru", "Russian local-source wording for Russia"),
            ("original", "Original user wording"),
        ]

    if country == "united_states":
        return [
            ("en", "English official US sources"),
            ("original", "Original user wording"),
        ]

    if country == "china":
        return [
            ("en", "English international sources"),
            ("zh", "Chinese sources for China"),
            ("original", "Original user wording"),
        ]

    return [
        ("en", "English-first web search"),
        ("original", "Original user wording as fallback"),
    ]


def build_oil_price_query(country, language, base_query):
    """Build specialized oil-price queries with stronger source intent."""
    if country == "canada" and language == "en":
        return "Canada gasoline prices today official government data"
    if country == "canada" and language == "fr":
        return "prix essence Canada aujourd'hui donnees officielles gouvernement"

    if country == "iran" and language == "en":
        return "Iran crude oil gasoline prices today EIA IEA Trading Economics"
    if country == "iran" and language == "fa":
        return "Iran gasoline price crude oil official today"

    if country == "russia" and language == "en":
        return "Russia crude oil gasoline prices today EIA IEA Trading Economics"
    if country == "russia" and language == "ru":
        return "Russia gasoline price crude oil official today"

    if country == "united_states" and language == "en":
        return "United States gasoline price today EIA official data"

    if language == "en":
        english_query = build_english_query_text(base_query)
        return f"{english_query} EIA IEA Trading Economics oil price today"

    return base_query


def build_localized_query(question, language):
    """Build one search query for a target language."""
    base_query = clean_query(question)
    country = detect_country(base_query)

    if is_oil_price_question(base_query):
        return build_oil_price_query(country, language, base_query)

    if language == "en":
        return build_english_query_text(base_query)

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
    """Classify a source using the five-level source-quality policy."""
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
    """Sort by source tier, English-first language choice, then position."""
    language_priority = {
        "en": 0,
        "fr": 1,
        "zh": 2,
        "fa": 2,
        "ru": 2,
        "original": 3,
    }

    return (
        result["tier"],
        language_priority.get(result["language"], 2),
        result["search_position"],
    )


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

    country = detect_country(question)

    if is_oil_price_question(question) and country in OIL_PRICE_FALLBACK_SOURCES:
        for result in OIL_PRICE_FALLBACK_SOURCES[country]:
            if result["url"] in seen_urls:
                continue

            result = dict(result)
            result["domain"] = get_domain(result["url"])
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
    """Search the web and fetch readable text from the top ranked results."""
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
