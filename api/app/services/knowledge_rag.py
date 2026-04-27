"""
Chunk published knowledge documents, embed with OpenAI, and semantic search for the store agent.
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from openai import OpenAI
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import KnowledgeChunk, KnowledgeDocument

logger = logging.getLogger(__name__)


def chunk_text(text: str, *, max_chars: int, overlap: int) -> list[str]:
    """Sliding-window chunks for RAG."""
    s = (text or "").strip()
    if not s:
        return []
    max_chars = max(200, max_chars)
    overlap = min(max(0, overlap), max_chars // 2)
    step = max_chars - overlap
    out: list[str] = []
    i = 0
    while i < len(s):
        piece = s[i : i + max_chars].strip()
        if piece:
            out.append(piece)
        i += step
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    a, b = a[:n], b[:n]
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _embed_batch(client: OpenAI, model: str, inputs: list[str]) -> list[list[float]]:
    if not inputs:
        return []
    r = client.embeddings.create(model=model, input=inputs)
    out: list[list[float]] = [[] for _ in inputs]
    for d in r.data:
        out[int(d.index)] = list(d.embedding)
    return out


def reindex_document(
    db: Session, document_id: int, settings: Settings | None = None
) -> int:
    """
    Rebuild chunks and embeddings for one document. Returns number of chunks.
    """
    settings = settings or get_settings()
    doc = db.get(KnowledgeDocument, document_id)
    if doc is None:
        return 0
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    if not (doc.is_published and (doc.body or "").strip()):
        db.commit()
        return 0

    chunks = chunk_text(
        doc.body,
        max_chars=settings.knowledge_chunk_max_chars,
        overlap=settings.knowledge_chunk_overlap,
    )
    if not chunks:
        db.commit()
        return 0

    key = (settings.openai_api_key or "").strip()
    embeddings: list[list[float] | None] = [None] * len(chunks)
    if key:
        try:
            client = OpenAI(api_key=key)
            # API allows batch embed
            em = _embed_batch(
                client, settings.openai_embedding_model, [c[:32_000] for c in chunks]
            )
            for i, v in enumerate(em):
                if v and len(v) > 1:
                    embeddings[i] = v
        except Exception as e:  # noqa: BLE001
            logger.exception("embedding batch: %s", e)

    for idx, c in enumerate(chunks):
        emb = embeddings[idx] if idx < len(embeddings) else None
        db.add(
            KnowledgeChunk(
                document_id=document_id,
                chunk_index=idx,
                content=c,
                embedding=emb,
            )
        )
    db.commit()
    return len(chunks)


def _fallback_keyword_hits(
    db: Session, query: str, top_k: int
) -> list[dict[str, Any]]:
    words = [w for w in re.split(r"\W+", (query or "").lower()) if len(w) > 2]
    if not words:
        return []
    rows = (
        db.execute(
            select(KnowledgeChunk, KnowledgeDocument.title)
            .join(
                KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id
            )
            .where(KnowledgeDocument.is_published.is_(True))
        )
        .all()
    )
    scored: list[tuple[float, str, int, str, str]] = []
    for ch, title in rows:
        low = (ch.content or "").lower()
        score = sum(1 for w in words if w in low)
        if score > 0:
            scored.append(
                (float(score), title or "", ch.document_id, ch.content, "keyword")
            )
    scored.sort(key=lambda x: -x[0])
    out: list[dict[str, Any]] = []
    for t in scored[:top_k]:
        out.append(
            {
                "title": t[1],
                "document_id": t[2],
                "snippet": (t[3] or "")[:1200],
                "score": t[0],
                "source": t[4],
            }
        )
    return out


def search_knowledge(
    db: Session, query: str, settings: Settings | None = None
) -> list[dict[str, Any]]:
    """
    Return top knowledge snippets (semantic if embeddings available, else keyword).
    """
    settings = settings or get_settings()
    top_k = max(1, min(settings.knowledge_search_top_k, 20))
    q = (query or "").strip()
    if not q:
        return []

    # Load published chunks with optional embeddings
    rows = (
        db.execute(
            select(KnowledgeChunk, KnowledgeDocument)
            .join(
                KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id
            )
            .where(KnowledgeDocument.is_published.is_(True))
        )
        .all()
    )
    with_emb: list[tuple[KnowledgeChunk, KnowledgeDocument, list[float]]] = []
    for ch, d in rows:
        emb = ch.embedding
        if isinstance(emb, list) and emb and all(isinstance(x, (int, float)) for x in emb):
            with_emb.append((ch, d, [float(x) for x in emb]))
    key = (settings.openai_api_key or "").strip()
    if with_emb and key:
        try:
            client = OpenAI(api_key=key)
            ev = _embed_batch(client, settings.openai_embedding_model, [q[:8000]])[0]
            if ev and len(ev) > 1:
                dist: list[tuple[float, KnowledgeChunk, KnowledgeDocument]] = []
                for ch, d, e in with_emb:
                    if len(e) == len(ev):
                        dist.append((_cosine(ev, e), ch, d))
                dist.sort(key=lambda x: -x[0])
                out: list[dict[str, Any]] = []
                for sc, ch, d in dist[:top_k]:
                    out.append(
                        {
                            "title": d.title,
                            "document_id": d.id,
                            "snippet": (ch.content or "")[:1200],
                            "score": round(sc, 4),
                            "source": "semantic",
                        }
                    )
                if out:
                    return out
        except Exception as e:  # noqa: BLE001
            logger.exception("semantic search: %s", e)

    return _fallback_keyword_hits(db, q, top_k)


def search_knowledge_response_json(
    db: Session, query: str, settings: Settings | None = None
) -> str:
    hits = search_knowledge(db, query, settings)
    if not hits:
        return json.dumps(
            {
                "ok": True,
                "hits": [],
                "message": "No knowledge base results (publish articles with content).",
            }
        )
    return json.dumps({"ok": True, "query": (query or "").strip(), "hits": hits})
