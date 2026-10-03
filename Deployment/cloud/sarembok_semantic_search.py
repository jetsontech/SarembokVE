"""Sarembok Intelligent Semantic Search & Hybrid Retrieval Pipeline.

Provides automated document ingestion, semantic chunking, dense vector indexing,
and hybrid search (combining dense vector cosine similarity + lexical token matching)
with Reciprocal Rank Fusion (RRF) re-ranking.
"""

from __future__ import annotations

import logging
import math
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from sarembok_distributed_tracing import tracer
from sarembok_vector_store import vector_store, _semantic_embed_text

LOG = logging.getLogger("sarembok.semantic_search")


def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split long documents into overlapping semantic chunks for fine-grained retrieval."""
    clean = text.strip()
    if len(clean) <= chunk_size:
        return [clean] if clean else []

    chunks = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        # Snap to sentence or line boundary if possible
        if end < len(clean):
            last_period = clean.rfind(".", start, end)
            last_newline = clean.rfind("\n", start, end)
            boundary = max(last_period, last_newline)
            if boundary > start + (chunk_size // 2):
                end = boundary + 1

        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(clean):
            break
        start = end - overlap

    return chunks


def _lexical_score(query_tokens: Set[str], document: str) -> float:
    """Compute normalized token overlap score between query and document."""
    doc_tokens = set(re.findall(r"\w+", document.lower()))
    if not doc_tokens or not query_tokens:
        return 0.0
    common = query_tokens.intersection(doc_tokens)
    return len(common) / math.sqrt(len(query_tokens) * len(doc_tokens))


class IntelligentSearchEngine:
    """Hybrid semantic retrieval engine with automated ingestion and RRF re-ranking."""

    def __init__(self) -> None:
        pass

    def ingest_document(
        self,
        document_id: str,
        content: str,
        collection: str = "knowledge_base",
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
    ) -> List[str]:
        """Automatically chunk, embed, and index a document into the semantic vector store."""
        with tracer.start_span("semantic_search.ingest", attributes={"doc.id": document_id, "collection": collection}) as span:
            chunks = chunk_document(content, chunk_size=chunk_size)
            indexed_ids = []
            base_meta = dict(metadata or {})
            base_meta["parent_doc_id"] = document_id
            base_meta["ingested_at"] = time.time()

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chk_{i}"
                chunk_meta = dict(base_meta)
                chunk_meta["chunk_index"] = i
                chunk_meta["total_chunks"] = len(chunks)

                vector_store.insert(
                    collection=collection,
                    record_id=chunk_id,
                    document=chunk,
                    metadata=chunk_meta,
                )
                indexed_ids.append(chunk_id)

            span.set_attribute("chunks_indexed", len(indexed_ids))
            LOG.info("Ingested document %s (%d chunks) into %s", document_id, len(indexed_ids), collection)
            return indexed_ids

    def hybrid_search(
        self,
        query: str,
        collection: str = "knowledge_base",
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search merging dense semantic vector similarity and lexical token match."""
        with tracer.start_span("semantic_search.hybrid_query", attributes={"query": query, "collection": collection}) as span:
            query_clean = query.strip()
            if not query_clean:
                return []

            # 1. Dense Semantic Vector Search
            dense_results = vector_store.query(
                collection=collection,
                query=query_clean,
                top_k=top_k * 2,
                filter_metadata=filter_metadata,
            )

            # 2. Lexical Token Overlap Search across candidates
            query_tokens = set(re.findall(r"\w+", query_clean.lower()))

            # 3. Reciprocal Rank Fusion (RRF)
            # RRF Score = 1 / (k + rank_dense) + 1 / (k + rank_lexical)
            dense_ranks = {item["id"]: idx + 1 for idx, item in enumerate(dense_results)}

            # Also score lexical match across all retrieved items
            lexical_scored = []
            for item in dense_results:
                l_score = _lexical_score(query_tokens, item["document"])
                lexical_scored.append((l_score, item))
            lexical_scored.sort(key=lambda x: x[0], reverse=True)
            lexical_ranks = {item["id"]: idx + 1 for idx, (score, item) in enumerate(lexical_scored)}

            # Combine scores
            all_items = {item["id"]: item for item in dense_results}
            fused_scores: Dict[str, float] = {}

            for item_id in all_items.keys():
                d_rank = dense_ranks.get(item_id, 100)
                l_rank = lexical_ranks.get(item_id, 100)
                score = (1.0 / (rrf_k + d_rank)) + (1.0 / (rrf_k + l_rank))
                fused_scores[item_id] = score

            sorted_ids = sorted(fused_scores.keys(), key=lambda i: fused_scores[i], reverse=True)

            final_results = []
            for item_id in sorted_ids[:top_k]:
                item = all_items[item_id]
                final_results.append({
                    "id": item["id"],
                    "document": item["document"],
                    "metadata": item["metadata"],
                    "dense_score": item.get("score", 0.0),
                    "hybrid_rrf_score": round(fused_scores[item_id], 5),
                })

            span.set_attribute("results_returned", len(final_results))
            return final_results


# Global singleton intelligent search engine
search_engine = IntelligentSearchEngine()
