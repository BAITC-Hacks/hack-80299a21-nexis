import copy
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retrieval.store import CORPUS_PATH, KnowledgeIndex, load_articles, request_deadline
from knowledge_base import localize_article, purchase_terms, source_metadata


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.corpus = Path(self.temp.name) / "articles.json"
        self.corpus.write_bytes(CORPUS_PATH.read_bytes())
        self.index = KnowledgeIndex(Path(self.temp.name) / "kb.sqlite3", self.corpus)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {"NEXIS_EMBEDDINGS_ENABLED": "false"}).start()

    def test_curated_corpus_has_three_languages_and_honest_provenance(self):
        articles = load_articles()
        self.assertGreaterEqual(len(articles), 50)
        for article in articles:
            self.assertEqual(set(article["translations"]), {"ru", "kk", "en"})
            self.assertTrue(article["source_url"])
            self.assertTrue(article["version"])
            if "requires" in article["verification_status"]:
                self.assertIsNone(article["verified_at"])
        self.assertEqual(localize_article(articles[0], "kz")["language"], "kk")

    def test_persistence_and_cross_language_lookup_without_embedding_calls(self):
        with patch("retrieval.store.embed", side_effect=AssertionError("Network forbidden")):
            status = self.index.build()
            self.assertEqual(status["chunks"], status["documents"] * 3)
            self.assertEqual(status["retrieval_mode"], "lexical")
            for language in ("ru", "kk", "en"):
                hit = self.index.search("Чем автомат отличается от УЗО?", language=language)[0]
                self.assertEqual(hit["id"], "mcb_rcd")
                self.assertEqual(hit["language"], language)
                self.assertIn(":" + language + ":", hit["chunk_id"])
                self.assertTrue(hit["content_hash"])
                self.assertIn("version", source_metadata(hit))
            reloaded = KnowledgeIndex(self.index.path, self.corpus)
            self.assertEqual(reloaded.search("refund return item", language="en")[0]["id"], "returns")

    def test_unknown_question_has_no_arbitrary_article(self):
        self.assertEqual(self.index.search("quantumfluff marsgobbledygook"), [])
        self.assertEqual(self.index.search(""), [])

    def test_device_definition_never_changes_the_requested_device(self):
        cases = [
            ("Что такое УЗО?", "ru", "rcd_definition"),
            ("УЗО деген не?", "kk", "rcd_definition"),
            ("ҚАҚ деген не?", "kk", "rcd_definition"),
            ("What is an RCCB?", "en", "rcd_definition"),
            ("Что представляет собой дифавтомат?", "ru", "rcbo"),
            ("Дифавтомат деген не?", "kk", "rcbo"),
            ("What is an RCBO?", "en", "rcbo"),
        ]
        for query, language, expected in cases:
            hit = self.index.search(query, language=language)[0]
            self.assertEqual(hit["id"], expected, query)
        self.assertEqual(self.index.search("Чем автомат отличается от УЗО?")[0]["id"], "mcb_rcd")

    def test_store_policy_outranks_product_mentions_and_keeps_specific_focus(self):
        cases = [
            ("Как вернуть кабель?", "returns"), ("Как оплатить автомат?", "payment"),
            ("How can I return a cable?", "returns"),
            ("Кабельді қалай қайтаруға болады?", "returns"),
            ("Сколько стоит доставка?", "shipping_cost"),
            ("Can you deliver today?", "delivery_date"),
            ("How do you ship items to another city?", "delivery"),
        ]
        for query, expected in cases:
            self.assertEqual(self.index.search(query)[0]["id"], expected, query)

    def test_independent_retrieval_regression_set(self):
        from backend.evals.retrieval import run
        report = run()
        self.assertEqual(report["model_calls"], 0)
        for language in ("ru", "kk", "en"):
            self.assertEqual(report["summary"][language]["total"], 10)
            self.assertEqual(report["summary"][language]["top1_accuracy"], 1)
            self.assertEqual(report["summary"][language]["recall_at_5"], 1)

    def test_source_change_invalidates_chunks_and_removed_documents(self):
        self.index.build()
        before = self.index.search("barcode")[0]
        data = json.loads(self.corpus.read_text(encoding="utf-8"))
        data["articles"] = [item for item in data["articles"] if item["id"] != "mcb_rcd"]
        item = next(item for item in data["articles"] if item["id"] == "search_barcode")
        item["translations"]["ru"]["content"] += " Уточнение версии."
        item["version"] = "2"
        self.corpus.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        after = self.index.search("barcode")[0]
        self.assertNotEqual(before["content_hash"], after["content_hash"])
        self.assertEqual(after["version"], "2")
        with self.index.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM knowledge_chunks WHERE article_id='mcb_rcd'").fetchone()[0], 0)

    def test_embedding_reuse_and_failed_build_preserves_previous_generation(self):
        calls = []
        def embedding(texts, model):
            calls.extend(texts)
            return [[1.0, .1, .2] for _ in texts]
        first = self.index.build(True, embedding)
        self.assertEqual(first["embedded_chunks"], first["chunks"])
        count = len(calls)
        self.index.build(True, embedding)
        self.assertEqual(len(calls), count)
        data = json.loads(self.corpus.read_text(encoding="utf-8"))
        data["articles"][0]["version"] = "2"
        self.corpus.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        def failed(texts, model):
            raise RuntimeError("upstream")
        with self.assertRaises(RuntimeError):
            self.index.build(True, failed)
        self.assertEqual(self.index.status()["corpus_hash"], first["corpus_hash"])

    def test_hybrid_query_and_explicit_fallback(self):
        embedding = lambda texts, model: [[1.0, .1] for _ in texts]
        self.index.build(True, embedding)
        with patch.dict(os.environ, {"NEXIS_EMBEDDINGS_ENABLED": "true"}):
            hit = self.index.search("delivery", embedder=embedding)[0]
            self.assertEqual(hit["retrieval_mode"], "hybrid")
            def failed(texts, model):
                raise RuntimeError("upstream")
            hit = self.index.search("delivery", embedder=failed)[0]
            self.assertEqual(hit["retrieval_mode"], "lexical")
            self.assertEqual(hit["fallback_reason"], "embedding_query_failed")

    def test_purchase_terms_are_localized(self):
        for lang in ("ru", "kk", "en"):
            terms = purchase_terms(lang)
            self.assertEqual(terms["answer_language"], lang)
            self.assertTrue(terms["minimum_order"])
            self.assertEqual(len(terms["articles"]), 3)

    def test_long_article_preserves_matching_chunk_and_provenance(self):
        article = copy.deepcopy(load_articles()[0])
        article["keywords"] = []
        for lang in ("ru", "kk", "en"):
            article["translations"][lang]["content"] = " ".join(["filler"] * 350 + ["needleunique explanation"])
        self.corpus.write_text(json.dumps({"articles": [article]}), encoding="utf-8")
        for language in ("ru", "kk", "en"):
            hit = self.index.search("needleunique", language=language)[0]
            self.assertTrue(hit["chunk_id"].endswith(":1"))
            self.assertEqual(localize_article(hit, language)["content"], "needleunique explanation")
            self.assertNotIn("filler", hit["content"])

    def test_external_rebuild_invalidates_cached_embeddings(self):
        self.index.build()
        self.index.search("delivery")
        external = KnowledgeIndex(self.index.path, self.corpus)
        embedding = lambda texts, model: [[1.0, .2] for _ in texts]
        external.build(True, embedding)
        with patch.dict(os.environ, {"NEXIS_EMBEDDINGS_ENABLED": "true"}):
            self.assertEqual(self.index.search("delivery", embedder=embedding)[0]["retrieval_mode"], "hybrid")
            with request_deadline(time.monotonic()-1):
                hit = self.index.search("delivery", embedder=lambda *_: self.fail("Expired request used embedding"))[0]
                self.assertEqual(hit["retrieval_mode"], "lexical")
                self.assertEqual(hit["fallback_reason"], "embedding_query_failed")

    def test_status_reports_model_and_key_readiness(self):
        self.index.build(True, lambda texts, model:[[1.0, .2] for _ in texts], model="old-model")
        with patch.dict(os.environ, {"NEXIS_EMBEDDINGS_ENABLED":"true", "OPENAI_API_KEY":""}):
            status = self.index.status()
            self.assertEqual(status["retrieval_mode"], "lexical")
            self.assertEqual(status["fallback_reason"], "embedding_key_missing")
            self.assertEqual(status["active_model_chunks"], 0)


if __name__ == "__main__":
    unittest.main()
