import copy
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ekt_client import EktClient
from retrieval.catalog_index import CatalogIndex
from scripts.import_catalog import import_catalog


def product(identifier=1, current=16):
    return EktClient._normalise_detail({"id": identifier, "article": f"SKU-{identifier}",
        "name": f"Автомат {current}А 3P 400В", "price": 1234, "quantity": 99,
        "properties": {"NOMINALNYY_TOK": f"{current} А", "KOLICHESTVO_POLYUSOV": "3",
                       "NOMINALNOE_NAPRYAZHENIE": "400В", "CML2_BAR_CODE": "3414970344526"}})


class ImportClient:
    def __init__(self, pages):
        self.pages, self.last_error, self.calls, self.retry_after = pages, None, [], 0

    def get_page(self, page, force=False):
        self.calls.append(page)
        items = self.pages.get(page)
        if items is None:
            self.last_error = "upstream_unavailable"
            return None
        return {"items": copy.deepcopy(items)}


class CatalogIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index = CatalogIndex(Path(self.temp.name) / "catalog.sqlite3")

    def test_checkpoint_resume_deduplicate_and_only_empty_page_confirms_complete(self):
        client = ImportClient({1: [product(1), product(2)], 2: [product(2), product(3)], 3: []})
        first = import_catalog(client, self.index, max_pages=1, delay=0, sleep=lambda _: None)
        self.assertFalse(first["complete_catalog"])
        self.assertEqual(first["next_page"], 2)
        final = import_catalog(client, self.index, delay=0, sleep=lambda _: None)
        self.assertTrue(final["complete_catalog"])
        self.assertEqual(final["indexed_products"], 3)
        self.assertEqual(client.calls, [1,2,3])
        for item in self.index.products():
            self.assertIsNone(item["price"])
            self.assertIsNone(item["quantity"])
            self.assertFalse(item["stock_verified"])
            self.assertTrue(item["discovery_only"])

    def test_failed_page_keeps_checkpoint_and_does_not_claim_complete(self):
        result = import_catalog(ImportClient({1:[product()]}), self.index, sleep=lambda _: None)
        self.assertFalse(result["complete_catalog"])
        self.assertEqual(result["next_page"], 2)
        self.assertEqual(result["last_error"], "upstream_unavailable")

    def test_repeated_pages_stop_without_false_full_coverage(self):
        result = import_catalog(ImportClient({1:[product()], 2:[product()]}), self.index, sleep=lambda _: None)
        self.assertFalse(result["complete_catalog"])
        self.assertEqual(result["last_error"], "repeated_page")

    def test_restart_prunes_removed_products_only_after_success(self):
        import_catalog(ImportClient({1:[product(1),product(2)],2:[]}), self.index, sleep=lambda _: None)
        import_catalog(ImportClient({1:[product(1)]}), self.index, restart=True, sleep=lambda _: None)
        self.assertEqual(len(self.index.products()), 2)
        result = import_catalog(ImportClient({2:[]}), self.index, sleep=lambda _: None)
        self.assertTrue(result["complete_catalog"])
        self.assertEqual([p["id"] for p in self.index.products()], [1])

    def test_rate_limit_retries_are_bounded(self):
        class RateLimited(ImportClient):
            def get_page(self, page, force=False):
                self.calls.append(page)
                self.last_error = "upstream_http_429"
                self.retry_after = 999
                return None
        client, delays = RateLimited({}), []
        result = import_catalog(client, self.index, sleep=delays.append)
        self.assertEqual(len(client.calls), 4)
        self.assertTrue(all(0 < delay <= 30 for delay in delays))
        self.assertEqual(result["next_page"], 1)

    def test_index_search_barcode_aliases_and_technical_filters(self):
        import_catalog(ImportClient({1:[product(1),product(2,25)],2:[]}), self.index, sleep=lambda _: None)
        client = EktClient(requester=lambda *a,**k: self.fail("Unexpected network request"), catalog_index=self.index)
        client.auth = ("test", "test")
        for query in ("circuit breaker 16A 3P", "автоматты ажыратқыш 16A 3P", "circuit breaker 16 amps 3 poles 400 volts"):
            hits = client.search_products(query)
            self.assertEqual([item["id"] for item in hits], [1], query)
            self.assertFalse(hits[0]["price_verified"])
        self.assertEqual(client.search_products("barcode 3414970344526")[0]["_match_type"], "exact")
        self.assertEqual(client.search_products("breaker 99A"), [])
        self.assertTrue(client.coverage()["complete_catalog"])

    def test_unlabelled_quantity_never_becomes_product_id(self):
        import_catalog(ImportClient({1:[product(3,25),product(99,16)],2:[]}), self.index, sleep=lambda _: None)
        client = EktClient(requester=lambda *a,**k: self.fail("Unexpected request"), catalog_index=self.index)
        self.assertEqual([p["id"] for p in client.search_products("автомат 16A 3 полюса")], [99])

    def test_invalid_page_is_not_interpreted_as_catalog_end(self):
        client = EktClient(requester=lambda *a,**k:SimpleNamespace(status_code=200,json=lambda:{"items":[{"id":"invalid"}]}))
        client.auth = ("test", "test")
        result = import_catalog(client, self.index, sleep=lambda _: None)
        self.assertFalse(result["complete_catalog"])
        self.assertEqual(result["last_error"], "invalid_catalog_page")

    def test_deadline_blocks_network_and_propagates_to_catalog_workers(self):
        client = EktClient(requester=lambda *a,**k: self.fail("Deadline ignored"))
        client.auth = ("test", "test")
        with client.request_deadline(time.monotonic()-1):
            client.preload_catalog(2)
        self.assertEqual(client.last_error, "request_deadline_exceeded")

    def test_request_timeout_obeys_remaining_deadline(self):
        timeouts = []
        def request(*args, **kwargs):
            timeouts.append(kwargs["timeout"])
            return SimpleNamespace(status_code=200, json=lambda:{"items":[]})
        client = EktClient(requester=request)
        client.auth = ("test", "test")
        with client.request_deadline(time.monotonic()+.4):
            client.get_page(1)
        self.assertLess(sum(timeouts[0]), .41)


if __name__ == "__main__":
    unittest.main()
