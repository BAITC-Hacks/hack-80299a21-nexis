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

    def test_products_catalog_endpoint(self):
        response = self.client.get("/api/products?page=1&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertGreaterEqual(data["total"], 1)
        self.assertLessEqual(len(data["items"]), 5)

    def test_faq_endpoint(self):
        response = self.client.get("/api/faq")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("categories", data)
        self.assertIn("articles", data)
        self.assertGreaterEqual(len(data["categories"]), 3)

    def test_purchase_terms(self):
        response = self.client.post("/api/agent/chat", json={
            "message": "Расскажите про условия доставки и оплаты в Астане"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Условия покупки", data["answer"])
        self.assertGreaterEqual(len(data["reasoning_steps"]), 1)

    def test_b2b_vat_rag_query(self):
        response = self.client.post("/api/agent/chat", json={
            "message": "Как получить счет на оплату с НДС для юрлица ТОО?"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("НДС 12%", data["answer"])
        self.assertIn("юридических лиц", data["answer"])

    def test_registration_guide_query(self):
        response = self.client.post("/api/agent/chat", json={
            "message": "Как зарегистрироваться в личном кабинете ekt.kz?"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("зарегистрироваться", data["answer"].lower())
        self.assertIn("БИН", data["answer"])

    def test_manager_escalation_endpoint(self):
        response = self.client.post("/api/manager/escalate", json={
            "client_name": "Айдар",
            "phone": "+7 777 999 88 77",
            "comment": "Заказ щитового оборудования на 15 млн тенге"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("TICK-EKT-", data["ticket_id"])
        self.assertIn("wa.me", data["manager_whatsapp_url"])

    def test_product_search_and_reasoning_steps(self):
        response = self.client.post("/api/agent/chat", json={
            "message": "Найди автоматический выключатель Legrand"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data["reasoning_steps"]), 2)
        answer_lower = data["answer"].lower()
        self.assertTrue("legrand" in answer_lower or "автомат" in answer_lower)

    def test_zero_stock_analog_suggestion(self):
        # Querying an item known or treated as out of stock
        response = self.client.post("/api/agent/chat", json={
            "message": "007886 диф автомат Legrand 16A"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data["reasoning_steps"]), 2)

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
