import copy
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from agent_service import AgentService
from cart_service import CartService
from ekt_client import EktClient
from main import create_app


def product(pid=1001, stock=5, current=16, voltage=400, poles=3, **extra):
    return {"id": pid, "article": f"TEST-{pid}", "name": f"Автомат TEST-{pid} {current}А {poles}P {voltage}В C16",
            "price": 1000, "quantity": stock, "unit": "шт.", "url": f"https://ekt.kz/catalog/test-{pid}/",
            "certificate_url": "https://ekt.kz/test-certificate.pdf",
            "stores": [{"id": 1, "name": "Нур-Султан", "quantity": stock}],
            "properties": {"OBYEM": "Автоматический выключатель", "NOMINALNYY_TOK": f"{current} А",
                           "NOMINALNOE_NAPRYAZHENIE": f"{voltage}В", "KOLICHESTVO_POLYUSOV": str(poles),
                           "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST": "6кА", "KRATNOST_MIN": "1",
                           "KHARAKTERISTIKA_SRABATYVANIYA": "C"}, **extra}


class Clock:
    def __init__(self):
        self.now = 1800000000.0

    def __call__(self):
        return self.now


class Transport:
    def __init__(self):
        self.products = {p["id"]: p for p in [product(), product(1002, stock=0), product(1003, current=25),
                                              product(1004, voltage=230), product(1005, poles=2)]}
        self.calls = []
        self.fail = False

    def __call__(self, url, params, **kwargs):
        self.calls.append((url, dict(params)))
        if self.fail:
            return SimpleNamespace(status_code=503, json=lambda: {})
        if url.endswith("/products/detail"):
            value = self.products.get(params["id"])
            return SimpleNamespace(status_code=200 if value else 404, json=lambda: copy.deepcopy(value))
        items = list(self.products.values()) if params["page"] == 1 else []
        return SimpleNamespace(status_code=200, json=lambda: {"page": params["page"], "per_page": 20, "count": len(items), "items": copy.deepcopy(items)})


class APIHarness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock = Clock()
        self.transport = Transport()
        self.catalog = EktClient(self.transport, self.clock)
        self.catalog.auth = ("synthetic-user", "synthetic-password")
        self.catalog.search_pages = 1
        self.carts = CartService(self.catalog, os.path.join(self.temp.name, "cart.sqlite3"), self.clock)
        self.agent = AgentService(self.catalog, self.carts)
        self.agent.client = None
        self.app = create_app(self.catalog, self.carts, self.agent, request_limit=10000)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.sid = self.client.post("/api/session").json()["session_id"]
        self.headers = {"X-Session-Id": self.sid}

    def chat(self, message, **values):
        return self.client.post("/api/agent/chat", json={"message": message, "session_id": self.sid, **values})

    def offer(self, pid=1001, quantity=1):
        return self.client.post("/api/cart/offer", headers=self.headers, json={"product_id": pid, "quantity": quantity})

    def confirm(self, offer, **changes):
        payload = {"product_id": offer["product_id"], "quantity": offer["quantity"], "offer_token": offer["offer_token"], "confirmed": True}
        return self.client.post("/api/cart/add", headers=self.headers, json={**payload, **changes})

    def cart(self):
        return self.client.get("/api/cart", headers=self.headers).json()
