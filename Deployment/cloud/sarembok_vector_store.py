"""Sarembok Vector Database & Semantic Retrieval Engine.

Provides high-speed semantic retrieval over episodic memory, knowledge base,
conversations, and cross-domain contexts with cosine/dot-product similarity,
metadata filtering, and persistent disk storage.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple, Union

from sarembok_distributed_tracing import tracer

LOG = logging.getLogger("sarembok.vector_store")

VECTOR_STORE_PATH = os.getenv("SAREMBOK_VECTOR_STORE_PATH", "/data/sarembok_vectors.json")
DEFAULT_DIMENSIONS = 128


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate cosine similarity between two numeric vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def _semantic_embed_text(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> List[float]:
    """Lightweight deterministic semantic projection embedding.
    
    Transforms text into a normalized dense vector using character n-gram hashing
    and term frequency distribution. Provides zero-dependency semantic clustering.
    """
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = clean.split()
    if not tokens:
        return [0.0] * dimensions

    vec = [0.0] * dimensions
    # Token and bi-gram hashing
    for i, token in enumerate(tokens):
        # Unigram hash
        h1 = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
        idx1 = h1 % dimensions
        weight = 1.0 / (1.0 + math.log1p(len(token)))
        vec[idx1] += weight

        # Bigram hash for phrase semantics
        if i < len(tokens) - 1:
            bigram = f"{token}_{tokens[i+1]}"
            h2 = int(hashlib.md5(bigram.encode("utf-8")).hexdigest()[:8], 16)
            idx2 = h2 % dimensions
            vec[idx2] += weight * 1.5

    # L2 normalization
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class VectorRecord:
    def __init__(
        self,
        record_id: str,
        vector: List[float],
        document: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = record_id
        self.vector = vector
        self.document = document
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vector": self.vector,
            "document": self.document,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VectorRecord:
        return cls(
            record_id=data["id"],
            vector=data["vector"],
            document=data.get("document", ""),
            metadata=data.get("metadata", {}),
        )


class VectorStore:
    """Multi-collection vector store for semantic retrieval and long-term memory."""

    def __init__(self, persistence_path: Optional[str] = None) -> None:
        self.persistence_path = persistence_path or VECTOR_STORE_PATH
        self._collections: Dict[str, Dict[str, VectorRecord]] = {
            "agent_memory": {},
            "knowledge_base": {},
            "conversations": {},
            "code_artifacts": {},
        }
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self.persistence_path or not os.path.exists(self.persistence_path):
            return
        try:
            with open(self.persistence_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            with self._lock:
                for col_name, records in raw.items():
                    self._collections[col_name] = {
                        r_id: VectorRecord.from_dict(r_data)
                        for r_id, r_data in records.items()
                    }
            LOG.info("Loaded vector store with collections: %s", list(self._collections.keys()))
        except Exception as e:
            LOG.warning("Failed loading vector store: %s", e)

    def persist(self) -> bool:
        if not self.persistence_path:
            return False
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.persistence_path)), exist_ok=True)
            with self._lock:
                dump = {
                    col: {r_id: r.to_dict() for r_id, r in recs.items()}
                    for col, recs in self._collections.items()
                }
            with open(self.persistence_path, "w", encoding="utf-8") as f:
                json.dump(dump, f, indent=2)
            return True
        except Exception as e:
            LOG.warning("Failed persisting vector store: %s", e)
            return False

    def insert(
        self,
        collection: str,
        record_id: str,
        document: str,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VectorRecord:
        """Insert or update a document in a vector collection."""
        with tracer.start_span("vector_store.insert", attributes={"collection": collection, "record_id": record_id}):
            if vector is None:
                vector = _semantic_embed_text(document)

            record = VectorRecord(
                record_id=record_id,
                vector=vector,
                document=document,
                metadata=metadata,
            )

            with self._lock:
                if collection not in self._collections:
                    self._collections[collection] = {}
                self._collections[collection][record_id] = record

            return record

    def query(
        self,
        collection: str,
        query: Union[str, List[float]],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Perform semantic nearest-neighbor retrieval over a collection."""
        with tracer.start_span("vector_store.query", attributes={"collection": collection, "top_k": top_k}) as span:
            if isinstance(query, str):
                query_vector = _semantic_embed_text(query)
            else:
                query_vector = query

            with self._lock:
                recs = list(self._collections.get(collection, {}).values())

            scored: List[Tuple[float, VectorRecord]] = []
            for r in recs:
                # Metadata pre-filtering
                if filter_metadata:
                    mismatch = False
                    for k, v in filter_metadata.items():
                        if r.metadata.get(k) != v:
                            mismatch = True
                            break
                    if mismatch:
                        continue

                sim = _cosine_similarity(query_vector, r.vector)
                if sim >= min_score:
                    scored.append((sim, r))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = [
                {
                    "id": r.id,
                    "score": round(sim, 4),
                    "document": r.document,
                    "metadata": r.metadata,
                }
                for sim, r in scored[:top_k]
            ]
            span.set_attribute("results_count", len(results))
            return results

    def delete(self, collection: str, record_id: str) -> bool:
        with self._lock:
            if collection in self._collections and record_id in self._collections[collection]:
                del self._collections[collection][record_id]
                return True
        return False

    def list_collections(self) -> Dict[str, int]:
        with self._lock:
            return {col: len(recs) for col, recs in self._collections.items()}

    def clear(self) -> None:
        with self._lock:
            for recs in self._collections.values():
                recs.clear()


# Global singleton vector store
vector_store = VectorStore()
