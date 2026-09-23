import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from main import app

class TestAgentAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["team"], "NEXIS")
        self.assertTrue(data["agent_ready"])

    def test_purchase_terms(self):
        response = self.client.post("/api/agent/chat", json={
            "message": "Расскажите про условия доставки и оплаты в Астане"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Условия покупки", data["answer"])
        self.assertGreaterEqual(len(data["reasoning_steps"]), 1)

    def test_product_search_and_reasoning_steps(self):
        response = self.client.post("/api/agent/chat", json={
            "message": "Найди автоматический выключатель Legrand"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data["reasoning_steps"]), 2)
        answer_lower = data["answer"].lower()
        self.assertTrue("legrand" in answer_lower or "автомат" in answer_lower)

    def test_guardrail_explicit_confirmation_adds_to_cart(self):
        # 1. User confirms addition
        response = self.client.post("/api/agent/chat", json={
            "message": "Да, добавь в корзину",
            "session_id": "test_session_guardrail"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["cart_updated"])
        self.assertGreaterEqual(data["cart_items_count"], 1)
        self.assertIsNotNone(data["cart_url"])

        # 2. Check cart state
        cart_resp = self.client.get("/api/cart?session_id=test_session_guardrail")
        self.assertEqual(cart_resp.status_code, 200)
        cart_data = cart_resp.json()
        self.assertGreaterEqual(cart_data["total_items"], 1)
        self.assertGreater(cart_data["total_sum"], 0)

if __name__ == "__main__":
    unittest.main()
