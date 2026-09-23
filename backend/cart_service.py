"""One confirmation policy for HTTP and chat; no partner order writes."""
import hashlib
import json
import math
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from settings import DB_PATH, OFFER_TTL, PUBLIC_URL, SESSION_TTL, ServiceError

LEGACY_SESSION = re.compile(r"ekt_web_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z", re.I)


class CartService:
    def __init__(self, catalog, db_path=DB_PATH, clock=time.time):
        self.catalog, self.db_path, self.clock = catalog, str(db_path), clock
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS cart_items (
                    session TEXT REFERENCES sessions(id) ON DELETE CASCADE,
                    product_id INTEGER, data TEXT NOT NULL, PRIMARY KEY(session, product_id));
                CREATE TABLE IF NOT EXISTS offers (
                    session TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
                    token TEXT NOT NULL, data TEXT NOT NULL, expires REAL NOT NULL, channel TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cart_links (
                    token TEXT PRIMARY KEY, session TEXT REFERENCES sessions(id) ON DELETE CASCADE,
                    expires REAL NOT NULL);
            """)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def new_session(self):
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE expires < ?", (self.clock(),))
            db.execute("INSERT INTO sessions VALUES (?,?)", (self.digest(token), self.clock() + SESSION_TTL))
        return {"session_id": token, "expires_in_seconds": SESSION_TTL}

    def session(self, token):
        if not isinstance(token, str) or not 36 <= len(token) <= 128:
            raise ServiceError("Создайте приватную сессию через POST /api/session.", "invalid_session", 401)
        key = self.digest(token)
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE expires < ?", (self.clock(),))
            db.execute("DELETE FROM offers WHERE expires < ?", (self.clock(),))
            db.execute("DELETE FROM cart_links WHERE expires < ?", (self.clock(),))
            row = db.execute("SELECT id FROM sessions WHERE id=?", (key,)).fetchone()
            if not row and LEGACY_SESSION.fullmatch(token):
                db.execute("INSERT INTO sessions VALUES (?,?)", (key, self.clock() + SESSION_TTL))
            elif not row:
                raise ServiceError("Сессия не найдена или истекла. Создайте новую сессию.", "invalid_session", 401)
        return key

    @staticmethod
    def _items(db, key):
        return [json.loads(row[0]) for row in db.execute("SELECT data FROM cart_items WHERE session=? ORDER BY product_id", (key,))]

    def _snapshot(self, key):
        with self.db() as db:
            items = self._items(db, key)
        return {"items": items, "total_positions": len(items),
                "total_items": sum(item["quantity"] for item in items),
                "total_sum": round(sum(item["price"] * item["quantity"] for item in items), 2),
                "cart_mode": "demo", "partner_cart_url": "https://ekt.kz/personal/cart/",
                "handoff_status": "not_configured", "stock_reserved": False}

    def snapshot(self, session_id):
        key = self.session(session_id)
        return {**self._snapshot(key), "checkout_url": self.view_url(session_id)}

    def view_url(self, session_id):
        key = self.session(session_id)
        token = secrets.token_urlsafe(24)
        with self.db() as db:
            db.execute("INSERT INTO cart_links VALUES (?,?,?)", (self.digest(token), key, self.clock() + OFFER_TTL))
        return f"{PUBLIC_URL}/cart/{token}"

    def read_link(self, token):
        with self.db() as db:
            row = db.execute("SELECT l.session FROM cart_links l JOIN sessions s ON s.id=l.session WHERE l.token=? AND l.expires>=? AND s.expires>=?", (self.digest(token), self.clock(), self.clock())).fetchone()
        if not row:
            raise ServiceError("Ссылка истекла. Получите новую ссылку в чате.", "expired_cart_link", 404)
        return self._snapshot(row[0])

    @staticmethod
    def _quantity(quantity):
        if type(quantity) is not int or not 1 <= quantity <= 100000:
            raise ServiceError("Количество должно быть целым положительным числом до 100000.", "invalid_quantity", 422)

    def _product(self, product_id):
        detail = self.catalog.get_product_detail(product_id, force_refresh=True)
        if not detail or detail.get("id") != product_id or not detail.get("stock_verified") or not detail.get("price_verified"):
            raise ServiceError("Не удалось проверить цену и остаток товара. Корзина не изменена.", "catalog_unavailable")
        if not isinstance(detail.get("price"), (int, float)) or not math.isfinite(detail["price"]) or detail["price"] <= 0:
            raise ServiceError("Цена требует уточнения у менеджера.", "price_unavailable")
        return detail

    @staticmethod
    def _check_stock(detail, quantity, existing_quantity):
        remaining = max(0, math.floor(detail["quantity"]) - existing_quantity)
        if quantity > remaining:
            raise ServiceError(f"Доступно для добавления не более {remaining} шт.", "insufficient_stock", 409, {"remaining": remaining})
        minimum = detail.get("min_order_quantity") or 1
        multiple = detail.get("order_multiple") or 1
        if quantity < minimum or (quantity / multiple) % 1 > 1e-8:
            raise ServiceError(f"Минимальная партия: {minimum}; кратность: {multiple}.", "packaging_mismatch", 409, {"minimum": minimum, "multiple": multiple})

    def prepare(self, session_id, product_id, quantity, channel="button"):
        key = self.session(session_id)
        self._quantity(quantity)
        detail = self._product(product_id)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = next((item for item in self._items(db, key) if item["product_id"] == product_id), {})
            self._check_stock(detail, quantity, existing.get("quantity", 0))
            token = secrets.token_urlsafe(24)
            offer = {"product_id": product_id, "product_name": detail["name"], "article": detail.get("article", ""),
                     "quantity": quantity, "price": detail["price"], "stock_available": detail["quantity"],
                     "operation": "add",
                     "cart_mode": "demo", "expires_in_seconds": OFFER_TTL,
                     "data_quality_warnings": detail.get("data_quality_warnings", [])}
            db.execute("INSERT OR REPLACE INTO offers VALUES (?,?,?,?,?)", (key, token, json.dumps(offer, ensure_ascii=False), self.clock() + OFFER_TTL, channel))
        return {**offer, "offer_token": token}

    def pending(self, session_id, channel="chat"):
        key = self.session(session_id)
        with self.db() as db:
            row = db.execute("SELECT * FROM offers WHERE session=? AND channel=? AND expires>=?", (key, channel, self.clock())).fetchone()
        return {**json.loads(row["data"]), "offer_token": row["token"]} if row else None

    def invalidate(self, session_id, channel="chat"):
        key = self.session(session_id)
        with self.db() as db:
            db.execute("DELETE FROM offers WHERE session=? AND channel=?", (key, channel))

    def _offer(self, db, key, token, product_id, quantity, operation="add"):
        row = db.execute("SELECT * FROM offers WHERE session=? AND expires>=?", (key, self.clock())).fetchone()
        if not row or not isinstance(token, str) or not secrets.compare_digest(row["token"], token):
            raise ServiceError("Подтверждение не найдено, использовано или истекло. Выберите товар заново.", "invalid_offer", 409)
        offer = json.loads(row["data"])
        if offer["product_id"] != product_id or offer["quantity"] != quantity or offer.get("operation", "add") != operation:
            raise ServiceError("Товар или количество отличаются от предложения.", "offer_mismatch", 409)
        return offer

    @staticmethod
    def _change_quantity(quantity):
        if type(quantity) is not int or not 0 <= quantity <= 100000:
            raise ServiceError("Укажите целое количество от 0 до 100000; 0 удаляет позицию.", "invalid_quantity", 422)

    def prepare_change(self, session_id, product_id, quantity):
        key = self.session(session_id)
        self._change_quantity(quantity)
        # Deleting a local item must remain possible during a partner API outage.
        detail = self._product(product_id) if quantity else None
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = next((item for item in self._items(db, key) if item["product_id"] == product_id), None)
            if not existing:
                raise ServiceError("Товара нет в корзине. Обновите её состояние.", "cart_item_not_found", 404)
            if quantity == existing["quantity"]:
                raise ServiceError("Это количество уже установлено.", "quantity_unchanged", 409)
            if detail:
                self._check_stock(detail, quantity, 0)
            source = detail or existing
            offer = {"product_id": product_id, "product_name": source["name"], "article": source.get("article", ""),
                     "quantity": quantity, "previous_quantity": existing["quantity"], "price": source["price"],
                     "stock_available": detail["quantity"] if detail else None, "operation": "set_quantity",
                     "cart_mode": "demo", "expires_in_seconds": OFFER_TTL,
                     "data_quality_warnings": source.get("data_quality_warnings", [])}
            token = secrets.token_urlsafe(24)
            db.execute("INSERT OR REPLACE INTO offers VALUES (?,?,?,?,?)", (key, token, json.dumps(offer, ensure_ascii=False), self.clock() + OFFER_TTL, "change"))
        return {**offer, "offer_token": token}

    def confirm_change(self, session_id, product_id, quantity, token, confirmed):
        key = self.session(session_id)
        self._change_quantity(quantity)
        if confirmed is not True:
            raise ServiceError("Подтвердите изменение корзины.", "confirmation_required", 409)
        with self.db() as db:
            self._offer(db, key, token, product_id, quantity, "set_quantity")
        detail = self._product(product_id) if quantity else None
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            offer = self._offer(db, key, token, product_id, quantity, "set_quantity")
            existing = next((item for item in self._items(db, key) if item["product_id"] == product_id), None)
            if not existing or existing["quantity"] != offer["previous_quantity"]:
                raise ServiceError("Корзина изменилась. Обновите её и подтвердите новое предложение.", "cart_changed", 409)
            if detail:
                if detail["price"] != offer["price"]:
                    raise ServiceError("Цена изменилась. Получите новое предложение и подтвердите его.", "price_changed", 409)
                self._check_stock(detail, quantity, 0)
                item = {**existing, "quantity": quantity, "price": detail["price"], "name": detail["name"],
                        "article": detail.get("article", ""), "unit": detail.get("unit", "шт."),
                        "image": detail.get("image"), "url": detail.get("url")}
                db.execute("UPDATE cart_items SET data=? WHERE session=? AND product_id=?", (json.dumps(item, ensure_ascii=False), key, product_id))
            else:
                db.execute("DELETE FROM cart_items WHERE session=? AND product_id=?", (key, product_id))
            db.execute("DELETE FROM offers WHERE session=?", (key,))
        cart = self.snapshot(session_id)
        answer = (f"Количество «{offer['product_name']}» изменено: {quantity}." if quantity
                  else f"«{offer['product_name']}» удалён из демонстрационной корзины.")
        answer += f"\n[Открыть актуальную корзину]({cart['checkout_url']})"
        summary = {"product_name": offer["product_name"], "article": offer["article"], "price": offer["price"],
                   "quantity": quantity, "quantity_added": quantity - offer["previous_quantity"], "operation": "set_quantity",
                   "stock_available": detail["quantity"] if detail else None,
                   "cart_items_count": cart["total_items"], "cart_url": cart["checkout_url"], "cart_mode": "demo"}
        return {"success": True, "answer": answer, "message": answer, "cart_confirmation": summary,
                "cart": cart["items"], "cart_url": cart["checkout_url"], "cart_mode": "demo"}

    def confirm(self, session_id, product_id, quantity, token, confirmed):
        key = self.session(session_id)
        self._quantity(quantity)
        if confirmed is not True:
            raise ServiceError("Требуется явное подтверждение добавления.", "confirmation_required", 409)
        with self.db() as db:
            self._offer(db, key, token, product_id, quantity)
        detail = self._product(product_id)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            offer = self._offer(db, key, token, product_id, quantity)
            if offer["price"] != detail["price"]:
                raise ServiceError("Цена изменилась. Получите новое предложение и подтвердите его.", "price_changed", 409)
            existing = next((item for item in self._items(db, key) if item["product_id"] == product_id), {})
            current_quantity = existing.get("quantity", 0)
            self._check_stock(detail, quantity, current_quantity)
            item = {"product_id": product_id, "name": detail["name"], "article": detail.get("article", ""),
                    "price": detail["price"], "quantity": current_quantity + quantity,
                    "unit": detail.get("unit", "шт."), "image": detail.get("image"), "url": detail.get("url")}
            db.execute("INSERT OR REPLACE INTO cart_items VALUES (?,?,?)", (key, product_id, json.dumps(item, ensure_ascii=False)))
            db.execute("DELETE FROM offers WHERE session=?", (key,))
        cart = self.snapshot(session_id)
        summary = {"product_name": item["name"], "article": item["article"], "price": item["price"],
                   "quantity_added": quantity, "stock_available": detail["quantity"],
                   "cart_items_count": cart["total_items"], "cart_url": cart["checkout_url"], "cart_mode": "demo"}
        answer = (f"✅ Товар добавлен в демонстрационную корзину.\n\n📦 {item['name']}\n"
                  f"🔢 Артикул: {item['article']}\n💰 Цена: {item['price']:,.2f} ₸\n"
                  f"📊 Добавлено: {quantity} {item['unit']} · Проверенный остаток: {detail['quantity']}\n"
                  f"🛒 В корзине: {cart['total_items']} ед.\n🔗 [Открыть актуальную корзину]({cart['checkout_url']})")
        return {"success": True, "answer": answer, "message": answer, "cart_confirmation": summary,
                "cart": cart["items"], "cart_url": cart["checkout_url"], "cart_mode": "demo", "product": detail}
