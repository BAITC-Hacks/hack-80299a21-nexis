"""Compatible facade over the persisted, multilingual curated knowledge base."""
from threading import RLock

from retrieval.store import KnowledgeIndex, load_articles, request_deadline

TERMS_URL = "https://ekt.kz/about/contacts/"
CONTACTS_URL = "https://ekt.kz/about/contacts/"
VERIFIED_AT = "2026-09-23"
_lock = RLock()
_index = None


def localize_article(item, language="ru"):
    language = "kk" if language == "kz" else language
    language = language if language in {"ru", "kk", "en"} else "ru"
    translations = item.get("translations", {})
    translated = {} if item.get("chunk_id") and item.get("language") == language else translations.get(language, {})
    return {**item, **translated, "language": language,
            "content_kk": translations.get("kk", {}).get("content", item.get("content_kk", "")),
            "content_en": translations.get("en", {}).get("content", item.get("content_en", ""))}


KB_ARTICLES = [localize_article(item) for item in load_articles()]


def get_index():
    global _index
    with _lock:
        if _index is None:
            _index = KnowledgeIndex()
        _index.ensure()
        return _index


def search_knowledge_base(query, limit=3, language="ru"):
    language = "kk" if language == "kz" else language
    return [localize_article(item, language) for item in get_index().search(query, limit, language)]


def source_metadata(item):
    keys = ("id", "title", "source_url", "verified_at", "verification_status", "source_id",
            "chunk_id", "version", "updated_at", "content_hash", "language", "retrieval_mode",
            "matched_language", "matched_chunk_id", "fallback_reason", "translation_review", "score")
    return {key: item[key] for key in keys if key in item}


def purchase_terms(language="ru"):
    by_id = {item["id"]: item for item in KB_ARTICLES}
    selected = [localize_article(by_id[key], language) for key in ("payment", "delivery", "minimum_order")]
    return {"articles": selected, "sources": [source_metadata(item) for item in selected],
            "payment": [selected[0]["content"]], "delivery": [selected[1]["content"]],
            "minimum_order": selected[2]["content"], "answer_language": selected[0]["language"]}


def retrieval_status():
    return get_index().status()
