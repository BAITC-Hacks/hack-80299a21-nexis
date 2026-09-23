"""Offline regressions for multilingual orchestration; no external model calls."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from backend.tests.support import APIHarness, product
from backend.tests.test_tools import ToolReply
from agent import composer, router
from agent.contracts import Evidence, RequestDeadline
from agent.tool_executor import ToolExecutor, compact_json


class AgentV3Tests(APIHarness):
    def direct(self, text, lang="ru", **kwargs):
        return self.agent.process_message(text, kwargs.get("history", []), self.sid, lang)

    def fake_client(self, replies):
        self.requests = []
        def create(**kwargs):
            self.requests.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=replies.pop(0))])
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    def test_educational_questions_never_enter_product_selection(self):
        for lang, query in (("ru", "Чем автомат отличается от УЗО?"), ("kk", "Автомат пен УЗО айырмашылығы қандай?"),
                            ("en", "What is the difference between a breaker and an RCD?")):
            response = self.direct(query, lang)
            self.assertEqual(response["answer_language"], lang)
            self.assertEqual(response["sources"], [])
            self.assertIsNone(response["pending_offer"])
            self.assertIsNone(response["clarification"])
            self.assertNotIn("catalog_match_unavailable", response["warning_codes"])
        self.assertEqual(self.transport.calls, [])

    def test_returning_cable_is_a_policy_question(self):
        for lang, query in (("ru", "Как вернуть кабель?"), ("kk", "Кабельді қалай қайтаруға болады?"), ("en", "How can I return a cable?")):
            response = self.direct(query, lang)
            self.assertTrue(response["knowledge_sources"])
            self.assertEqual(response["sources"], [])
            self.assertIsNone(response["clarification"])

    def test_quantity_is_not_electrical_rating(self):
        response = self.direct("Нужно 2 автомата")
        self.assertEqual(response["clarification"]["missing_fields"], ["current", "poles", "voltage"])
        self.assertEqual(self.transport.calls, [])

    def test_partial_parameters_accumulate_without_loose_selection(self):
        self.direct("Нужен автомат")
        self.assertIsNotNone(self.direct("16А")["clarification"])
        self.assertIsNotNone(self.direct("три полюса")["clarification"])
        response = self.direct("400В")
        self.assertEqual({item["id"] for item in response["sources"]}, {1001, 1002})

    def test_selected_parameters_can_be_corrected(self):
        self.direct("TEST-1001")
        response = self.direct("Нет, нужен 25А")
        self.assertEqual([item["id"] for item in response["sources"]], [1003])

    def test_ordinal_uses_last_displayed_candidates(self):
        self.direct("Сравни TEST-1001 и TEST-1003")
        response = self.direct("Второй, 2 шт")
        self.assertEqual(response["pending_offer"]["product_id"], 1003)
        self.assertEqual(response["pending_offer"]["quantity"], 2)
        self.assertEqual(self.cart()["total_items"], 0)

    def test_ordinal_outside_list_asks_for_selection(self):
        response = self.direct("The second one", "en")
        self.assertEqual(response["clarification"]["kind"], "product_selection")
        self.assertEqual(response["sources"], [])

    def test_language_switch_preserves_selection_and_quantity(self):
        self.direct("TEST-1001 3 шт")
        response = self.direct("Its specifications", "en")
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertIn("Voltage", response["answer"])
        self.assertEqual(self.agent.context.get(self.sid)["quantity"], 3)
        response = self.direct("Бес дана керек", "kk")
        self.assertEqual(response["pending_offer"]["quantity"], 5)
        self.assertTrue(self.direct("Иә, қос", "kk")["cart_updated"])

    def test_english_confirmation_requires_same_server_offer(self):
        response = self.direct("TEST-1001 two pieces", "en")
        self.assertEqual(response["pending_offer"]["quantity"], 2)
        self.assertFalse(self.direct("Yes, add?", "en")["cart_updated"])
        self.assertFalse(self.direct("Yes, add", "en")["cart_updated"])
        self.direct("TEST-1001 two pieces", "en")
        added = self.direct("Yes, add", "en")
        self.assertTrue(added["cart_updated"])
        self.assertIn("language=en", added["answer"])

    def test_city_aliases_and_budget_work_across_languages(self):
        self.direct("TEST-1001")
        response = self.direct("Is it available in Astana?", "en")
        self.assertEqual(response["sources"][0]["city_stock"]["stores"][0]["quantity"], 5)
        self.assertIsNone(response["pending_offer"])
        self.assertEqual(router.city("Қарағандыда бар ма?"), "караганда")
        self.assertEqual(router.budget("800 теңгеге дейін"), 800)

    def test_initial_budget_filters_returned_cards(self):
        self.transport.products[1001]["price"] = 700
        response = self.direct("автомат 16А 3P 400В до 800 тенге")
        self.assertEqual([item["id"] for item in response["sources"]], [1001])

    def test_new_family_clears_previous_city_and_selection(self):
        self.direct("TEST-1001")
        self.direct("В Астане?")
        response = self.direct("Подбери кабель")
        self.assertIsNotNone(response["clarification"])
        self.assertIsNone(self.agent.context.get(self.sid)["city"])
        self.assertIsNone(self.agent.context.get(self.sid)["product_id"])

    def test_barcode_does_not_trigger_payment_guard(self):
        self.transport.products[1001]["properties"]["CML2_BAR_CODE"] = "3414970344526"
        response = self.direct("Штрихкод 3414970344526")
        self.assertNotIn("платёжные", response["answer"])
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertTrue(router.sensitive("My card number is 4111 1111 1111 1111"))
        self.assertFalse(router.sensitive("EAN 3414970344526"))

    def test_tool_city_and_analog_outputs_are_retained(self):
        self.agent.client = self.fake_client([ToolReply("check_city_stock", '{"product_id":1001,"city":"Almaty"}'), ToolReply()])
        response = self.direct("TEST-1001")
        self.assertEqual(response["sources"][0]["city_stock"]["stores"], [])
        self.assertIsNone(response["pending_offer"])
        self.agent.client = self.fake_client([ToolReply("find_analogs", '{"product_id":1002}'), ToolReply()])
        response = self.direct("TEST-1002")
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertTrue(response["sources"][0]["matched_parameters"])

    def test_model_only_knowledge_tool_does_not_fall_through_product_not_found(self):
        self.agent.client = self.fake_client([ToolReply("query_knowledge_base", '{"topic":"payment"}'), ToolReply()])
        response = self.direct("Расскажи подробнее", "en")
        self.assertTrue(response["knowledge_sources"])
        self.assertEqual(response["sources"], [])
        self.assertNotIn("catalog_match_unavailable", response["warning_codes"])

    def test_unknown_model_prose_cannot_invent_commercial_facts(self):
        reply = ToolReply()
        reply.content = "There are 999 units in stock and delivery is free worldwide."
        self.agent.client = self.fake_client([reply])
        response = self.direct("Tell me something", "en")
        self.assertNotIn("999", response["answer"])
        self.assertNotIn("free worldwide", response["answer"])
        self.assertIn("knowledge_unavailable", response["warning_codes"])

    def test_grounded_model_extract_is_preserved_unsupported_sentence_dropped(self):
        source = {"language": "en", "content": "Delivery arrangements depend on the destination and order.", "source_url": "https://ekt.kz/checkout-delivery/"}
        prose = source["content"] + " There are 999 units in stock."
        result = composer.grounded_model_text(prose, [source], "en")
        self.assertEqual(result, source["content"])

    def test_timeout_is_remaining_budget_and_json_is_valid(self):
        self.agent.client = self.fake_client([ToolReply()])
        self.direct("TEST-1001")
        self.assertLessEqual(self.requests[0]["timeout"], self.agent.timeout)
        for payload in ({"data": "я" * 40000, "list": [{"content": "z" * 10000}] * 40}, [{"content": "z" * 10000}] * 40):
            encoded = compact_json(payload, 2000)
            self.assertLessEqual(len(encoded), 2000)
            json.loads(encoded)

    def test_multi_intent_question_includes_product_and_policy_sources(self):
        response = self.direct("TEST-1001 наличие и условия доставки")
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertTrue(response["knowledge_sources"])

    def test_metadata_contains_no_session_or_raw_prompt(self):
        response = self.direct("Привет")
        self.assertEqual(response["answer_language"], "ru")
        self.assertEqual(len(response["request_id"]), 32)
        self.assertNotIn(self.sid, json.dumps(response["diagnostics"]))
        self.assertNotIn("Привет", json.dumps(response["diagnostics"], ensure_ascii=False))

    def test_specs_question_does_not_prepare_cart_offer(self):
        response = self.direct("TEST-1001 specifications", "en")
        self.assertIsNone(response["pending_offer"])
        self.assertIn("Voltage", response["answer"])

    def test_later_model_failure_preserves_verified_results(self):
        replies = [ToolReply("get_product_detail", '{"product_id":1001}')]
        def create(**kwargs):
            if replies: return SimpleNamespace(choices=[SimpleNamespace(message=replies.pop())])
            raise TimeoutError("simulated late failure")
        self.agent.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        response = self.direct("TEST-1001", "en")
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertIn("llm_unavailable_rules_used", response["warning_codes"])
        self.assertIn("model is unavailable", response["warnings"][0])

    def test_rejected_tool_is_not_shown_as_success(self):
        self.agent.client = self.fake_client([ToolReply("add_to_cart", '{}'), ToolReply()])
        response = self.direct("TEST-1001", "en")
        rejected = next(step for step in response["reasoning_steps"] if step["tool_name"] == "add_to_cart")
        self.assertEqual(rejected["status"], "failed")
        self.assertIn("rejected", rejected["message"])
        self.assertEqual(self.cart()["total_items"], 0)

    def test_request_id_matches_caller_and_old_sensitive_history_is_filtered(self):
        response = self.agent.process_message("Hello", [{"role": "user", "content": "My card number is 4111 1111 1111 1111"}],
                                              self.sid, "en", request_id="known-http-id")
        self.assertEqual(response["request_id"], "known-http-id")
        self.assertIn("Hello", response["answer"])

    def test_deadline_in_alternatives_preserves_product_and_discloses_unfinished_check(self):
        with patch.object(self.catalog, "find_analogs", side_effect=TimeoutError("deadline")):
            response = self.direct("TEST-1002", "en")
        self.assertEqual(response["sources"][0]["id"], 1002)
        self.assertEqual(response["sources"][0]["analog_status"], "unavailable")
        self.assertIn("request_deadline", response["warning_codes"])
        self.assertIsNone(response["pending_offer"])

    def test_comparing_device_categories_is_explanatory(self):
        for lang, query in (("ru", "Сравни автомат и УЗО"), ("kk", "Автомат пен УЗО салыстыр"), ("en", "Compare MCB and RCD")):
            response = self.direct(query, lang)
            self.assertTrue(response["knowledge_sources"])
            self.assertEqual(response["sources"], [])
            self.assertIsNone(response["clarification"])

    def test_local_knowledge_does_not_need_a_model_call(self):
        def fail(**kwargs): raise AssertionError("Knowledge answer should use direct retrieval")
        self.agent.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
        response = self.direct("What file formats can I upload?", "en")
        self.assertTrue(response["knowledge_sources"])
        self.assertNotIn("llm_unavailable_rules_used", response["warning_codes"])

    def test_multi_intent_selection_and_delivery_both_answered(self):
        response = self.direct("Нужен автомат 16А 3P 400В и расскажи про доставку")
        self.assertEqual({p["id"] for p in response["sources"]}, {1001, 1002})
        self.assertTrue(any(p["id"] in {"delivery", "delivery_date", "shipping_cost"} for p in response["knowledge_sources"]))
        self.assertNotIn("breaker_selection", [p["id"] for p in response["knowledge_sources"]])

    def test_price_and_delivery_followup_retains_product(self):
        self.direct("TEST-1001")
        response = self.direct("Какая цена и доставка?")
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertIn("1,000.00", response["answer"])
        self.assertTrue(response["knowledge_sources"])

    def test_possessive_voltage_question_uses_product_fact(self):
        self.direct("TEST-1001", "en")
        response = self.direct("What is its voltage?", "en")
        self.assertEqual(response["sources"][0]["id"], 1001)
        self.assertIn("400", response["answer"])
        self.assertEqual(response["knowledge_sources"], [])

    def test_compare_selected_second_against_original_first(self):
        self.direct("Сравни TEST-1001 и TEST-1003")
        self.direct("Второй, 2 шт")
        response = self.direct("Сравни с первым")
        self.assertEqual([p["id"] for p in response["sources"]], [1003, 1001])
        self.assertIsNone(response["pending_offer"])
        self.assertEqual(self.agent.context.get(self.sid)["candidate_ids"], [1001, 1003])
        self.assertEqual(self.cart()["total_items"], 0)

    def test_budget_is_not_product_identifier_and_units_inflect(self):
        self.transport.products[1010] = product(1010, price=700)
        self.direct("TEST-1001")
        response = self.direct("до 10000 тенге")
        self.assertEqual([p["id"] for p in response["sources"]], [1010])
        response = self.direct("Нужно 3 штуки")
        self.assertEqual(response["pending_offer"]["quantity"], 3)

    def test_explicit_same_article_retains_city_and_quantity(self):
        self.direct("TEST-1001 3 шт")
        self.direct("В Астане?")
        response = self.direct("Сертификат TEST-1001")
        self.assertEqual(response["sources"][0]["city_stock"]["city"], "астана")
        self.assertEqual(self.agent.context.get(self.sid)["quantity"], 3)
        self.assertIsNone(response["pending_offer"])

    def test_model_analogs_are_grouped_and_checked_per_target(self):
        self.transport.products[1003]["quantity"] = 0
        self.transport.products[1010] = product(1010, current=25)
        self.agent.client = self.fake_client([
            ToolReply("get_product_detail", '{"product_id":1002}'),
            ToolReply("get_product_detail", '{"product_id":1003}'),
            SimpleNamespace(tool_calls=[
                SimpleNamespace(id="a", function=SimpleNamespace(name="find_analogs", arguments='{"product_id":1002}')),
                SimpleNamespace(id="b", function=SimpleNamespace(name="find_analogs", arguments='{"product_id":1003}')),
            ], content=None, model_dump=lambda **kwargs: {"role": "assistant", "content": None}),
        ])
        response = self.direct("Сравни TEST-1002 и TEST-1003")
        by_id = {p["id"]: [a["id"] for a in p["analogs"]] for p in response["sources"]}
        self.assertEqual(by_id, {1002: [1001], 1003: [1010]})

    def test_explicit_analog_request_does_not_offer_original_product(self):
        self.transport.products[1010] = product(1010, price=700)
        self.agent.client = self.fake_client([
            ToolReply("get_product_detail", '{"product_id":1001}'),
            ToolReply("find_analogs", '{"product_id":1001}'), ToolReply(),
        ])
        response = self.direct("Найди аналог TEST-1001")
        self.assertEqual([p["id"] for p in response["sources"]], [1010])
        self.assertEqual(response["pending_offer"]["product_id"], 1010)

    def test_comparison_matrix_preserves_unknown_and_highlights_actual_differences(self):
        self.transport.products[1003]["price"] = None
        response = self.direct("Compare TEST-1001 and TEST-1003", "en")
        matrix = response["comparison"]
        self.assertEqual([item["id"] for item in matrix["products"]], [1001, 1003])
        rows = {row["key"]: row for row in matrix["rows"]}
        self.assertEqual(rows["price"]["values"], ["1,000.00 ₸", None])
        self.assertFalse(rows["price"]["same"])
        self.assertEqual(rows["NOMINALNYY_TOK"]["values"], ["16 А", "25 А"])
        self.assertFalse(rows["NOMINALNYY_TOK"]["same"])
        self.assertIn("Differences and unknown fields", response["answer"])
        self.assertIsNone(response["pending_offer"])

    def test_explicit_numeric_comparison_resolves_each_product_id(self):
        for lang, query in (("en", "Compare products 1001 and 1003"), ("en", "Compare IDs 1001 and 1003"),
                            ("en", "Compare ID 1001 and ID 1003"), ("ru", "Сравни товары 1001 и 1003"),
                            ("kk", "1001 және 1003 тауарларын салыстыр")):
            response = self.direct(query, lang)
            self.assertEqual([p["id"] for p in response["sources"]], [1001, 1003], query)
            self.assertEqual([p["id"] for p in response["comparison"]["products"]], [1001, 1003], query)
            self.assertIsNone(response["pending_offer"])
            self.assertFalse(response["cart_updated"])

    def test_comparison_id_list_does_not_include_budget_or_electrical_ratings(self):
        self.assertEqual(router.comparison_product_ids("Compare products 1001 and 1003 with a budget of 10000"), [1001, 1003])
        for query in ("Compare breakers 16A and 25A", "Compare products 16A and 25A", "Compare articles 1001 and 1003", "Compare a budget of 10000 and 20000"):
            self.assertEqual(router.comparison_product_ids(query), [], query)

    def test_missing_comparison_id_is_disclosed_without_inventing_a_card(self):
        response = self.direct("Compare products 1001 and 999999", "en")
        self.assertEqual([p["id"] for p in response["sources"]], [1001])
        self.assertIsNone(response["comparison"])
        self.assertIsNone(response["pending_offer"])
        self.assertIn("999999 could not be verified", response["answer"])
        self.assertIn("catalog_match_unavailable", response["warning_codes"])

    def test_unavailable_numeric_comparison_never_falls_back_to_cached_search(self):
        self.catalog.get_product_detail(1001)
        self.catalog.get_product_detail(1003)
        self.transport.fail = True
        with patch.object(self.catalog, "search_products", side_effect=AssertionError("No search fallback after explicit ID failure")):
            response = self.direct("Compare products 1001 and 1003", "en")
        self.assertEqual(response["sources"], [])
        self.assertIsNone(response["comparison"])
        self.assertIsNone(response["pending_offer"])
