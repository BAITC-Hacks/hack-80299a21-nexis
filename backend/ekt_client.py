import os
import re
from datetime import datetime, timezone
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("EKT_API_BASE", "https://ekt.kz/api")
API_USER = os.getenv("EKT_API_USER", "")
API_PASS = os.getenv("EKT_API_PASS", "")

class EktClient:
    """Client for ekt.kz catalog and product APIs with in-memory caching."""
    def __init__(self):
        self.auth = HTTPBasicAuth(API_USER, API_PASS) if API_USER and API_PASS else None
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "HackAlem-NEXIS-Agent/1.0"
        }
        self._catalog_cache: List[Dict[str, Any]] = []
        self._details_cache: Dict[int, Dict[str, Any]] = {}
        self._loaded_pages = 0
        self._is_indexed = False

    def preload_catalog(self, pages: int = 5, force: bool = False):
        """Warm up local cache with catalog items for fast search & analog lookup."""
        if self._loaded_pages >= pages and not force:
            return
        if not self.auth:
            return
        
        all_items = []
        start_page = 1 if force else self._loaded_pages + 1
        for page in range(start_page, pages + 1):
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
                    if not isinstance(items, list):
                        break
                    all_items.extend(items)
                    per_page = int(data.get("per_page", len(items)) or len(items))
                    if not items or (per_page and len(items) < per_page):
                        self._loaded_pages = page
                        break
                    self._loaded_pages = page
                else:
                    break
            except (requests.RequestException, ValueError, TypeError) as e:
                print(f"[EktClient] Warning: preload page {page} failed: {e}")
                break
        
        if all_items:
            merged = self._catalog_cache + all_items
            self._catalog_cache = list({item.get("id"): item for item in merged if item.get("id")}.values())
            self._is_indexed = True
            print(f"[EktClient] Preloaded {len(self._catalog_cache)} products into memory.")

    def search_products(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search catalog pages by exact article/id first and then token relevance."""
        self.preload_catalog(pages=4)
        query = str(query or "").strip().lower()
        if not query:
            return []
        query_compact = re.sub(r"[^\w]", "", query)
        raw_tokens = re.findall(r"[\w]+", query, flags=re.UNICODE)
        stop_words = {"найди", "покажи", "есть", "ли", "мне", "нужен", "нужна", "купить", "хочу", "подскажи", "товар", "пожалуйста", "проверь", "наличие"}
        tokens = [token for token in raw_tokens if token not in stop_words and len(token) > 1]
        if not tokens:
            tokens = raw_tokens

        # A pure numeric query is commonly an ekt product id or article.
        exact_matches = []
        for item in self._catalog_cache:
            article = str(item.get("article", "")).lower()
            item_id = str(item.get("id", ""))
            supplier_article = str((item.get("properties") or {}).get("ARTIKULPOSTAVSHCHIKA", "")).lower()
            identifiers = {re.sub(r"[^\w]", "", value) for value in (article, item_id, supplier_article)}
            if query_compact and query_compact in identifiers:
                exact_matches.append(dict(item, _match_score=100, _match_type="exact"))
        if exact_matches:
            return exact_matches[:limit]

        # Score items by token overlap
        scored = []
        for item in self._catalog_cache:
            name = str(item.get("name", "")).lower()
            article = str(item.get("article", "")).lower()
            properties = " ".join(str(value) for value in (item.get("properties") or {}).values()).lower()
            text = f"{name} {article} {properties}"
            score = sum(1 for token in tokens if token in text)
            if score > 0:
                scored.append((score, dict(item, _match_score=score, _match_type="text")))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        if not scored:
            return []
        # Do not return an unrelated first catalog page when no query tokens match.
        threshold = 1 if len(tokens) <= 2 else 2
        return [item for score, item in scored[:limit] if score >= threshold]

    def get_product_detail(self, product_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch full product detail including stock per city warehouse and specs."""
        if not force_refresh and product_id in self._details_cache:
            return self._details_cache[product_id]

        if not self.auth:
            return None
        try:
            resp = requests.get(
                f"{API_BASE}/products/detail?id={product_id}",
                auth=self.auth,
                headers=self.headers,
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                if not isinstance(data, dict) or data.get("id") is None:
                    return None
                data = self._normalise_detail(data)
                data["last_checked_at"] = datetime.now(timezone.utc).isoformat()
                self._details_cache[product_id] = data
                return data
        except Exception as e:
            print(f"[EktClient] Failed to fetch product {product_id}: {e}")

        return None

    @staticmethod
    def _normalise_detail(data: Dict[str, Any]) -> Dict[str, Any]:
        """Expose stable frontend fields while retaining the partner's original properties."""
        properties = data.get("properties") if isinstance(data.get("properties"), dict) else {}
        spec_keys = {
            "OBYEM": "Тип изделия",
            "KOLICHESTVO_POLYUSOV": "Количество полюсов",
            "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST": "Отключающая способность",
            "NOMINALNOE_NAPRYAZHENIE": "Номинальное напряжение",
            "NOMINALNYY_TOK": "Номинальный ток по свойству каталога",
            "TIP_USTANOVKI": "Тип установки",
            "TORGOVAYA_MARKA": "Торговая марка",
        }
        specifications = [
            {"name": label, "value": str(properties[key])}
            for key, label in spec_keys.items()
            if properties.get(key) not in (None, "", [])
        ]
        stores = data.get("stores") if isinstance(data.get("stores"), list) else []
        normalized_stores = [
            {"id": store.get("id"), "name": str(store.get("name", "")), "quantity": max(0, int(store.get("quantity", 0) or 0))}
            for store in stores if isinstance(store, dict)
        ]
        cert_url = data.get("certificate_url") or data.get("certificate_link")
        for key, value in properties.items():
            if "CERT" in str(key).upper() or "SERT" in str(key).upper():
                if isinstance(value, str) and value.startswith(("https://", "http://")):
                    cert_url = cert_url or value
        data = dict(data)
        data["stores"] = normalized_stores
        data["quantity"] = max(0, int(data.get("quantity", 0) or 0)) if data.get("quantity") is not None else None
        data["specifications"] = specifications
        data["certificate_url"] = cert_url
        data["stock_verified"] = "quantity" in data and data.get("quantity") is not None
        warnings = []
        name_current = EktClient._first_number(data.get("name") or "", r"(?:а|a)\b")
        property_current = EktClient._first_number(properties.get("NOMINALNYY_TOK"), r"(?:а|a)\b")
        if name_current is not None and property_current is not None and name_current != property_current:
            warnings.append(
                f"Номинальный ток расходится: в названии указано {name_current:g} А, "
                f"в свойстве каталога — {property_current:g} А. Нужна проверка карточки."
            )
        data["data_quality_warnings"] = warnings
        return data

    def find_analogs(self, product: Dict[str, Any], limit: int = 2) -> List[Dict[str, Any]]:
        """Find analogs with verified positive stock and explain matching properties."""
        self.preload_catalog(pages=4)
        if not self._catalog_cache:
            return []
        if product.get("data_quality_warnings"):
            return []
        target_name = str(product.get("name", "")).lower()
        target_id = product.get("id")
        target_props = product.get("properties") or {}
        target_category = str(target_props.get("OBYEM", "")).lower()
        target_tokens = set(re.findall(r"[\w]+", target_name))
        target_current = self._first_number(target_props.get("NOMINALNYY_TOK") or target_name, r"(?:а|a)\b")
        target_poles = self._first_number(target_props.get("KOLICHESTVO_POLYUSOV") or target_name, r"(?:полюс|p\b|ф\b)")
        candidates = []
        for item in self._catalog_cache:
            if item.get("id") == target_id:
                continue
            item_props = item.get("properties") or {}
            item_category = str(item_props.get("OBYEM", "")).lower()
            item_name = str(item.get("name", "")).lower()
            item_current = self._first_number(item_props.get("NOMINALNYY_TOK") or item_name, r"(?:а|a)\b")
            item_poles = self._first_number(item_props.get("KOLICHESTVO_POLYUSOV") or item_name, r"(?:полюс|p\b|ф\b)")
            score = 0
            rationale = []
            if target_category and target_category == item_category:
                score += 4
                rationale.append("тот же тип изделия")
            if target_current is not None and target_current == item_current:
                score += 4
                rationale.append(f"тот же номинальный ток {target_current} А")
            if target_poles is not None and target_poles == item_poles:
                score += 3
                rationale.append(f"то же число полюсов ({target_poles})")
            common = target_tokens.intersection(set(re.findall(r"[\w]+", item_name)))
            meaningful_common = common - {"автоматический", "выключатель", "автомат", "legrand", "iek"}
            score += min(len(meaningful_common), 3)
            if score >= 4:
                candidates.append((score, item, rationale))

        candidates.sort(key=lambda row: row[0], reverse=True)
        analogs = []
        for _, cand, rationale in candidates[:max(limit * 4, 6)]:
            detail = self.get_product_detail(cand.get("id"), force_refresh=True)
            if not detail or not detail.get("stock_verified") or int(detail.get("quantity") or 0) < 1:
                continue
            analogs.append({
                **detail,
                "rationale": "; ".join(rationale) if rationale else "Совпали ключевые слова в названии; характеристики нужно сверить перед покупкой.",
            })
            if len(analogs) >= limit:
                break
        return analogs

    @staticmethod
    def _first_number(value: Any, suffix_pattern: str) -> Optional[float]:
        if value is None:
            return None
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*" + suffix_pattern, str(value).lower())
        return float(match.group(1).replace(",", ".")) if match else None

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
