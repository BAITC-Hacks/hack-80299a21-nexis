from backend.tests.support import APIHarness, product
from dialogue_context import DialogueContext


class DialogueTests(APIHarness):
    def test_greeting_and_vague_requests_do_not_select_random_products(self):
        greeting = self.chat("Привет!").json()
        self.assertIn("Помогу", greeting["answer"])
        self.assertEqual(greeting["sources"], [])
        for message, expected in (("Нужен автомат", "номинальный ток"), ("Подбери кабель", "число жил")):
            response = self.chat(message).json()
            self.assertIn(expected, response["answer"])
            self.assertIsNone(response["pending_offer"])
            self.assertEqual(response["sources"], [])
        self.assertEqual(self.transport.calls, [])

    def test_clarification_uses_parameters_in_next_message(self):
        self.chat("Нужен автомат")
        response = self.chat("16А 3P 400В").json()
        self.assertEqual({item["id"] for item in response["sources"]}, {1001, 1002})
        self.assertFalse(response["cart_updated"])
        self.assertIsNone(response["pending_offer"])

    def test_quantity_followup_replaces_offer_but_does_not_confirm(self):
        old = self.chat("TEST-1001").json()["pending_offer"]
        response = self.chat("нужно пять").json()
        offer = response["pending_offer"]
        self.assertEqual(offer["product_id"], 1001)
        self.assertEqual(offer["quantity"], 5)
        self.assertNotEqual(offer["offer_token"], old["offer_token"])
        self.assertEqual(self.cart()["total_items"], 0)
        self.assertEqual(self.confirm(old).status_code, 409)
        self.assertTrue(self.chat("Да, добавь").json()["cart_updated"])
        self.assertEqual(self.cart()["total_items"], 5)

    def test_quantity_zero_and_excess_do_not_fall_back_to_one(self):
        self.chat("TEST-1001")
        for request in ("0 шт", "нужно шесть"):
            response = self.chat(request).json()
            self.assertIsNone(response["pending_offer"])
            self.assertFalse(response["cart_updated"])
        self.assertEqual(self.cart()["total_items"], 0)

    def test_negative_and_fractional_quantities_never_become_one(self):
        for request in ("TEST-1001 -3 шт", "TEST-1001 1.5 шт", "TEST-1001 1,5 шт", "TEST-1001 0 шт"):
            response = self.chat(request).json()
            self.assertIsNone(response["pending_offer"], request)
            self.assertFalse(response["cart_updated"])
            self.assertIn("invalid_quantity", response["warning_codes"])
        self.chat("TEST-1001")
        for request in ("нужно -3", "1.5 шт", "нужно 1,5"):
            response = self.chat(request).json()
            self.assertIsNone(response["pending_offer"], request)
            self.assertIn("invalid_quantity", response["warning_codes"])
        self.assertEqual(self.cart()["total_items"], 0)

    def test_city_followup_keeps_selection_and_never_uses_other_warehouse(self):
        self.chat("TEST-1001")
        response = self.chat("А в Алматы?").json()
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertEqual(response["sources"][0]["city_stock"]["stores"], [])
        self.assertIsNone(response["pending_offer"])
        self.assertFalse(self.chat("Да, добавь").json()["cart_updated"])
        response = self.chat("А в Астане?").json()
        self.assertEqual(response["sources"][0]["city_stock"]["stores"][0]["quantity"], 5)

    def test_city_and_quantity_persist_across_detail_followups(self):
        self.chat("TEST-1001")
        self.chat("3 шт")
        self.chat("А в Астане?")
        response = self.chat("Его характеристики").json()
        self.assertEqual(response["sources"][0]["city_stock"]["city"], "астана")
        self.assertEqual(self.agent.context.get(self.sid)["quantity"], 3)
        self.assertEqual(self.cart()["total_items"], 0)

    def test_cheaper_followup_requires_compatibility_stock_price_and_city(self):
        self.transport.products[1010] = product(1010, price=700, stores=[{"name": "Алматы", "quantity": 3}])
        self.transport.products[1011] = product(1011, current=25, price=500, stores=[{"name": "Алматы", "quantity": 5}])
        self.transport.products[1012] = product(1012, price=600)
        self.transport.products[1013] = product(1013, price=1100, stores=[{"name": "Алматы", "quantity": 3}])
        self.chat("TEST-1001")
        self.chat("А в Алматы?")
        response = self.chat("А подешевле? Бюджет 800 тенге").json()
        self.assertEqual([item["id"] for item in response["sources"]], [1010])
        self.assertTrue(response["sources"][0]["matched_parameters"])
        self.assertIn("Совпадающие параметры", response["answer"])
        self.assertFalse(response["cart_updated"])
        self.assertEqual(self.agent.context.get(self.sid)["budget"], 800)

    def test_cheaper_without_suitable_candidate_reports_no_match(self):
        self.chat("TEST-1001")
        response = self.chat("А подешевле?").json()
        self.assertIn("не найден", response["answer"])
        self.assertIn("cheaper_match_unavailable", response["warning_codes"])
        self.assertIsNone(response["pending_offer"])

    def test_cheaper_rejects_zero_or_unknown_prices_and_enforces_budget(self):
        self.transport.products[1010] = product(1010, price=0)
        self.transport.products[1011] = product(1011, price=None)
        self.transport.products[1012] = product(1012, price=700)
        self.chat("TEST-1001")
        response = self.chat("до 500 тенге").json()
        self.assertIn("cheaper_match_unavailable", response["warning_codes"])
        self.assertIsNone(response["pending_offer"])

    def test_cheaper_followup_creates_new_offer_with_preserved_quantity(self):
        self.transport.products[1010] = product(1010, price=700)
        self.chat("TEST-1001 3 шт")
        response = self.chat("А дешевле?").json()
        self.assertEqual(response["pending_offer"]["product_id"], 1010)
        self.assertEqual(response["pending_offer"]["quantity"], 3)
        self.assertEqual(self.cart()["total_items"], 0)

    def test_two_explicit_articles_are_compared_without_automatic_offer(self):
        response = self.chat("Сравни TEST-1001 и TEST-1003").json()
        self.assertEqual({item["id"] for item in response["sources"]}, {1001, 1003})
        self.assertIn("Сравнение найденных товаров", response["answer"])
        self.assertIsNone(response["pending_offer"])

    def test_context_is_ephemeral_bounded_and_isolated(self):
        self.chat("TEST-1001")
        second_session = self.carts.new_session()["session_id"]
        response = self.agent.process_message("А в Алматы?", [], second_session)
        self.assertEqual(response["sources"], [])
        self.clock.now += 1801
        response = self.chat("А в Алматы?").json()
        self.assertEqual(response["sources"], [])
        memory = DialogueContext(self.clock, ttl=10, capacity=2)
        for sid in ("a", "b", "c"):
            memory.update(sid, product_id=1001, unwanted_message="Never retain this")
        self.assertEqual(memory.get("a"), {})
        self.assertEqual(memory.get("b"), {"product_id": 1001})
        self.clock.now += 11
        self.assertEqual(memory.get("b"), {})

    def test_context_does_not_hide_upstream_failure(self):
        self.chat("TEST-1001")
        self.transport.fail = True
        response = self.chat("А в Алматы?").json()
        self.assertEqual(response["sources"], [])
        self.assertIsNone(response["pending_offer"])
        self.assertIn("недоступен", response["answer"])


