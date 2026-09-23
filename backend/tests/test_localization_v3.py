"""End-to-end language contract with synthetic catalog; no paid requests."""
import copy
from urllib.parse import urlsplit

from backend.tests.support import APIHarness
from localization import LANGUAGES, TEXT, localize_error, localize_product, normalize_language, tr


class LocalizationV3Tests(APIHarness):
    def test_language_helpers_are_complete_and_do_not_expose_unknown_errors(self):
        self.assertEqual(normalize_language("kz"), "kk")
        self.assertEqual(normalize_language("en-GB"), "en")
        for key, values in TEXT.items():
            with self.subTest(key=key):
                self.assertEqual(len(values), 3)
                self.assertTrue(all(values))
        self.assertEqual(localize_error("unknown", "en", "private internal data"), tr("unavailable", "en"))
        self.assertEqual(localize_error("unknown", "ru", "private internal data"), tr("unavailable", "ru"))

    def test_english_cart_confirmation_link_page_and_csv(self):
        headers = {**self.headers, "X-Language": "en"}
        offered = self.client.post("/api/cart/offer", headers=headers, json={"product_id": 1001, "quantity": 2}).json()
        self.assertEqual(offered["answer_language"], "en")
        result = self.client.post("/api/cart/add", headers=headers, json={
            "product_id": 1001, "quantity": 2, "confirmed": True, "offer_token": offered["offer_token"]}).json()
        self.assertIn("added to the demo cart", result["answer"])
        self.assertIn("1,000.00", result["answer"])
        self.assertIn("TEST-1001", result["answer"])
        self.assertIn("language=en", result["cart_url"])
        parts = urlsplit(result["cart_url"])
        page = self.client.get(parts.path + "?" + parts.query)
        self.assertIn('lang="en"', page.text)
        self.assertIn("no order has been placed", page.text)
        self.assertIn("TEST-1001", page.text)
        csv = self.client.get("/api/cart/export", headers=headers)
        self.assertIn("Product code,Name,Quantity,Price KZT,Amount KZT", csv.text)
        self.assertEqual(self.cart()["total_items"], 2)

    def test_kazakh_removal_survives_catalog_outage_and_still_needs_consent(self):
        self.confirm(self.offer().json())
        headers = {**self.headers, "X-Language": "kk"}
        self.transport.fail = True
        offer = self.client.post("/api/cart/change-offer", headers=headers,
                                 json={"product_id": 1001, "quantity": 0}).json()
        payload = {"product_id": 1001, "quantity": 0, "offer_token": offer["offer_token"], "confirmed": False}
        denied = self.client.post("/api/cart/change", headers=headers, json=payload)
        self.assertEqual(denied.status_code, 409)
        self.assertIn("растау", denied.json()["detail"])
        self.assertEqual(self.cart()["total_items"], 1)
        done = self.client.post("/api/cart/change", headers=headers, json={**payload, "confirmed": True}).json()
        self.assertIn("жойылды", done["answer"])
        self.assertEqual(self.cart()["total_items"], 0)

    def test_stock_errors_preserve_numeric_parameters_in_every_language(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                error = self.client.post("/api/cart/offer", headers={**self.headers, "X-Language": language},
                                         json={"product_id": 1001, "quantity": 99})
                self.assertEqual(error.status_code, 409)
                self.assertEqual(error.json()["code"], "insufficient_stock")
                self.assertEqual(error.json()["params"], {"remaining": 5})
                self.assertIn("5", error.json()["detail"])
                self.assertEqual(error.json()["answer_language"], language)

    def test_validation_is_localized_and_never_echoes_submitted_values(self):
        response = self.client.post("/api/cart/add", headers={**self.headers, "X-Language": "en"},
                                    json={"product_id": 1001, "quantity": "PRIVATE-MARKER", "confirmed": True})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "validation_error")
        self.assertNotIn("PRIVATE-MARKER", response.text)
        self.assertIn("Check", response.json()["detail"])

    def test_language_query_takes_priority_and_cors_accepts_header(self):
        response = self.client.get("/api/cart?language=en", headers={**self.headers, "X-Language": "kk"})
        self.assertEqual(response.json()["answer_language"], "en")
        self.assertEqual(response.headers["content-language"], "en")
        self.assertEqual(len(response.headers["x-request-id"]), 32)
        preflight = self.client.options("/api/cart", headers={"Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "X-Session-Id,X-Language"})
        self.assertEqual(preflight.status_code, 200)

    def test_upload_localizes_status_summary_and_unmatched_rows(self):
        for language, header, status in (("ru", "Артикул;Количество", "В наличии"),
                                        ("kk", "Артикул;Саны", "Қоймада бар"),
                                        ("en", "Product code;Quantity", "In stock")):
            with self.subTest(language=language):
                data = (header + "\nTEST-1001;2\nUNKNOWN-999;3").encode()
                response = self.client.post("/api/agent/upload-spec", headers={"X-Language": language},
                                            files={"file": ("spec.txt", data, "text/plain")})
                self.assertEqual(response.status_code, 200, response.text)
                estimate = response.json()["estimate"]
                row = estimate["matched_items"][0]
                self.assertEqual(row["status"], status)
                self.assertEqual(row["status_code"], "in_stock")
                self.assertEqual(row["quantity"], 2)
                self.assertEqual(estimate["unmatched_items"][0]["status_code"], "ambiguous_match")
                self.assertEqual(estimate["answer_language"], language)
                self.assertEqual(self.cart()["total_items"], 0)

    def test_upload_error_and_missing_quantity_in_english(self):
        error = self.client.post("/api/agent/upload-spec?language=en", files={"file": ("empty.txt", b"")})
        self.assertEqual(error.json()["detail"], "The file is empty.")
        response = self.client.post("/api/agent/upload-spec?language=en", files={"file": ("spec.txt", b"TEST-1001")})
        item = response.json()["estimate"]["matched_items"][0]
        self.assertEqual(item["status_code"], "quantity_unknown")
        self.assertIn("positive whole", item["quantity_warning"])
        self.assertIsNone(item["quantity"])

    def test_product_localization_preserves_facts_and_is_idempotent(self):
        original = self.catalog.get_product_detail(1001)
        original["data_quality_warnings"] = ["Ток в названии (16 А) расходится со свойством каталога (25 А). Требуется уточнение."]
        frozen = copy.deepcopy(original)
        translated = localize_product(original, "en")
        self.assertEqual(original, frozen)
        for field in ("id", "article", "name", "price", "quantity", "certificate_url", "technical"):
            self.assertEqual(translated[field], original[field])
        self.assertIn("Rated current", [item["name"] for item in translated["specifications"]])
        self.assertIn("16 A", translated["data_quality_warnings"][0])
        self.assertEqual(localize_product(translated, "en"), translated)

    def test_manager_handoff_is_localized_and_does_not_claim_sending(self):
        result = self.client.post("/api/manager/escalate?language=en", json={"comment": "Help"}).json()
        self.assertIn("no message has been sent", result["message"])
        self.assertEqual(result["answer_language"], "en")

    def test_faq_and_terms_support_all_three_languages(self):
        for language, query, marker in (("ru", "оплата", "оплат"), ("kk", "төлем", "төле"), ("en", "payment", "pay")):
            with self.subTest(language=language):
                faq = self.client.get("/api/faq", params={"q": query, "language": language}).json()
                self.assertEqual(faq["answer_language"], language)
                self.assertTrue(faq["articles"])
                terms = self.client.get("/api/purchase-terms", params={"language": language}).json()
                self.assertIn(marker, " ".join(terms["payment"]).lower())

    def test_chat_body_language_overrides_header(self):
        response = self.client.post("/api/agent/chat", headers={"X-Language": "ru"},
                                    json={"message": "Hello", "session_id": self.sid, "language": "en"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer_language"], "en")
        self.assertEqual(response.headers["content-language"], "en")
        self.assertEqual(response.json()["request_id"], response.headers["x-request-id"])

    def test_invalid_chat_uses_body_language_without_header(self):
        response = self.client.post("/api/agent/chat", json={"message": "", "session_id": self.sid, "language": "en"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["answer_language"], "en")
        self.assertIn("Check", response.json()["detail"])

    def test_upload_exposes_packaging_and_translated_unit_without_changing_source(self):
        self.transport.products[1001]["properties"]["KRATNOST_MIN"] = "2"
        response = self.client.post("/api/agent/upload-spec?language=en", files={"file": ("spec.txt", b"TEST-1001 2 pcs")})
        row = response.json()["estimate"]["matched_items"][0]
        self.assertEqual(row["unit"], "шт.")
        self.assertEqual(row["unit_display"], "pcs")
        self.assertEqual(row["min_order_quantity"], 2)
        self.assertEqual(row["order_multiple"], 2)
        self.assertTrue(row["stores"])

    def test_button_selection_updates_dialogue_without_granting_chat_consent(self):
        self.chat("TEST-1001")
        response = self.offer(1003, 2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.agent.context.get(self.sid)["product_id"], 1003)
        self.assertEqual(self.cart()["total_items"], 0)
        # An offer shown in the button dialog is not a chat confirmation.
        self.assertFalse(self.chat("Да, добавь").json()["cart_updated"])
        followup = self.chat("А в Астане?").json()
        self.assertEqual(followup["sources"][0]["id"], 1003)

    def test_warning_codes_are_separate_from_display_text(self):
        result = self.chat("Product UNKNOWN-909090", language="en").json()
        self.assertIn("catalog_match_unavailable", result["warning_codes"])
        self.assertNotIn("catalog_match_unavailable", result["warnings"])
        self.assertTrue(all("_" not in warning for warning in result["warnings"]))
