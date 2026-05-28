import math
import re
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_FOLDER = PROJECT_ROOT / "memory"
DATABASE_FILE = MEMORY_FOLDER / "memory.sqlite"

MAX_MEMORY_RESULTS = 6

MEMORY_QUESTION_KEYWORDS = [
    "memory",
    "remember",
    "preference",
    "prefer",
    "profile",
    "about me",
    "\u8bb0\u5fc6",
    "\u8bb0\u5f97",
    "\u504f\u597d",
    "\u559c\u597d",
    "\u5173\u4e8e\u6211",
    "\u6211\u7684\u4fe1\u606f",
    "\u6211\u7684\u8981\u6c42",
]

TOPIC_KEYWORDS = {
    "coding": [
        "code",
        "coding",
        "program",
        "python",
        "debug",
        "git",
        "github",
        "\u4ee3\u7801",
        "\u7f16\u7a0b",
        "\u8c03\u8bd5",
        "\u9879\u76ee",
        "\u7a0b\u5e8f",
    ],
    "local_ai": [
        "ollama",
        "qwen",
        "model",
        "rag",
        "knowledge",
        "memory",
        "gpu",
        "ai",
        "\u6a21\u578b",
        "\u77e5\u8bc6\u5e93",
        "\u957f\u671f\u8bb0\u5fc6",
        "\u8054\u7f51",
        "\u672c\u5730",
    ],
    "preference": [
        "prefer",
        "preference",
        "like",
        "want",
        "from now on",
        "\u504f\u597d",
        "\u559c\u6b22",
        "\u5e0c\u671b",
        "\u4ee5\u540e",
        "\u4e0b\u6b21",
        "\u4e0d\u7528",
        "\u4e0d\u8981",
        "\u6700\u4f18\u89e3",
    ],
    "identity": [
        "my name",
        "i am",
        "\u6211\u53eb",
        "\u6211\u7684\u540d\u5b57",
        "\u6211\u662f",
    ],
    "school": [
        "class",
        "course",
        "assignment",
        "college",
        "school",
        "\u8bfe\u7a0b",
        "\u4f5c\u4e1a",
        "\u5b66\u6821",
    ],
}

STRONG_MEMORY_MARKERS = [
    "remember",
    "from now on",
    "always",
    "never",
    "\u8bb0\u4f4f",
    "\u4ee5\u540e",
    "\u603b\u662f",
    "\u6c38\u8fdc",
    "\u4e0d\u8981",
    "\u4e0d\u7528",
    "\u6700\u4f18\u89e3",
]

DURABLE_PATTERNS = [
    "remember",
    "i prefer",
    "i like",
    "i want",
    "from now on",
    "\u8bb0\u4f4f",
    "\u4ee5\u540e",
    "\u4e0b\u6b21",
    "\u4e0d\u7528",
    "\u4e0d\u8981",
    "\u6211\u5e0c\u671b",
    "\u6211\u60f3\u8981",
    "\u6700\u4f18\u89e3",
]

IDENTITY_PATTERNS = [
    "\u6211\u53eb[^\uff0c\u3002,.!?]+",
    "\u6211\u7684\u540d\u5b57\u662f[^\uff0c\u3002,.!?]+",
    "my name is [^,.!?]+",
    "i am [^,.!?]+",
]


def get_connection():
    """Open the local SQLite memory database."""
    MEMORY_FOLDER.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_FILE)


def now_text():
    """Return the current time as readable text."""
    return datetime.now().isoformat(timespec="seconds")


def add_column_if_missing(connection, table_name, column_name, column_definition):
    """Add a SQLite column only when an older database does not have it yet."""
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_names = [column[1] for column in columns]

    if column_name not in existing_names:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def init_database():
    """Create and migrate memory tables if they do not exist yet."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                content TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                last_used_at TEXT
            )
            """
        )

        add_column_if_missing(connection, "memories", "topic", "TEXT DEFAULT 'general'")
        add_column_if_missing(connection, "memories", "importance", "REAL DEFAULT 0.5")
        add_column_if_missing(connection, "memories", "confidence", "REAL DEFAULT 0.7")
        add_column_if_missing(connection, "memories", "use_count", "INTEGER DEFAULT 0")
        add_column_if_missing(connection, "memories", "updated_at", "TEXT")

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_topic ON memories(topic)"
        )
        backfill_memory_weights(connection)