class SearchImprovementTests(APIHarness):
    def test_labelled_id_in_sentence_resolves_outside_sample(self):
        self.catalog.preload_catalog()
        self.transport.products[999999] = product(999999)
        result = self.catalog.search_products("Покажи наличие товара с ID: 999999, пожалуйста")
        self.assertEqual([item["id"] for item in result], [999999])
        self.assertFalse(self.catalog.coverage()["complete_catalog"])

    def test_article_label_is_not_confused_with_internal_id(self):
        self.assertEqual(self.catalog.search_products("Артикул 1001"), [])
        self.transport.products[1003]["article"] = "1001"
        self.clock.now += self.catalog.catalog_ttl + 1
        self.assertEqual(self.catalog.search_products("Артикул 1001")[0]["id"], 1003)
        self.assertEqual(self.catalog.search_products("1001")[0]["id"], 1003)
        self.assertEqual(self.catalog.search_products("ID 1001")[0]["id"], 1001)

    def test_cable_dimensions_normalize_cyrillic_latin_and_decimal_comma(self):
        self.transport.products[2001] = product(2001, name="Кабель ВВГ 3х2,5", properties={"OBYEM": "Кабель"})
        self.transport.products[2002] = product(2002, name="Кабель ВВГ 3x1.5", properties={"OBYEM": "Кабель"})
        for request in ("кабель 3x2.5", "кабели 3×2,5", "кабель 3 х 2,5"):
            self.assertEqual([item["id"] for item in self.catalog.search_products(request)], [2001], request)

    def test_electrical_parameters_are_constraints_not_loose_word_matches(self):
        result = self.catalog.search_products("автоматический выключатель 16А 3P 400В")
        self.assertEqual({item["id"] for item in result}, {1001, 1002})
        result = self.catalog.search_products("автомат 25А 3P 400В")
        self.assertEqual([item["id"] for item in result], [1003])
