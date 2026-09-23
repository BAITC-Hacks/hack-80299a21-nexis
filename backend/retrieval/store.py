"""SQLite knowledge index, lexical ranking and optional persisted embeddings.

Only the curated JSON corpus is ingested. No network request occurs during a
normal lexical build. Embeddings must be explicitly enabled by the operator.
"""
import hashlib
import json
import math
import os
import re
import sqlite3
import time
import uuid
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from threading import RLock

ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "database" / "knowledge" / "articles.json"
_deadline = ContextVar("knowledge_request_deadline", default=None)
STOP = set("и в на для как что это ли с по мне нужен нужна нужно чем от или а the a an is are what how of to for in do can i please explain tell about не бар ма қалай неге және бұл керек қандай me my you your does us our который где есть у меня туралы такое такой такая такие такой каким какими какой которая которые могу может можете вы мы я собой представляет объясни объясните расскажи пожалуйста между деген нені неге қайдан қанша болады бола пен мен осы аламын жасаймын білдіреді get have obtain who which another other".split())
POLICY_TOPICS = {
    "returns": r"возврат|вернут|обмен|қайтар|ауыстыр|\b(?:returns?|refund|exchange)\b",
    "delivery": r"достав|самовывоз|отправ|жеткіз|алып кет|\b(?:delivery|shipping|ships?|dispatch|collection|pickup)\b",
    "payment": r"оплат|заплат|төлем|төле|\b(?:payments?|pay|paid)\b",
    "quantity": r"минимальн|кратност|ең аз|еселік|\bminimum\b|pack multiple",
    "certificates": r"сертифик|сәйкестік|\bcertificat\w*",
    "warranty": r"гарант|кепіл|\bwarrant\w*",
}
TOPIC_TERMS = {"returns": "return", "delivery": "delivery", "payment": "payment",
               "quantity": "minimum", "certificates": "certificate", "warranty": "warranty"}


def query_context(query):
    text = str(query).lower()
    topics = {topic for topic, pattern in POLICY_TOPICS.items() if re.search(pattern, text)}
    subjects = set()
    if re.search(r"\b(?:узо|қақ|rcd|rccb)\b", text): subjects.add("rcd")
    if re.search(r"дифавтомат|\brcbo\b", text): subjects.add("rcbo")
    if re.search(r"\bавтомат(?:а|ом|ы|ов|қа|тың)?\b|\bmcb\b", text): subjects.add("mcb")
    if not subjects and re.search(r"\bcircuit breaker\b", text): subjects.add("mcb")
    comparison = bool(re.search(r"отлич|разниц|сравни|айырмаш|салыстыр|difference|compare", text))
    definition = not comparison and bool(re.search(r"что такое|что представляет|для чего|деген не|what (?:is|are)|define", text))
    return topics, subjects, "comparison" if comparison else "definition" if definition else None