def backfill_memory_weights(connection):
    """Upgrade older memory rows with topics and weights."""
    rows = connection.execute(
        """
        SELECT id, kind, content, topic, importance, confidence, updated_at
        FROM memories
        """
    ).fetchall()

    for memory_id, kind, content, topic, importance, confidence, updated_at in rows:
        should_update = (
            not topic
            or topic == "general"
            or importance is None
            or float(importance) <= 0.5
            or confidence is None
            or float(confidence) <= 0.7
        )

        if not should_update:
            continue

        new_topic = classify_topic(content, kind)
        new_importance = estimate_importance(kind, content)
        new_confidence = estimate_confidence(kind, content)

        connection.execute(
            """
            UPDATE memories
            SET topic = ?,
                importance = MAX(COALESCE(importance, 0), ?),
                confidence = MAX(COALESCE(confidence, 0), ?),
                updated_at = COALESCE(updated_at, ?)
            WHERE id = ?
            """,
            (new_topic, new_importance, new_confidence, now_text(), memory_id),
        )


def save_message(role, content):
    """Save one chat message to long-term storage."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content.strip(), now_text()),
        )


def clamp(value, minimum, maximum):
    """Keep a numeric value inside a fixed range."""
    return max(minimum, min(maximum, value))


def classify_topic(text, kind="general"):
    """Assign one broad topic to a memory."""
    lower_text = text.lower()
    best_topic = kind if kind in ["identity", "preference"] else "general"
    best_score = 0

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            if keyword in lower_text:
                score += 1

        if score > best_score:
            best_score = score
            best_topic = topic

    return best_topic


def estimate_importance(kind, content):
    """Estimate how strongly a memory should influence future answers."""
    lower_content = content.lower()

    if kind == "identity":
        return 0.95

    if kind == "preference":
        return 0.85

    if any(marker in lower_content for marker in STRONG_MEMORY_MARKERS):
        return 0.9

    return 0.55


def estimate_confidence(kind, content):
    """Estimate how reliable the extracted memory is."""
    if kind in ["identity", "preference"]:
        return 0.9

    if len(content) > 20:
        return 0.75

    return 0.6


def save_memory(kind, content, topic=None, importance=None, confidence=None):
    """Save or update one durable weighted memory."""
    cleaned = " ".join(content.split())

    if not cleaned:
        return

    topic = topic or classify_topic(cleaned, kind)
    importance = estimate_importance(kind, cleaned) if importance is None else importance
    confidence = estimate_confidence(kind, cleaned) if confidence is None else confidence
    importance = clamp(float(importance), 0.0, 1.0)
    confidence = clamp(float(confidence), 0.0, 1.0)
    current_time = now_text()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO memories (
                kind, content, created_at, last_used_at,
                topic, importance, confidence, use_count, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(content) DO UPDATE SET
                topic = excluded.topic,
                importance = MAX(memories.importance, excluded.importance),
                confidence = MAX(memories.confidence, excluded.confidence),
                updated_at = excluded.updated_at
            """,
            (
                kind,
                cleaned,
                current_time,
                None,
                topic,
                importance,
                confidence,
                0,
                current_time,
            ),
        )


def extract_memory_candidates(user_message, ai_response):
    """
    Extract durable memory candidates from one user message.

    This intentionally stores explicit preferences, durable instructions, and
    identity facts instead of turning every casual sentence into memory.
    """
    candidates = []
    text = user_message.strip()
    lower_text = text.lower()

    for pattern in IDENTITY_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            candidates.append(
                {
                    "kind": "identity",
                    "content": match.group(0),
                    "topic": "identity",
                    "importance": 0.95,
                    "confidence": 0.9,
                }
            )

    if any(pattern in lower_text for pattern in DURABLE_PATTERNS):
        candidates.append(
            {
                "kind": "preference",
                "content": text,
                "topic": classify_topic(text, "preference"),
                "importance": estimate_importance("preference", text),
                "confidence": 0.85,
            }
        )

    if "\u6700\u4f18\u89e3" in text or "best solution" in lower_text:
        candidates.append(
            {
                "kind": "preference",
                "content": (
                    "The user prefers optimal, scalable solutions over "
                    "beginner-only simplicity."
                ),
                "topic": "preference",
                "importance": 1.0,
                "confidence": 0.95,
            }
        )

    return candidates


def save_memories_from_turn(user_message, ai_response):
    """Extract and save durable memories from one conversation turn."""
    for candidate in extract_memory_candidates(user_message, ai_response):
        save_memory(
            candidate["kind"],
            candidate["content"],
            candidate.get("topic"),
            candidate.get("importance"),
            candidate.get("confidence"),
        )


def get_keywords(text):
    """Extract simple search keywords from English and Chinese text."""
    return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())


def score_text(text, keywords):
    """Score text by keyword overlap."""
    lower_text = text.lower()
    score = 0

    for keyword in keywords:
        if keyword in lower_text:
            score += lower_text.count(keyword)

    return score


def is_memory_question(query):
    """Return True when the user is asking about stored memory in general."""
    lower_query = query.lower()

    for keyword in MEMORY_QUESTION_KEYWORDS:
        if keyword in lower_query:
            return True

    return False


def topic_match_score(memory_topic, query):
    """Score whether a memory topic appears relevant to the query."""
    query_topic = classify_topic(query)

    if memory_topic == query_topic:
        return 2.0

    if memory_topic == "preference":
        return 0.8

    return 0.0


