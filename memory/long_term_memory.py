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
    "记忆",
    "记得",
    "偏好",
    "喜好",
    "关于我",
    "我的信息",
    "我的要求",
]


def get_connection():
    """Open the local SQLite memory database."""
    MEMORY_FOLDER.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_FILE)


def init_database():
    """Create memory tables if they do not exist yet."""
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
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)"
        )


def now_text():
    """Return the current time as readable text."""
    return datetime.now().isoformat(timespec="seconds")


def save_message(role, content):
    """Save one chat message to long-term storage."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content.strip(), now_text()),
        )


def save_memory(kind, content):
    """Save one durable memory if it does not already exist."""
    cleaned = " ".join(content.split())

    if not cleaned:
        return

    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO memories (kind, content, created_at, last_used_at)
            VALUES (?, ?, ?, ?)
            """,
            (kind, cleaned, now_text(), None),
        )


def extract_memory_candidates(user_message, ai_response):
    """
    Extract simple long-term memories from the user's message.

    This is intentionally conservative. It remembers explicit preferences,
    identity statements, and durable instructions. It does not try to store
    every casual sentence as a permanent fact.
    """
    candidates = []
    text = user_message.strip()
    lower_text = text.lower()

    durable_patterns = [
        "remember",
        "记住",
        "以后",
        "下次",
        "不用",
        "不要",
        "我希望",
        "我想要",
        "i prefer",
        "i like",
        "i want",
        "from now on",
    ]

    identity_patterns = [
        r"我叫[^，。,.!?]+",
        r"我的名字是[^，。,.!?]+",
        r"my name is [^,.!?]+",
        r"i am [^,.!?]+",
    ]

    for pattern in identity_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            candidates.append(("identity", match.group(0)))

    if any(pattern in lower_text for pattern in durable_patterns):
        candidates.append(("preference", text))

    if "最优解" in text or "best solution" in lower_text:
        candidates.append(
            (
                "preference",
                "The user prefers optimal, scalable solutions over beginner-only simplicity.",
            )
        )

    return candidates


def save_memories_from_turn(user_message, ai_response):
    """Extract and save durable memories from one conversation turn."""
    for kind, content in extract_memory_candidates(user_message, ai_response):
        save_memory(kind, content)


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


def get_recent_durable_memories():
    """Return recent durable memories for broad memory questions."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, kind, content, created_at
            FROM memories
            ORDER BY id DESC
            LIMIT ?
            """,
            (MAX_MEMORY_RESULTS,),
        ).fetchall()

    return [
        {
            "score": 10,
            "type": "memory",
            "id": memory_id,
            "kind": kind,
            "content": content,
            "created_at": created_at,
        }
        for memory_id, kind, content, created_at in rows
    ]


def search_long_term_memory(query):
    """
    Search durable memories and previous messages related to the new question.

    This keeps long-term memory useful without dumping the entire chat history
    into every prompt.
    """
    keywords = get_keywords(query)

    if is_memory_question(query):
        return get_recent_durable_memories()

    if not keywords:
        return []

    results = []

    with get_connection() as connection:
        memory_rows = connection.execute(
            "SELECT id, kind, content, created_at FROM memories"
        ).fetchall()
        message_rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT 80
            """
        ).fetchall()

        for memory_id, kind, content, created_at in memory_rows:
            score = score_text(content, keywords)

            if score > 0:
                results.append(
                    {
                        "score": score + 3,
                        "type": "memory",
                        "id": memory_id,
                        "kind": kind,
                        "content": content,
                        "created_at": created_at,
                    }
                )

        for message_id, role, content, created_at in message_rows:
            score = score_text(content, keywords)

            if score > 0:
                results.append(
                    {
                        "score": score,
                        "type": "message",
                        "id": message_id,
                        "kind": role,
                        "content": content,
                        "created_at": created_at,
                    }
                )

    results.sort(key=lambda item: item["score"], reverse=True)
    selected = results[:MAX_MEMORY_RESULTS]

    if selected:
        with get_connection() as connection:
            for result in selected:
                if result["type"] == "memory":
                    connection.execute(
                        "UPDATE memories SET last_used_at = ? WHERE id = ?",
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
            f"[M{index}] {result['type']} / {result['kind']} / "
            f"{result['created_at']}: {result['content']}"
        )

    return "\n".join(lines)


def get_memory_stats():
    """Return basic memory database counts."""
    with get_connection() as connection:
        message_count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        memory_count = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    return {
        "messages": message_count,
        "memories": memory_count,
        "database": str(DATABASE_FILE),
    }
