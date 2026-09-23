import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from agent_service import agent_service
from ekt_client import ekt_client
from main import CART_OFFERS, CART_STORE, app


PRODUCT = {
    "id": 123,
    "name": "Автоматический выключатель 3P 160A",
    "article": "ABC-123",
    "price": 64920,
    "quantity": 3,
    "stock_verified": True,
    "image": None,
    "stores": [],
    "specifications": [],
    "data_quality_warnings": [],
}


class CartGuardrailTests(unittest.TestCase):
    def setUp(self):
        CART_STORE.clear()
        CART_OFFERS.clear()
        agent_service.pending_offers.clear()
        self.client = TestClient(app)
        self.detail_patch = patch.object(ekt_client, "get_product_detail", return_value=PRODUCT.copy())
        self.detail_patch.start()
        self.addCleanup(self.detail_patch.stop)

    def test_offer_is_bound_to_session_product_and_quantity_and_used_once(self):
        session = "?session_id=buyer-a"
        offer = self.client.post("/api/cart/offer" + session, json={"product_id": 123, "quantity": 2})
        self.assertEqual(offer.status_code, 200)
        token = offer.json()["offer_token"]

        base = {"product_id": 123, "quantity": 2, "confirmed": True, "offer_token": token}
        self.assertEqual(self.client.post("/api/cart/add?session_id=buyer-b", json=base).status_code, 409)
        self.assertEqual(self.client.post("/api/cart/add" + session, json={**base, "quantity": 1}).status_code, 409)
        self.assertEqual(self.client.post("/api/cart/add" + session, json={**base, "confirmed": False}).status_code, 409)
        self.assertEqual(self.client.get("/api/cart" + session).json()["total_items"], 0)

        added = self.client.post("/api/cart/add" + session, json=base)
        self.assertEqual(added.status_code, 200)
        self.assertEqual(added.json()["cart_confirmation"]["article"], PRODUCT["article"])
        self.assertEqual(added.json()["cart_confirmation"]["price"], PRODUCT["price"])
        self.assertEqual(self.client.get("/api/cart" + session).json()["total_items"], 2)
        self.assertEqual(self.client.post("/api/cart/add" + session, json=base).status_code, 409)
        self.assertEqual(
            self.client.post("/api/cart/offer" + session, json={"product_id": 123, "quantity": 2}).status_code,
            409,
        )

    def test_stock_is_rechecked_after_offer(self):
        session = "?session_id=buyer-stale"
        offer = self.client.post("/api/cart/offer" + session, json={"product_id": 123, "quantity": 2})
        self.assertEqual(offer.status_code, 200)
        with patch.object(ekt_client, "get_product_detail", return_value={**PRODUCT, "quantity": 1}):
            added = self.client.post("/api/cart/add" + session, json={
                "product_id": 123, "quantity": 2, "confirmed": True,
                "offer_token": offer.json()["offer_token"],
            })
        self.assertEqual(added.status_code, 409)
        self.assertEqual(self.client.get("/api/cart" + session).json()["total_items"], 0)

    def test_chat_confirmation_requires_matching_pending_offer(self):
        with patch.object(agent_service, "client", None), patch.object(
            ekt_client, "search_products", return_value=[{"id": 123, "name": PRODUCT["name"]}]
        ):
            session = "buyer-chat"
            query = self.client.post("/api/agent/chat", json={"message": "Артикул ABC-123", "session_id": session})
            self.assertEqual(query.status_code, 200)
            self.assertFalse(query.json()["cart_updated"])
            self.assertEqual(query.json()["sources"][0]["id"], 123)

            wrong_quantity = self.client.post("/api/agent/chat", json={"message": "Да, добавь 2 шт.", "session_id": session})
            self.assertFalse(wrong_quantity.json()["cart_updated"])
            self.assertEqual(self.client.get("/api/cart?session_id=" + session).json()["total_items"], 0)

            confirmed = self.client.post("/api/agent/chat", json={"message": "Да, добавь", "session_id": session})
            self.assertTrue(confirmed.json()["cart_updated"])
            self.assertIn(PRODUCT["article"], confirmed.json()["answer"])
            self.assertEqual(self.client.get("/api/cart?session_id=" + session).json()["total_items"], 1)

    def test_model_supplied_confirmed_flag_cannot_mutate_cart(self):
        agent_service.pending_offers["tool-session"] = {
            "product_id": 123, "quantity": 1, "created_at": time.time(),
        }
        result, mutation = agent_service.execute_tool(
            "add_to_cart_confirmed",
            {"product_id": 123, "quantity": 1, "user_confirmed": True},
            CART_STORE,
            "tool-session",
        )
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(mutation)
        self.assertNotIn("tool-session", CART_STORE)

    def test_upload_rejects_invalid_file_and_matches_quantity(self):
        unsupported = self.client.post("/api/agent/upload-spec", files={
            "file": ("spec.exe", b"payload", "application/octet-stream"),
        })
        self.assertEqual(unsupported.status_code, 415)
        empty = self.client.post("/api/agent/upload-spec", files={
            "file": ("spec.txt", b"", "text/plain"),
        })
        self.assertEqual(empty.status_code, 422)

        with patch.object(
            ekt_client, "search_products", return_value=[{"id": 123, "_match_type": "exact"}]
        ):
            response = self.client.post("/api/agent/upload-spec", files={
                "file": ("spec.txt", "Спецификация\nТовар ABC-123 2 шт.".encode(), "text/plain"),
            })
        self.assertEqual(response.status_code, 200)
        estimate = response.json()["estimate"]
        self.assertEqual(estimate["total_positions_found"], 1)
        self.assertEqual(estimate["matched_items"][0]["quantity"], 2)
        self.assertEqual(estimate["total_estimate_kzt"], 2 * PRODUCT["price"])


if __name__ == "__main__":
    unittest.main()
