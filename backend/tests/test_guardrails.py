import concurrent.futures
from urllib.parse import urlparse

from backend.tests.support import APIHarness
from cart_service import CartService
from settings import OFFER_TTL, SESSION_TTL


class CartGuardrailTests(APIHarness):
    def test_explicit_confirmation_and_single_use(self):
        offer = self.offer(quantity=2).json()
        for change in ({"confirmed": False}, {"offer_token": None}, {"quantity": 1}, {"product_id": 1003}):
            self.assertEqual(self.confirm(offer, **change).status_code, 409)
        self.assertEqual(self.cart()["total_items"], 0)
        added = self.confirm(offer)
        self.assertEqual(added.status_code, 200)
        self.assertIn("TEST-1001", added.json()["answer"])
        self.assertEqual(added.json()["cart_confirmation"]["quantity_added"], 2)
        self.assertEqual(self.confirm(offer).status_code, 409)
        self.assertEqual(self.cart()["total_items"], 2)

    def test_unknown_session_and_other_session_cannot_confirm(self):
        self.assertEqual(self.client.get("/api/cart").status_code, 401)
        self.assertEqual(self.client.get("/api/cart?session_id=" + "x" * 43).status_code, 401)
        offer = self.offer().json()
        other = self.client.post("/api/session").json()["session_id"]
        result = self.client.post("/api/cart/add", headers={"X-Session-Id": other}, json={
            "product_id": 1001, "quantity": 1, "confirmed": True, "offer_token": offer["offer_token"]})
        self.assertEqual(result.status_code, 409)
        self.assertEqual(self.client.get("/api/cart", headers={"X-Session-Id": other}).json()["total_items"], 0)

    def test_price_stock_and_cumulative_quantity(self):
        offer = self.offer(quantity=2).json()
        self.transport.products[1001]["price"] = 1100
        self.assertEqual(self.confirm(offer).json()["code"], "price_changed")
        offer = self.offer(quantity=2).json()
        self.transport.products[1001]["quantity"] = 1
        self.assertEqual(self.confirm(offer).json()["code"], "insufficient_stock")
        self.transport.products[1001]["quantity"] = 3
        self.assertEqual(self.confirm(offer).status_code, 200)
        self.assertEqual(self.offer(quantity=2).json()["code"], "insufficient_stock")
        self.assertEqual(self.cart()["total_items"], 2)

    def test_unavailable_catalog_cannot_use_cached_stock(self):
        offer = self.offer().json()
        self.transport.fail = True
        self.assertEqual(self.confirm(offer).status_code, 503)
        self.assertEqual(self.cart()["total_items"], 0)

    def test_expired_offer_and_session(self):
        offer = self.offer().json()
        self.clock.now += OFFER_TTL + 1
        self.assertEqual(self.confirm(offer).status_code, 409)
        self.clock.now += SESSION_TTL
        self.assertEqual(self.client.get("/api/cart", headers=self.headers).status_code, 401)

    def test_concurrent_replays_only_add_once(self):
        offer = self.offer(quantity=2).json()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: self.confirm(offer).status_code, range(5)))
        self.assertEqual(results.count(200), 1)
        self.assertEqual(self.cart()["total_items"], 2)

    def test_quantity_validation_and_packaging(self):
        for qty in (0, -1, 1.5, True, "2", 100001):
            self.assertEqual(self.offer(quantity=qty).status_code, 422)
        self.transport.products[1001]["properties"]["KRATNOST_MIN"] = "2"
        self.assertEqual(self.offer(quantity=1).json()["code"], "packaging_mismatch")
        self.assertEqual(self.offer(quantity=3).status_code, 409)
        self.assertEqual(self.offer(quantity=2).status_code, 200)

    def test_chat_confirmation_bound_to_offered_quantity(self):
        queried = self.chat("Артикул TEST-1001 2 шт.").json()
        self.assertEqual(queried["pending_offer"]["quantity"], 2)
        for message in ("Да, добавь 3 шт.", "Да, добавь 0 шт."):
            self.assertFalse(self.chat(message).json()["cart_updated"])
        accepted = self.chat("Да, добавь").json()
        self.assertTrue(accepted["cart_updated"])
        self.assertEqual(self.cart()["total_items"], 2)
        self.assertFalse(self.chat("Да, добавь").json()["cart_updated"])

    def test_negations_questions_quotes_are_not_consent(self):
        for message in ("не добавляй", "не подтверждаю", "если я скажу да добавь", "Да, добавь?", "«Да, добавь»"):
            self.chat("Артикул TEST-1001")
            self.assertFalse(self.chat(message).json()["cart_updated"], message)
            self.assertEqual(self.cart()["total_items"], 0)
            self.assertFalse(self.chat("Да, добавь").json()["cart_updated"])

    def test_tool_cannot_authorize_its_own_write(self):
        self.chat("Артикул TEST-1001")
        result = self.agent.execute_tool("add_to_cart_confirmed", {"product_id": 1001, "quantity": 1, "user_confirmed": True})
        self.assertEqual(result["error"], "tool_not_allowed")
        self.assertEqual(self.cart()["total_items"], 0)

    def test_persistence_current_read_link_and_csv(self):
        self.assertEqual(self.confirm(self.offer().json()).status_code, 200)
        url = self.cart()["checkout_url"]
        reopened = CartService(self.catalog, self.carts.db_path, self.clock)
        self.assertEqual(reopened.snapshot(self.sid)["total_items"], 1)
        self.confirm(self.offer().json())
        page = self.client.get(urlparse(url).path)
        self.assertEqual(page.status_code, 200)
        self.assertIn("TEST-1001", page.text)
        self.assertIn(">2</td>", page.text)
        self.assertEqual(page.headers["referrer-policy"], "no-referrer")
        exported = self.client.get("/api/cart/export", headers=self.headers)
        self.assertIn("TEST-1001", exported.text)
        self.assertEqual(self.cart()["handoff_status"], "not_configured")

    def test_read_link_expiry_and_html_escaping(self):
        self.transport.products[1001]["name"] = "<script>alert(1)</script>"
        self.confirm(self.offer().json())
        path = urlparse(self.cart()["checkout_url"]).path
        page = self.client.get(path).text
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.clock.now += OFFER_TTL + 1
        self.assertEqual(self.client.get(path).status_code, 404)
