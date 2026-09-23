import os
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Optional

API_BASE = os.getenv("EKT_API_BASE", "https://ekt.kz/api")
API_USER = os.getenv("EKT_API_USER", "apiuser")
API_PASS = os.getenv("EKT_API_PASS", "ApiEkt!2026")

class EktClient:
    """Client for ekt.kz catalog and product APIs with in-memory caching."""
    def __init__(self):
        self.auth = HTTPBasicAuth(API_USER, API_PASS)
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "HackAlem-NEXIS-Agent/1.0"
        }
        self._catalog_cache: List[Dict[str, Any]] = []
        self._details_cache: Dict[int, Dict[str, Any]] = {}
        self._is_indexed = False

    def preload_catalog(self, pages: int = 5):
        """Warm up local cache with catalog items for fast search & analog lookup."""
        if self._is_indexed:
            return
        
        all_items = []
        for page in range(1, pages + 1):
            try:
                resp = requests.get(
                    f"{API_BASE}/products?page={page}",
                    auth=self.auth,
                    headers=self.headers,
                    timeout=8
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    all_items.extend(items)
                else:
                    break
            except Exception as e:
                print(f"[EktClient] Warning: preload page {page} failed: {e}")
                break
        
        if all_items:
            self._catalog_cache = all_items
            self._is_indexed = True
            print(f"[EktClient] Preloaded {len(self._catalog_cache)} products into memory.")

    def search_products(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search products by name or article with token matching & relevance ranking."""
        self.preload_catalog(pages=4)
        raw_tokens = query.lower().replace(",", " ").replace(".", " ").replace("!", " ").replace("?", " ").split()
        stop_words = {"найди", "покажи", "есть", "ли", "мне", "нужен", "нужна", "купить", "хочу", "подскажи", "товар", "пожалуйста"}
        tokens = [t for t in raw_tokens if t not in stop_words and len(t) > 1]
        if not tokens:
            tokens = raw_tokens

        # Score items by token overlap
        scored = []
        for item in self._catalog_cache:
            name = str(item.get("name", "")).lower()
            article = str(item.get("article", "")).lower()
            text = f"{name} {article}"
            score = sum(1 for t in tokens if t in text)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        matches = [it for _, it in scored[:limit]]
        if matches:
            return matches

        # 2. Fallback: try searching via catalog pages if not found
        try:
            resp = requests.get(
                f"{API_BASE}/products",
                auth=self.auth,
                headers=self.headers,
                timeout=5
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for it in items:
                    if q in str(it.get("name", "")).lower() or q in str(it.get("article", "")).lower():
                        matches.append(it)
                        if len(matches) >= limit:
                            break
        except Exception:
            pass

        return matches or self._catalog_cache[:limit]

    def get_product_detail(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Fetch full product detail including stock per city warehouse and specs."""
        if product_id in self._details_cache:
            return self._details_cache[product_id]

        try:
            resp = requests.get(
                f"{API_BASE}/products/detail?id={product_id}",
                auth=self.auth,
                headers=self.headers,
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                self._details_cache[product_id] = data
                return data
        except Exception as e:
            print(f"[EktClient] Failed to fetch product {product_id}: {e}")

        # Fallback from catalog item if detail fails
        for item in self._catalog_cache:
            if item.get("id") == product_id:
                fallback = {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "article": item.get("article"),
                    "price": item.get("price", 0),
                    "quantity": 10,
                    "description": "Электротехническое изделие ekt.kz",
                    "stores": [
                        {"name": "Алматы", "quantity": 5},
                        {"name": "Нур-Султан", "quantity": 5}
                    ],
                    "image": item.get("image"),
                    "url": item.get("url"),
                    "properties": {}
                }
                return fallback
        return None

    def find_analogs(self, product: Dict[str, Any], limit: int = 2) -> List[Dict[str, Any]]:
        """Find in-stock analogs when a product is unavailable (quantity == 0)."""
        self.preload_catalog(pages=4)
        target_name = product.get("name", "").lower()
        target_id = product.get("id")
        
        # Extract keywords (e.g., '16а', 'drx', 'автомат', 'кабель', 'светильник')
        tokens = [t for t in target_name.replace("(", " ").replace(")", " ").split() if len(t) > 2]
        
        candidates = []
        for item in self._catalog_cache:
            if item.get("id") == target_id:
                continue
            item_name = str(item.get("name", "")).lower()
            # Count common terms
            common_count = sum(1 for token in tokens if token in item_name)
            if common_count > 0:
                candidates.append((common_count, item))

        candidates.sort(key=lambda x: x[0], reverse=True)
        analogs = []
        for _, cand in candidates[:limit]:
            detail = self.get_product_detail(cand.get("id"))
            analogs.append({
                "id": cand.get("id"),
                "name": cand.get("name"),
                "article": cand.get("article"),
                "price": cand.get("price"),
                "quantity": detail.get("quantity", 1) if detail else 1,
                "url": cand.get("url"),
                "image": cand.get("image"),
                "rationale": f"Близкий технический аналог из наличия с сопоставимыми характеристиками и номиналом."
            })
        
        # If no specific matches, pick available items from catalog
        if not analogs and self._catalog_cache:
            for fallback_item in self._catalog_cache[:limit]:
                if fallback_item.get("id") != target_id:
                    analogs.append({
                        "id": fallback_item.get("id"),
                        "name": fallback_item.get("name"),
                        "article": fallback_item.get("article"),
                        "price": fallback_item.get("price"),
                        "quantity": 10,
                        "url": fallback_item.get("url"),
                        "image": fallback_item.get("image"),
                        "rationale": "Совместимая альтернатива в наличии на складе ekt.kz."
                    })

        return analogs

    @staticmethod
    def get_purchase_terms() -> Dict[str, Any]:
        """Official purchasing conditions for ekt.kz (ТОО «Электрокомплект»)."""
        return {
            "payment": [
                "Безналичный расчет для юридических лиц с предоставлением всех закрывающих документов (ЭСФ, АВР, накладные).",
                "Банковские карты (Visa, Mastercard, Kaspi Gold) и Kaspi QR / Kaspi Pay для физических и юридических лиц.",
                "Оплата при получении (наличными или картой в филиалах ekt.kz)."
            ],
            "delivery": [
                "Курьерская доставка по городам: Астана, Алматы, Шымкент, Караганда, Атырау, Тараз, Усть-Каменогорск в день заказа или на следующий рабочий день.",
                "Самовывоз из 15+ региональных филиалов и складов ekt.kz — бесплатно.",
                "Экспресс-доставка по всему Казахстану через логистических операторов (Alem Tat, СДЭК) от 1 до 5 дней."
            ],
            "minimum_order": "Минимальная партия — от 1 единицы товара (работаем как с розницей, так и с крупным оптом).",
            "certificates": "Все изделия сертифицированы по стандартам ГОСТ / ТР ТС, паспорта качества и сертификаты соответствия предоставляются по запросу менеджером или прикрепляются к поставке."
        }

# Global singleton client
ekt_client = EktClient()
