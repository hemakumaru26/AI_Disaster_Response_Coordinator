"""Load prototype disaster-response knowledge documents into text chunks."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
SUPPORTED_SUFFIXES = {".md", ".txt"}


def discover_knowledge_files(knowledge_dir=None):
    """Return supported knowledge files in a stable order.

    Raises a clear error when the prototype corpus has not been created or does
    not contain any Markdown/text documents.
    """
    directory = Path(knowledge_dir) if knowledge_dir is not None else DEFAULT_KNOWLEDGE_DIR
    if not directory.is_dir():
        raise FileNotFoundError(f"Knowledge directory does not exist: {directory}")

    files = sorted(
        path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not files:
        raise ValueError(f"No .md or .txt knowledge documents found in: {directory}")
    return files


def chunk_text(text, chunk_size=800, overlap=100):
    """Split text into overlapping, whitespace-normalized chunks."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not isinstance(chunk_size, int) or chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    if not isinstance(overlap, int) or overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    chunks = []
    start = 0
    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        if end < len(normalized_text):
            boundary = normalized_text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(normalized_text[start:end].strip())
        if end == len(normalized_text):
            break
        start = end - overlap
    return chunks


def load_knowledge_documents(knowledge_dir=None, chunk_size=800, overlap=100):
    """Load knowledge files as dictionaries ready for vector indexing.

    Each dictionary has ``content``, ``source``, and ``chunk_index`` fields.
    Files are read only when this function is called, never at import time.
    """
    directory = Path(knowledge_dir) if knowledge_dir is not None else DEFAULT_KNOWLEDGE_DIR
    documents = []
    for path in discover_knowledge_files(directory):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"Knowledge file is not valid UTF-8: {path}") from error

        for chunk_index, content in enumerate(chunk_text(text, chunk_size, overlap)):
            documents.append(
                {
                    "content": content,
                    "source": path.relative_to(directory).as_posix(),
                    "chunk_index": chunk_index,
                }
            )
    if not documents:
        raise ValueError(f"Knowledge documents contain no readable text: {directory}")
    return documents


if __name__ == "__main__":
    loaded_documents = load_knowledge_documents()
    print(f"Loaded {len(loaded_documents)} knowledge chunks.")
