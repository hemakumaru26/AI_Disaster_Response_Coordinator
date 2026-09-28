"""Lazy ChromaDB and SentenceTransformer retrieval for prototype guidance."""

import hashlib
from pathlib import Path

from rag.loader import load_knowledge_documents


DEFAULT_VECTOR_STORE_DIR = Path(__file__).resolve().parent / "vector_store"
DEFAULT_COLLECTION_NAME = "disaster_response_knowledge"
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


_MODEL_CACHE = {}
_CLIENT_CACHE = {}


def _embedding_model(model_name=DEFAULT_MODEL_NAME):
    """Return a cached embedding model singleton, avoiding reloading weights on each query."""
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]

    from sentence_transformers import SentenceTransformer

    try:
        try:
            model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            model = SentenceTransformer(model_name)
        _MODEL_CACHE[model_name] = model
        return model
    except Exception as error:
        raise RuntimeError(
            "Unable to load the embedding model. Cache the model locally or "
            "allow access to the model provider before building or querying the index."
        ) from error


def _chroma_client(vector_store_dir):
    """Return a cached Chroma client singleton for the directory."""
    dir_key = str(vector_store_dir)
    if dir_key in _CLIENT_CACHE:
        return _CLIENT_CACHE[dir_key]
    import chromadb

    client = chromadb.PersistentClient(path=dir_key)
    _CLIENT_CACHE[dir_key] = client
    return client


def _chunk_id(document):
    """Create a stable ID so rebuilding upserts rather than duplicates chunks."""
    value = f"{document['source']}:{document['chunk_index']}:{document['content']}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_vector_index(
    knowledge_dir=None,
    vector_store_dir=None,
    collection_name=DEFAULT_COLLECTION_NAME,
    model_name=DEFAULT_MODEL_NAME,
):
    """Index the project knowledge corpus without deleting existing collections.

    Repeated builds upsert stable chunk IDs. Other Chroma collections and the
    SQLite application database are never touched.
    """
    documents = load_knowledge_documents(knowledge_dir)
    store_directory = Path(vector_store_dir) if vector_store_dir is not None else DEFAULT_VECTOR_STORE_DIR
    model = _embedding_model(model_name)
    embeddings = model.encode(
        [document["content"] for document in documents],
        normalize_embeddings=True,
    ).tolist()

    collection = _chroma_client(store_directory).get_or_create_collection(
        name=collection_name,
        metadata={
            "hnsw:space": "cosine",
            "description": "Prototype disaster-response guidance",
        },
    )
    collection.upsert(
        ids=[_chunk_id(document) for document in documents],
        documents=[document["content"] for document in documents],
        metadatas=[
            {"source": document["source"], "chunk_index": document["chunk_index"]}
            for document in documents
        ],
        embeddings=embeddings,
    )
    return {"collection_name": collection_name, "indexed_chunks": len(documents)}


def retrieve_context(
    query,
    n_results=3,
    vector_store_dir=None,
    collection_name=DEFAULT_COLLECTION_NAME,
    model_name=DEFAULT_MODEL_NAME,
):
    """Return semantic matches as content/source/score dictionaries.

    A missing local index is treated as an empty result so importing or calling
    this optional foundation cannot bring down the rest of the application.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(n_results, int) or n_results < 1:
        raise ValueError("n_results must be a positive integer")

    store_directory = Path(vector_store_dir) if vector_store_dir is not None else DEFAULT_VECTOR_STORE_DIR
    if not store_directory.exists():
        return []

    client = _chroma_client(store_directory)
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return []
    if collection.count() == 0:
        return []

    query_embedding = _embedding_model(model_name).encode(
        [query.strip()], normalize_embeddings=True
    ).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    matches = []
    for content, metadata, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        matches.append(
            {
                "content": content,
                "source": metadata.get("source", "unknown"),
                "score": max(0.0, min(1.0, 1.0 - float(distance))),
            }
        )
    return matches


if __name__ == "__main__":
    result = build_vector_index()
    print(f"Indexed {result['indexed_chunks']} chunks in {result['collection_name']}.")