def tokens(value):
    return [word for word in re.findall(r"[\w]+", str(value).lower().replace("ё", "е"))
            if len(word) > 1 and word not in STOP]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def load_articles(path=CORPUS_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    articles = data["articles"]
    seen = set()
    for item in articles:
        if not item.get("id") or item["id"] in seen:
            raise ValueError("Each knowledge article needs a unique id")
        seen.add(item["id"])
        if not item.get("source_url") or not item.get("version") or not item.get("verification_status"):
            raise ValueError("Knowledge provenance is required")
        if set(item.get("translations", {})) != {"ru", "kk", "en"}:
            raise ValueError("Every article needs ru, kk and en translations")
        if any(not text.get("title") or not text.get("content") for text in item["translations"].values()):
            raise ValueError("Empty knowledge translation")
    return articles


def chunks(text, words=350):
    parts = text.split()
    return [" ".join(parts[index:index + words]) for index in range(0, len(parts), words)]


def embed(texts, model):
    from openai import OpenAI
    deadline = _deadline.get()
    remaining = deadline - time.monotonic() if deadline is not None else 6.0
    if remaining <= 0:
        raise TimeoutError("Retrieval request deadline exceeded")
    with OpenAI(timeout=min(6.0, remaining), max_retries=0) as client:
        response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


@contextmanager
def request_deadline(deadline_monotonic):
    token = _deadline.set(deadline_monotonic)
    try:
        yield
    finally:
        _deadline.reset(token)


class KnowledgeIndex:
    def __init__(self, path=None, corpus_path=CORPUS_PATH):
        self.path = Path(path or os.getenv("NEXIS_KNOWLEDGE_DB_PATH", str(ROOT / "database" / "knowledge.sqlite3")))
        self.corpus_path = Path(corpus_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self._signature = None
        self._db_signature = None
        self._cached_rows = None
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    chunk_id TEXT PRIMARY KEY, article_id TEXT NOT NULL, language TEXT NOT NULL,
                    text TEXT NOT NULL, payload TEXT NOT NULL, content_hash TEXT NOT NULL,
                    embedding TEXT, embedding_model TEXT);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def build(self, with_embeddings=False, embedder=None, model=None):
        articles = load_articles(self.corpus_path)
        corpus_hash = digest(articles)
        model = model or os.getenv("NEXIS_EMBEDDING_MODEL", "text-embedding-3-small")
        with self.lock, self.connection() as db:
            existing = {row[0]: row[1:] for row in db.execute(
                "SELECT chunk_id,content_hash,embedding,embedding_model FROM knowledge_chunks")}
            rows, needs = [], []
            for item in articles:
                for language, translation in item["translations"].items():
                    for index, text in enumerate(chunks(translation["content"])):
                        chunk_id = f"{item['id']}:{language}:{index}"
                        content_hash = digest([item, language, text])
                        old = existing.get(chunk_id)
                        vector = old[1] if old and old[0] == content_hash and old[2] == model else None
                        payload = {**item, "title": translation["title"], "content": text,
                                   "language": language, "source_id": item.get("source_id", item["id"]),
                                   "chunk_id": chunk_id, "content_hash": content_hash}
                        row = [chunk_id, item["id"], language, text, json.dumps(payload, ensure_ascii=False),
                               content_hash, vector, model if vector else None]
                        rows.append(row)
                        if with_embeddings and vector is None:
                            needs.append((len(rows)-1, translation["title"] + "\n" + text))
            # Compute all changed vectors before touching the committed generation.
            for start in range(0, len(needs), 32):
                batch = needs[start:start+32]
                vectors = (embedder or embed)([text for _, text in batch], model)
                if len(vectors) != len(batch):
                    raise ValueError("Embedding batch size mismatch")
                for (index, _), vector in zip(batch, vectors):
                    if not vector or any(not math.isfinite(float(value)) for value in vector):
                        raise ValueError("Invalid embedding")
                    rows[index][6:8] = [json.dumps(vector), model]
            db.execute("DELETE FROM knowledge_chunks")
            db.executemany("INSERT INTO knowledge_chunks VALUES (?,?,?,?,?,?,?,?)", rows)
            db.execute("INSERT OR REPLACE INTO knowledge_meta VALUES ('corpus_hash',?)", (corpus_hash,))
            db.execute("INSERT OR REPLACE INTO knowledge_meta VALUES ('generation',?)", (uuid.uuid4().hex,))
            db.commit()
            self._signature = (self.corpus_path.stat().st_mtime_ns, self.corpus_path.stat().st_size)
            self._cached_rows = None
            self._db_signature = (self.path.stat().st_mtime_ns, self.path.stat().st_size)
        return self.status()

    def ensure(self):
        signature = (self.corpus_path.stat().st_mtime_ns, self.corpus_path.stat().st_size)
        with self.lock:
            db_signature = (self.path.stat().st_mtime_ns, self.path.stat().st_size)
            if self._signature == signature and self._db_signature == db_signature:
                return
            self._cached_rows = None
            articles = load_articles(self.corpus_path)
            with self.connection() as db:
                row = db.execute("SELECT value FROM knowledge_meta WHERE key='corpus_hash'").fetchone()
            if not row or row[0] != digest(articles):
                self.build()
            self._signature = signature
            self._db_signature = (self.path.stat().st_mtime_ns, self.path.stat().st_size)

    def status(self):
        model = os.getenv("NEXIS_EMBEDDING_MODEL", "text-embedding-3-small")
        with self.connection() as db:
            count, articles, vectors = db.execute(
                "SELECT COUNT(*),COUNT(DISTINCT article_id),COUNT(embedding) FROM knowledge_chunks").fetchone()
            version = db.execute("SELECT value FROM knowledge_meta WHERE key='corpus_hash'").fetchone()
            matching_vectors = db.execute("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NOT NULL AND embedding_model=?", (model,)).fetchone()[0]
        enabled = os.getenv("NEXIS_EMBEDDINGS_ENABLED", "false").lower() == "true"
        key_available = bool(os.getenv("OPENAI_API_KEY"))
        ready = enabled and key_available and matching_vectors == count and count > 0
        reason = ("embeddings_disabled" if not enabled else "embedding_key_missing" if not key_available
                  else "embeddings_not_indexed" if not matching_vectors else "embedding_index_partial" if matching_vectors != count else None)
        return {"documents": articles, "chunks": count, "embedded_chunks": vectors,
                "active_model_chunks": matching_vectors, "embedding_model": model,
                "retrieval_mode": "hybrid" if ready else "lexical", "fallback_reason": reason,
                "corpus_hash": version[0] if version else None,
                "embeddings_enabled": enabled, "embedding_key_available": key_available,
                "translation_review": "kk_requires_native_review"}

    def _rows(self):
        with self.lock:
            if self._cached_rows is None:
                with self.connection() as db:
                    self._cached_rows = db.execute("SELECT payload,embedding,embedding_model FROM knowledge_chunks").fetchall()
            return self._cached_rows

    def search(self, query, limit=3, language="ru", embedder=None):
        self.ensure()
        language = language if language in {"ru", "kk", "en"} else "ru"
        topics, subjects, answer_kind = query_context(query)
        query_tokens = list(dict.fromkeys(tokens(query) + [TOPIC_TERMS[topic] for topic in topics]))
        if not query_tokens or limit < 1:
            return []
        rows = [(json.loads(payload), json.loads(vector) if vector else None, model)
                for payload, vector, model in self._rows()]
        # Query all translations; return the requested translation of each article.
        # Shared article identity provides cross-language lexical retrieval offline.
        documents = []
        for item, vector, model in rows:
            text_tokens = tokens(item["title"] + " " + item["content"] + " " + " ".join(item.get("keywords", [])))
            title_tokens = tokens(item["title"])
            documents.append((item, vector, model, text_tokens, title_tokens))
        frequencies = Counter(token for _, _, _, terms, _ in documents for token in set(terms))
        lexical = []
        for index, (item, _, _, terms, title_terms) in enumerate(documents):
            score = 0.0
            keyword_terms = tokens(" ".join(item.get("keywords", [])))
            for word in query_tokens:
                matches = [term for term in set(terms) if term == word or
                           (min(len(term), len(word)) >= 4 and (term.startswith(word) or word.startswith(term)))]
                # Count each query concept once; many incidental inflected words
                # in the body must not outweigh the actual subject in the title.
                score += max((math.log(1 + len(documents) / (1 + frequencies[term])) *
                              (5 if term in title_terms else 2 if term in keyword_terms else 1) *
                              (1 if term == word else .8) for term in matches), default=0)
            if score:
                if topics:
                    score *= 3 if item.get("category") in topics else .4
                    focus = item.get("focus_keywords", [])
                    if focus and not any(stem in str(query).lower() for stem in focus):
                        score *= .25
                if subjects and not topics:
                    article_subjects = set(item.get("subjects", []))
                    if article_subjects:
                        score *= 2 if subjects == article_subjects else 1 if subjects & article_subjects else .1
                        if answer_kind and item.get("answer_kind") == answer_kind:
                            score *= 2
                lexical.append((index, score / (1 + len(terms) / 350)))
        lexical.sort(key=lambda entry: entry[1], reverse=True)
        scores = {index: 1 / (60 + rank) for rank, (index, _) in enumerate(lexical, 1)}
        mode, fallback = "lexical", None
        if os.getenv("NEXIS_EMBEDDINGS_ENABLED", "false").lower() == "true":
            model = os.getenv("NEXIS_EMBEDDING_MODEL", "text-embedding-3-small")
            candidates = [(index, vector) for index, (_, vector, vector_model, _, _) in enumerate(documents)
                          if vector and vector_model == model]
            if candidates:
                try:
                    if _deadline.get() is not None and time.monotonic() >= _deadline.get():
                        raise TimeoutError("Retrieval request deadline exceeded")
                    query_vector = (embedder or embed)([str(query)[:4000]], model)[0]
                    if not query_vector or any(not math.isfinite(float(value)) for value in query_vector):
                        raise ValueError("Invalid query embedding")
                    norm = math.sqrt(sum(value * value for value in query_vector))
                    semantic = []
                    for index, vector in candidates:
                        if len(vector) != len(query_vector):
                            continue
                        divisor = norm * math.sqrt(sum(value * value for value in vector))
                        similarity = sum(a*b for a,b in zip(vector, query_vector))/divisor if divisor else 0
                        if similarity >= .3:
                            semantic.append((index, similarity))
                    for rank, (index, _) in enumerate(sorted(semantic, key=lambda row: row[1], reverse=True), 1):
                        scores[index] = scores.get(index, 0) + 1 / (60 + rank)
                    mode = "hybrid"
                except Exception:
                    fallback = "embedding_query_failed"
            else:
                fallback = "embeddings_not_indexed"
        results, seen = [], set()
        for index, score in sorted(scores.items(), key=lambda row: row[1], reverse=True):
            hit = documents[index][0]
            if hit["id"] in seen:
                continue
            seen.add(hit["id"])
            localized = hit
            if hit["language"] != language:
                ordinal = hit["chunk_id"].rsplit(":", 1)[1]
                translated_id = f"{hit['id']}:{language}:{ordinal}"
                localized = next((row[0] for row in documents if row[0]["chunk_id"] == translated_id), None)
                if localized is None:
                    # Keep the translated chunk's own provenance when lengths differ.
                    localized = next(row[0] for row in documents if row[0]["id"] == hit["id"] and row[0]["language"] == language)
            results.append({**localized, "score": round(score, 6), "retrieval_mode": mode,
                            "matched_language": hit["language"], "matched_chunk_id": hit["chunk_id"],
                            "fallback_reason": fallback})
            if len(results) >= min(limit, 10):
                break
        return results
