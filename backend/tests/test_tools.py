from types import SimpleNamespace

from backend.tests.support import APIHarness
from fastapi.testclient import TestClient
from main import create_app


class ToolReply:
    def __init__(self, name=None, arguments="{}"):
        self.tool_calls = [SimpleNamespace(id="tool-1", function=SimpleNamespace(name=name, arguments=arguments))] if name else None

    def model_dump(self, **kwargs):
        return {"role": "assistant", "content": None, "tool_calls": [
            {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}}
            for call in self.tool_calls or []]}


class ToolsTests(APIHarness):
    def fake_client(self, replies):
        self.requests = []
        def create(**kwargs):
            self.requests.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=replies.pop(0))])
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    def test_function_call_loop_returns_facts_and_tool_outputs(self):
        self.agent.client = self.fake_client([ToolReply("search_products", '{"query":"TEST-1001"}'), ToolReply("get_product_detail", '{"product_id":1001}'), ToolReply()])
        reply = self.chat("Нужен TEST-1001").json()
        self.assertEqual(reply["agent_mode"], "tools")
        self.assertEqual(reply["sources"][0]["id"], 1001)
        self.assertTrue(any(m.get("role") == "tool" for m in self.requests[1]["messages"]))
        self.assertFalse(reply["cart_updated"])

    def test_unknown_mutation_tool_and_malformed_json_do_not_change_cart(self):
        self.agent.client = self.fake_client([ToolReply("add_to_cart_confirmed", '{"product_id":1001,"user_confirmed":true}'), ToolReply("get_product_detail", "bad-json"), ToolReply()])
        result = self.chat("Артикул TEST-1001").json()
        self.assertFalse(result["cart_updated"])
        self.assertEqual(self.cart()["total_items"], 0)

    def test_detail_selection_takes_priority_over_broad_search(self):
        self.agent.client = self.fake_client([ToolReply("search_products", '{"query":"Автомат"}'), ToolReply("get_product_detail", '{"product_id":1001}'), ToolReply()])
        result = self.chat("Подбери автомат").json()
        self.assertEqual([item["id"] for item in result["sources"]], [1001])
        self.assertEqual(result["pending_offer"]["product_id"], 1001)

    def test_llm_failure_falls_back_to_catalog_not_synthetic_stock(self):
        def fail(**kwargs):
            raise TimeoutError("simulated")
        self.agent.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
        reply = self.chat("TEST-1001").json()
        self.assertEqual(reply["sources"][0]["quantity"], 5)
        self.assertIn("llm_unavailable_rules_used", reply["warnings"])

    def test_rate_limit_applies_even_when_invalid_session_rotates_and_has_cors(self):
        client = TestClient(create_app(self.catalog, self.carts, self.agent, request_limit=2))
        self.addCleanup(client.close)
        for i in range(2):
            client.get("/api/cart?session_id=" + str(i) * 43)
        response = client.get("/api/cart?session_id=" + "z" * 43, headers={"Origin": "http://localhost:3000"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")
        self.assertIn("Retry-After", response.headers)
