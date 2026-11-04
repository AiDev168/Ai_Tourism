# RAG persistence contract — MVP baseline

This document defines the database boundary only. It does not select, benchmark or implement the user's RAG algorithm.

## Ingestion path

```text
Source registry
    -> knowledge_documents (source + raw text + hash + freshness/provenance)
        -> knowledge_chunks (document id + order + text + hash + metadata)
            -> chunk_embeddings (chunk id + embedding_space id + vector)
```

## Required guarantees

1. A document must retain a source, source classification, stable document key and content hash.
2. A chunk must have a document parent, deterministic chunk index and content hash.
3. An embedding must reference exactly one chunk and one embedding space.
4. `(document_id, chunk_index)` is unique.
5. `(chunk_id, embedding_space_id)` is unique.
6. The stored vector dimension must equal the dimension configured in `embedding_spaces`.
7. Changing a model/provider/preprocessing pipeline creates or selects a new embedding space; the database schema is not tied to a particular model name or dimension.
8. Only active/verified real sources may be used in production retrieval. Synthetic test fixtures are never production evidence.
9. Dynamic facts such as weather, prices and availability require their own freshness/expiry contract; they must not be treated as permanent knowledge documents.

## Retrieval baseline tested here

The smoke test persists deterministic 3D and 4D test vectors, filters rows by `embedding_space_id`, runs exact cosine-distance ordering through pgvector, checks the expected nearest chunk, and confirms that a vector with the wrong dimension is rejected. All test rows are rolled back at the end.

This verifies the database's RAG storage/retrieval contract. It does **not** measure semantic relevance, recall, MRR, reranker quality, chunking quality, prompt quality or answer faithfulness. Those remain in the user's independent RAG algorithm work and will be connected through a replaceable provider interface.

## Why exact search first

pgvector supports exact nearest-neighbor search by default and optional approximate indexes such as HNSW and IVFFlat. Exact search is the correctness baseline at small data sizes. Approximate indexing changes retrieval behavior and should be introduced only after profiling and recall checks on the selected embedding space.

## Suggested adapter interface (for later implementation)

```python
class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...

    def embed_query(self, text: str) -> Sequence[float]: ...
```

The application owns provider selection and credentials. API keys remain on the backend and are never placed in PWA code, SQL seeds, or this database package.


## Current pre-Codex test boundary

The SQL smoke test inserts deterministic 3D and 4D vectors in a transaction, runs exact cosine-nearest-neighbor ordering, validates per-space dimension guards, then rolls the test data back. This validates pgvector persistence/query plumbing and dimension isolation only. It does **not** validate Persian semantic relevance, Recall@K, MRR/nDCG, chunking quality, reranking, answer faithfulness, or the owner's RAG algorithm. Those remain adapter-level integration/acceptance tests and must use the owner's selected RAG implementation when it is connected. No embedding model or dimension is selected by this database package.
