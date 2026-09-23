"""Explicit opt-in smoke check: EKT GET requests and an isolated local demo cart."""
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from agent_service import AgentService
from cart_service import CartService
from ekt_client import EktClient
from main import create_app


def run():
    started = time.perf_counter()
    catalog = EktClient()
    page = catalog.get_page(2, force=True)
    detail = catalog.get_product_detail(515291, force_refresh=True)
    assert page and page["items"], "EKT page 2 unavailable"
    assert detail and detail["id"] == 515291, "EKT detail unavailable"
    assert detail["stock_verified"] and detail["price_verified"], "EKT facts missing"
    with tempfile.TemporaryDirectory() as directory:
        carts = CartService(catalog, Path(directory) / "smoke.sqlite3")
        agent = AgentService(catalog, carts)
        agent.client = None
        with TestClient(create_app(catalog, carts, agent)) as client:
            sid = client.post("/api/session").json()["session_id"]
            headers = {"X-Session-Id": sid}
            response = client.post("/api/agent/chat", json={"session_id": sid, "message": "515291"})
            assert response.status_code == 200, response.status_code
            assert response.json()["sources"][0]["id"] == 515291
            offer_response = client.post("/api/cart/offer", headers=headers, json={"product_id": 515291, "quantity": 1})
            cart_added = False
            if detail["quantity"] >= 1:
                assert offer_response.status_code == 200, offer_response.text
                offer = offer_response.json()
                payload = {"product_id": 515291, "quantity": 1, "confirmed": True, "offer_token": offer["offer_token"]}
                result = client.post("/api/cart/add", headers=headers, json=payload)
                assert result.status_code == 200, result.text
                link = result.json()["cart_url"]
                view = client.get(urlparse(link).path)
                assert view.status_code == 200 and detail["article"] in view.text
                cart_added = True
            print(json.dumps({"ok": True, "product_id": detail["id"], "page_items": len(page["items"]),
                              "stock_verified": detail["stock_verified"], "price_verified": detail["price_verified"],
                              "warehouses": len(detail["stores"]), "data_quality_warnings": len(detail["data_quality_warnings"]),
                              "isolated_demo_cart_added": cart_added, "partner_writes": 0,
                              "elapsed_seconds": round(time.perf_counter() - started, 2)}, ensure_ascii=False))


if __name__ == "__main__":
    run()
