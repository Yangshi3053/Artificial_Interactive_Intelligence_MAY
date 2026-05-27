import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_FOLDER = PROJECT_ROOT / "knowledge_base" / "documents"
INDEX_FILE = PROJECT_ROOT / "knowledge_base" / "index.json"

SUPPORTED_FILE_TYPES = [".txt", ".md"]
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def read_text_file(file_path):
    """Read a text file with a few common encodings."""
    encodings = ["utf-8", "utf-8-sig", "gbk"]

    for encoding in encodings:
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    return file_path.read_text(encoding="utf-8", errors="ignore")


def split_into_chunks(text):
    """
    Split a long document into smaller text chunks.

    Smaller chunks make search results easier to send to the model.
    """
    cleaned_text = " ".join(text.split())

    if not cleaned_text:
        return []

    chunks = []
    start = 0

    while start < len(cleaned_text):
        end = start + CHUNK_SIZE
        chunks.append(cleaned_text[start:end])
        start = end - CHUNK_OVERLAP

        if start < 0:
            start = 0

    return chunks


def build_index():
    """
    Build a simple local search index from files in knowledge_base/documents.

    This beginner version stores text chunks in JSON. It does not use a vector
    database yet, which keeps setup simple.
    """
    documents = []

    for file_path in DOCUMENTS_FOLDER.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_FILE_TYPES:
            continue

        text = read_text_file(file_path)
        chunks = split_into_chunks(text)

        for chunk_number, chunk_text in enumerate(chunks, start=1):
            documents.append(
                {
                    "source": str(file_path.relative_to(PROJECT_ROOT)),
                    "chunk": chunk_number,
                    "text": chunk_text,
                }
            )

    INDEX_FILE.write_text(
        json.dumps(documents, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return len(documents)


def main():
    DOCUMENTS_FOLDER.mkdir(parents=True, exist_ok=True)
    chunk_count = build_index()

    print(f"Indexed {chunk_count} text chunks.")
    print(f"Index saved to: {INDEX_FILE}")


if __name__ == "__main__":
    main()