def age_decay(created_at):
    """Gently reduce score for old memories without deleting them."""
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return 1.0

    age_days = max(0, (datetime.now() - created).days)
    return math.exp(-age_days / 365)


def weighted_memory_score(memory, keywords, query):
    """Combine relevance, topic, importance, confidence, usage, and age."""
    content_score = score_text(memory["content"], keywords)
    topic_bonus = topic_match_score(memory["topic"], query)
    importance_bonus = memory["importance"] * 4
    confidence_bonus = memory["confidence"] * 2
    usage_bonus = min(memory["use_count"], 10) * 0.15
    decay = age_decay(memory["created_at"])

    return (
        content_score
        + topic_bonus
        + importance_bonus
        + confidence_bonus
        + usage_bonus
    ) * decay


def get_recent_durable_memories():
    """Return high-priority recent memories for broad memory questions."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, kind, content, created_at, topic, importance, confidence, use_count
            FROM memories
            ORDER BY importance DESC, confidence DESC, id DESC
            LIMIT ?
            """,
            (MAX_MEMORY_RESULTS,),
        ).fetchall()

    return [
        {
            "score": importance * 10,
            "type": "memory",
            "id": memory_id,
            "kind": kind,
            "content": content,
            "created_at": created_at,
            "topic": topic,
            "importance": importance,
            "confidence": confidence,
            "use_count": use_count,
        }
        for memory_id, kind, content, created_at, topic, importance, confidence, use_count in rows
    ]


def search_long_term_memory(query):
    """
    Search memories and previous messages related to the new question.

    Durable memories use weighted ranking. Raw messages are still searchable,
    but they score lower than curated memories.
    """
    keywords = get_keywords(query)

    if is_memory_question(query):
        return get_recent_durable_memories()

    if not keywords:
        return []

    results = []

    with get_connection() as connection:
        memory_rows = connection.execute(
            """
            SELECT id, kind, content, created_at, topic, importance, confidence, use_count
            FROM memories
            """
        ).fetchall()
        message_rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT 80
            """
        ).fetchall()

        for row in memory_rows:
            memory = {
                "type": "memory",
                "id": row[0],
                "kind": row[1],
                "content": row[2],
                "created_at": row[3],
                "topic": row[4] or "general",
                "importance": float(row[5] or 0.5),
                "confidence": float(row[6] or 0.7),
                "use_count": int(row[7] or 0),
            }
            score = weighted_memory_score(memory, keywords, query)

            if score > 0:
                memory["score"] = score
                results.append(memory)

        for message_id, role, content, created_at in message_rows:
            score = score_text(content, keywords)

            if score > 0:
                results.append(
                    {
                        "score": score * 0.6,
                        "type": "message",
                        "id": message_id,
                        "kind": role,
                        "content": content,
                        "created_at": created_at,
                        "topic": "chat_history",
                        "importance": 0.3,
                        "confidence": 0.6,
                        "use_count": 0,
                    }
                )

    results.sort(key=lambda item: item["score"], reverse=True)
    selected = results[:MAX_MEMORY_RESULTS]

    if selected:
        with get_connection() as connection:
            for result in selected:
                if result["type"] == "memory":
                    connection.execute(
                        """
                        UPDATE memories
                        SET last_used_at = ?, use_count = use_count + 1
                        WHERE id = ?
                        """,
                        (now_text(), result["id"]),
                    )

    return selected


def format_memory_context(results):
    """Format memory search results for the model prompt."""
    if not results:
        return "No relevant long-term memories found."

    lines = []

    for index, result in enumerate(results, start=1):
        lines.append(
            f"[M{index}] {result['type']} / topic={result['topic']} / "
            f"kind={result['kind']} / importance={result['importance']:.2f} / "
            f"confidence={result['confidence']:.2f} / used={result['use_count']} / "
            f"{result['created_at']}: {result['content']}"
        )

    return "\n".join(lines)


def get_topic_summary():
    """Return memory counts and average weights by topic."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT topic, COUNT(*), AVG(importance), AVG(confidence), SUM(use_count)
            FROM memories
            GROUP BY topic
            ORDER BY AVG(importance) DESC, COUNT(*) DESC
            """
        ).fetchall()

    return [
        {
            "topic": topic,
            "count": count,
            "avg_importance": avg_importance or 0,
            "avg_confidence": avg_confidence or 0,
            "use_count": use_count or 0,
        }
        for topic, count, avg_importance, avg_confidence, use_count in rows
    ]


def get_memory_stats():
    """Return basic memory database counts and topic summary."""
    with get_connection() as connection:
        message_count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        memory_count = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    return {
        "messages": message_count,
        "memories": memory_count,
        "topics": get_topic_summary(),
        "database": str(DATABASE_FILE),
    }
