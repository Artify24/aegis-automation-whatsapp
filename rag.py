"""RAG Knowledge Engine — indexes local business documents and answers FAQs.

Supports:
  - Markdown (.md)
  - Plain text (.txt)
  - JSON (.json)
  - CSV (.csv)
  - PDF (.pdf via pypdf)

Hot-reloading: detects file changes in knowledge/ automatically.
Retrieval: pure-Python BM25 + n-gram keyword scoring. Sub-millisecond, zero extra APIs needed.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import config
import llm

logger = logging.getLogger("aegisbot.rag")

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


@dataclass
class DocumentChunk:
    id: str
    source_file: str
    title: str
    content: str
    tokens: Set[str] = field(default_factory=set)
    term_freq: Dict[str, int] = field(default_factory=dict)
    length: int = 0


class KnowledgeBase:
    """In-memory searchable knowledge base with hot-reload."""

    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR) -> None:
        self.knowledge_dir = knowledge_dir
        self.chunks: List[DocumentChunk] = []
        self._doc_freqs: Dict[str, int] = {}
        self._avg_chunk_length: float = 1.0
        self._last_loaded_mtime: float = 0.0
        self.reload()

    def _get_latest_mtime(self) -> float:
        if not self.knowledge_dir.exists():
            return 0.0
        mtimes = [0.0]
        for f in self.knowledge_dir.rglob("*"):
            if f.is_file():
                try:
                    mtimes.append(f.stat().st_mtime)
                except OSError:
                    pass
        return max(mtimes)

    def maybe_reload(self) -> None:
        """Reload if directory files have changed on disk."""
        latest = self._get_latest_mtime()
        if latest > self._last_loaded_mtime:
            logger.info("Knowledge directory updated on disk — reloading index...")
            self.reload()

    def reload(self) -> None:
        """Scan directory and index all documents."""
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        chunks: List[DocumentChunk] = []

        for p in sorted(self.knowledge_dir.rglob("*")):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            try:
                if ext in (".md", ".txt"):
                    chunks.extend(self._parse_markdown(p))
                elif ext == ".json":
                    chunks.extend(self._parse_json(p))
                elif ext == ".csv":
                    chunks.extend(self._parse_csv(p))
                elif ext == ".pdf":
                    chunks.extend(self._parse_pdf(p))
            except Exception as e:
                logger.error("Failed to parse knowledge file %s: %s", p.name, e)

        # compute BM25 statistics
        doc_freqs: Dict[str, int] = {}
        total_len = 0
        for c in chunks:
            total_len += c.length
            for token in c.tokens:
                doc_freqs[token] = doc_freqs.get(token, 0) + 1

        self.chunks = chunks
        self._doc_freqs = doc_freqs
        self._avg_chunk_length = (total_len / max(1, len(chunks)))
        self._last_loaded_mtime = self._get_latest_mtime()
        logger.info("Indexed %d knowledge chunks from %s", len(self.chunks), self.knowledge_dir)

    # ── Parsers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [w for w in cleaned.split() if len(w) > 1]
        return tokens

    def _make_chunk(self, source: str, title: str, content: str, idx: int) -> DocumentChunk:
        raw_tokens = self._tokenize(title + " " + content)
        tf: Dict[str, int] = {}
        for t in raw_tokens:
            tf[t] = tf.get(t, 0) + 1
        return DocumentChunk(
            id=f"{source}:{idx}",
            source_file=source,
            title=title.strip(),
            content=content.strip(),
            tokens=set(raw_tokens),
            term_freq=tf,
            length=len(raw_tokens),
        )

    def _parse_markdown(self, path: Path) -> List[DocumentChunk]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        sections = re.split(r"(?m)^(?=#{1,3}\s+)", text)
        chunks: List[DocumentChunk] = []
        for i, sec in enumerate(sections):
            if not sec.strip():
                continue
            lines = sec.strip().splitlines()
            title = lines[0].lstrip("#").strip() if lines else path.stem
            chunks.append(self._make_chunk(path.name, title, sec.strip(), i))
        return chunks

    def _parse_json(self, path: Path) -> List[DocumentChunk]:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        chunks: List[DocumentChunk] = []
        if isinstance(data, dict):
            for i, (k, v) in enumerate(data.items()):
                val_str = json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v)
                content = f"{k.replace('_', ' ').title()}: {val_str}"
                chunks.append(self._make_chunk(path.name, k, content, i))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                content = json.dumps(item, indent=2) if isinstance(item, dict) else str(item)
                chunks.append(self._make_chunk(path.name, f"{path.stem} #{i+1}", content, i))
        return chunks

    def _parse_csv(self, path: Path) -> List[DocumentChunk]:
        import csv
        chunks: List[DocumentChunk] = []
        with open(path, mode="r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                content = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
                title = row.get("name") or row.get("title") or f"Row #{i+1}"
                chunks.append(self._make_chunk(path.name, title, content, i))
        return chunks

    def _parse_pdf(self, path: Path) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            for i, page in enumerate(reader.pages):
                txt = (page.extract_text() or "").strip()
                if txt:
                    # split large pages by double newline
                    paragraphs = [p.strip() for p in txt.split("\n\n") if len(p.strip()) > 30]
                    for j, para in enumerate(paragraphs or [txt]):
                        title = f"Page {i+1} Part {j+1}"
                        chunks.append(self._make_chunk(path.name, title, para, len(chunks)))
        except Exception as e:
            logger.warning("pypdf error reading %s: %s", path.name, e)
        return chunks

    # ── BM25 Search ───────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> List[Tuple[DocumentChunk, float]]:
        """Retrieve most relevant chunks for a user query."""
        self.maybe_reload()
        if not self.chunks or not query.strip():
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        # BM25 parameters
        k1 = 1.5
        b = 0.75
        n_docs = len(self.chunks)
        scores: List[Tuple[DocumentChunk, float]] = []

        for chunk in self.chunks:
            score = 0.0
            doc_len = chunk.length
            for qt in q_tokens:
                if qt not in chunk.tokens:
                    continue
                tf = chunk.term_freq.get(qt, 0)
                df = self._doc_freqs.get(qt, 0)
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                numerator = tf * (k1 + 1.0)
                denominator = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, self._avg_chunk_length)))
                score += idf * (numerator / max(1e-6, denominator))

            # bonus for exact phrase or title match
            low_q = query.lower()
            if low_q in chunk.title.lower():
                score += 3.0
            if any(qt in chunk.title.lower() for qt in q_tokens):
                score += 1.5

            if score > 0.0:
                scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_context(self, query: str, top_k: int = 3) -> Tuple[str, float]:
        """Returns (concatenated context string, max_score)."""
        results = self.search(query, top_k=top_k)
        if not results:
            return "", 0.0
        max_score = results[0][1]
        blocks = []
        for chunk, s in results:
            blocks.append(f"[{chunk.source_file} - {chunk.title}]\n{chunk.content}")
        return "\n\n---\n\n".join(blocks), max_score


# Global singleton instance
_kb: Optional[KnowledgeBase] = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def answer_faq(question: str, history: Optional[List[Dict[str, str]]] = None) -> Tuple[str, bool]:
    """Answers customer question using RAG knowledge.

    Returns:
      (reply_text, has_knowledge_match)
    """
    kb = get_kb()
    context, score = kb.get_context(question, top_k=3)

    if not context or score < 0.8:
        # No strong match in docs
        return "", False

    prompt = (
        f"You are the official WhatsApp sales & support assistant for {config.BUSINESS_NAME}.\n"
        "Answer the customer's question accurately using ONLY the official business facts below.\n\n"
        f"OFFICIAL BUSINESS INFO:\n{context}\n\n"
        f"Customer asked: {question}\n\n"
        "Guidelines:\n"
        "- Reply in 2-4 lines, friendly WhatsApp style.\n"
        "- Give exact prices, timings, addresses, or policies from the text.\n"
        "- Use bullet points and appropriate emojis.\n"
        "- Never make up facts not mentioned in the info.\n"
        "- End with a polite follow-up or offer to help."
    )

    reply = llm.generate(prompt)
    if not reply or len(reply.strip()) < 10:
        return "", False

    return reply.strip(), True
