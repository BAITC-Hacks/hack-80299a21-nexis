"""Read-only EKT catalog integration. Missing facts remain unknown."""
import copy
import math
import os
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import RLock
from urllib.parse import urljoin, urlparse

import requests
from requests.auth import HTTPBasicAuth

from settings import env_int
from retrieval.catalog_index import CatalogIndex

_deadline = ContextVar("catalog_request_deadline", default=None)


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(str(value).replace(",", ".").replace("\u00a0", "").strip())
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError):
        return None


def measure(value):
    matches = re.findall(r"\d+(?:[.,]\d+)?", str(value or ""))
    return number(matches[0]) if len(matches) == 1 else None


def rating(value, kind):
    """Normalize A/V/kA/mA; ambiguous ranges cannot establish compatibility."""
    result = measure(value)
    if result is None:
        return None
    units = re.sub(r"[\d\s.,]", "", str(value).lower()).translate(str.maketrans({"а": "a", "в": "v", "к": "k", "м": "m"}))
    units = units.replace("ac", "").replace("dc", "")
    factors = {"current": {"": 1, "a": 1, "ka": 1000, "ma": .001},
               "voltage": {"": 1, "v": 1, "kv": 1000},
               "capacity": {"": 1, "ka": 1, "a": .001},
               "leakage": {"": 1, "ma": 1, "a": 1000}}
    factor = factors[kind].get(units)
    return result * factor if factor is not None else None


def utc(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def safe_url(value):
    if not isinstance(value, str) or not value.strip():
        return None
    url = urljoin("https://ekt.kz/", value.strip())
    parsed = urlparse(url)
    return url if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username else None


SPEC_NAMES = {
    "OBYEM": "Тип изделия", "KOLICHESTVO_POLYUSOV": "Число полюсов",
    "NOMINALNYY_TOK": "Номинальный ток", "NOMINALNOE_NAPRYAZHENIE": "Напряжение",
    "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST": "Отключающая способность",
    "TIP_USTANOVKI": "Монтаж", "TORGOVAYA_MARKA": "Марка",
    "SECHENIE": "Сечение", "KOLICHESTVO_ZHIL": "Число жил",
    "KHARAKTERISTIKA_SRABATYVANIYA": "Характеристика срабатывания",
    "NOMINALNYY_OTKLYUCHAYUSHCHIY_DIFFERENTSIALNYY_TOK": "Дифференциальный ток",
}


class EktClient:
    def __init__(self, requester=None, clock=time.time, catalog_index=None):
        self.base = os.getenv("EKT_API_BASE", "https://ekt.kz/api").rstrip("/")
        user, password = os.getenv("EKT_API_USER", ""), os.getenv("EKT_API_PASS", "")
        self.auth = HTTPBasicAuth(user, password) if user and password else None
        self.requester = requester or requests.get
        self.clock = clock
        self.catalog_ttl = env_int("EKT_CATALOG_TTL_SECONDS", 300)
        self.detail_ttl = env_int("EKT_DETAIL_TTL_SECONDS", 30)
        self.search_pages = env_int("EKT_CATALOG_PAGES", 4, 1, 50)
        self._pages, self._details = {}, {}
        self._lock = RLock()
        self.last_error = None
        self.retry_after = None
        # Fake clients do not accidentally consume an operator's live import.
        self.catalog_index = catalog_index if catalog_index is not None else (CatalogIndex() if requester is None else None)

    @staticmethod
    @contextmanager
    def request_deadline(deadline_monotonic):
        token = _deadline.set(deadline_monotonic)
        try:
            yield
        finally:
            _deadline.reset(token)

    @staticmethod
    def _parallel(function, values, max_workers=4):
        values = list(values)
        if not values:
            return []
        with ThreadPoolExecutor(max_workers=min(max_workers, len(values))) as pool:
            futures = [pool.submit(copy_context().run, function, value) for value in values]
            return [future.result() for future in futures]

    def _request(self, path, params):
        deadline = _deadline.get()
        remaining = deadline - time.monotonic() if deadline is not None else None
        if remaining is not None and remaining <= 0:
            self.last_error = "request_deadline_exceeded"
            return None
        if not self.auth:
            self.last_error = "credentials_missing"
            return None
        try:
            response = self.requester(
                f"{self.base}/{path}", params=params, auth=self.auth,
                headers={"Accept": "application/json", "User-Agent": "NEXIS/2.0"},
                timeout=(min(3, max(.01, remaining / 2)), min(6, max(.01, remaining / 2))) if remaining is not None else (3, 6),
                allow_redirects=False,
            )
            if response.status_code != 200:
                self.last_error = f"upstream_http_{response.status_code}"
                self.retry_after = number(getattr(response, "headers", {}).get("Retry-After"))
                return None
            data = response.json()
            self.last_error = None
            return data
        except (requests.RequestException, ValueError, TypeError):
            self.last_error = "upstream_unavailable"
            return None

    def get_page(self, page=1, force=False):
        with self._lock:
            cached = self._pages.get(page)
            if cached and not force and self.clock() - cached[0] < self.catalog_ttl:
                return copy.deepcopy(cached[1])
        data = self._request("products", {"page": page})
        if data is None:
            return None
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            self.last_error = "invalid_catalog_page"
            return None
        if any(not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] < 1 for item in data["items"]):
            self.last_error = "invalid_catalog_page"
            return None
        checked = self.clock()
        items = []
        for item in data["items"]:
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                item = self._normalise_detail(item)
                item.update(last_checked_at=utc(checked), expires_at=utc(checked + self.catalog_ttl), data_source="ekt.kz")
                items.append(item)
        result = {"page": page, "per_page": data.get("per_page", len(items)),
                  "count": len(items), "items": items, "last_checked_at": utc(checked)}
        with self._lock:
            self._pages[page] = (checked, result)
        return copy.deepcopy(result)

    def preload_catalog(self, pages=None, force=False):
        pages = min(pages or self.search_pages, 50)
        self._parallel(lambda page: self.get_page(page, force), range(1, pages + 1))

    @property
    def _catalog_cache(self):
        with self._lock:
            values = [item for checked, page in self._pages.values()
                      if self.clock() - checked < self.catalog_ttl for item in page["items"]]
        indexed = self.catalog_index.products() if self.catalog_index else []
        return list({item["id"]: copy.deepcopy(item) for item in indexed + values}.values())

    def coverage(self):
        indexed = self.catalog_index.coverage() if self.catalog_index else {"indexed_products": 0, "complete_catalog": False}
        return {**indexed, "loaded_products": len(self._catalog_cache), "search_pages": self.search_pages,
                "scope": "imported_catalog" if indexed["indexed_products"] else "representative_sample",
                "trade_facts_require_live_detail": True}

    @staticmethod
    def _key(text):
        return re.sub(r"[\W_]+", "", str(text).lower())

    @staticmethod
    def normalize_query(text):
        text = str(text).lower().replace("ё", "е").replace("×", "x")
        text = re.sub(r"(?<=\d)\s*[хx*]\s*(?=\d)", "x", text)
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:amps?|amperes?|ампер\w*)\b", r"\1a", text)
        text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:volts?|вольт\w*)\b", r"\1v", text)
        for pattern, replacement in ((r"\bавтоматическ\w*\s+выключател\w*", "автомат"),
                                     (r"\b(?:circuit\s+breakers?|mcbs?)\b", "автомат"),
                                     (r"\bавтомат(?:ты|тық)?\s+(?:ажыратқыш|сөндіргіш)\w*", "автомат"),
                                     (r"\b(?:cables?|wires?)\b", "кабель"),
                                     (r"\b(?:residual\s+current\s+(?:devices?|breakers?)|rccb|rcd)\b", "узо"),
                                     (r"\brcbo\b", "дифавтомат"),
                                     (r"\b(?:лампалар|lamps?|bulbs?)\b", "лампа"),
                                     (r"\bавтомат(?:ы|а|ов|ом)?\b", "автомат"),
                                     (r"\bкабел[ьяеи]\w*\b", "кабель"),
                                     (r"\bсветодиодн\w*", "led"),
                                     (r"\bлампочк\w*", "лампа")):
            text = re.sub(pattern, replacement, text)
        return text

    def search_products(self, query, limit=5):
        query = self.normalize_query(query or "").strip()
        if not query:
            return []
        # Explicit ID labels are unambiguous even in a natural-language sentence.
        # A labelled article must never be interpreted as a product ID.
        article_query = bool(re.search(r"\b(?:артикул\w*|sku|article|barcode|штрихкод\w*|ean|gtin)\b", query))
        direct = None if article_query else re.search(r"\b(?:id|идентификатор)(?:\s+товара)?\s*[:=#№]?\s*(\d{1,10})\b", query)
        if direct:
            detail = self.get_product_detail(int(direct[1]))
            return [{**detail, "_match_type": "exact", "_match_score": 100}] if detail else []
        if not self.catalog_index or not self.catalog_index.coverage()["indexed_products"]:
            self.preload_catalog()
        bare_number = re.fullmatch(r"\d{1,10}", query)
        query = re.sub(r"\b\d+\s*(?:шт\.?|штук|pcs|pieces?|дана|ед\.?)\b", "", query)
        words = re.findall(r"[\w./-]+", query)
        keys = {self._key(word) for word in words}
        exact, scored = [], []
        stop = {"найди", "найдите", "покажи", "покажите", "есть", "мне", "нужен", "нужно", "нужна",
                "купить", "хочу", "товар", "артикул", "пожалуйста", "наличие", "сертификат", "шт", "для", "это",
                "по", "подбери", "подберите", "какой", "какая", "какие", "ли", "на", "характеристики", "цена",
                "find", "show", "me", "need", "want", "please", "buy", "the", "sku", "article", "barcode", "stock", "available",
                "керек", "тауар", "табыңыз", "ізде", "бар", "ма", "маған", "баға", "қажет", "дана"}
        tokens = [word for word in words if len(word) > 1 and word not in stop]
        requested_specs = {}
        for field, pattern in (("current", r"(?<![\w.])(\d+(?:\.\d+)?)\s*[аa]\b"),
                               ("poles", r"(?<![\w.])(\d+)\s*(?:[pрф]|poles?|полюс\w*)\b"),
                               ("voltage", r"(?<![\w.])(\d+)\s*[вv]\b"),
                               ("breaking_capacity", r"(?<![\w.])(\d+(?:\.\d+)?)\s*[кk][аa]\b")):
            found = re.search(pattern, query)
            if found:
                requested_specs[field] = number(found[1])
        for item in self._catalog_cache:
            props = item.get("properties") or {}
            identifiers = [item.get("article"), props.get("ARTIKULPOSTAVSHCHIKA"), props.get("CML2_BAR_CODE")]
            identifiers = [entry for value in identifiers for entry in (value if isinstance(value, list) else [value])]
            # Unlabelled quantities, voltages and budgets must not become IDs.
            # Explicit ID labels and a bare numeric identifier are handled above/below.
            if any(self._key(value) in keys for value in identifiers if value):
                exact.append({**item, "_match_type": "exact", "_match_score": 100})
                continue
            haystack = self.normalize_query(f"{item['name']} {item.get('article', '')} {' '.join(map(str, props.values()))}")
            if any(item.get("technical", {}).get(field) != expected for field, expected in requested_specs.items()):
                continue
            dimensions = re.findall(r"\b\d+x\d+(?:\.\d+)?\b", query)
            if dimensions and not all(re.search(rf"(?<![\d.]){re.escape(dimension)}(?![\d.])", haystack) for dimension in dimensions):
                continue
            score = sum(1 for word in tokens if word in haystack)
            requested_family = ("rcbo" if "дифавтомат" in query else "rcd" if "узо" in query else
                                "breaker" if "автомат" in query else "cable" if "кабель" in query else None)
            if requested_family:
                if item.get("technical", {}).get("family") != requested_family:
                    continue
                score += 1
            threshold = 1 if len(tokens) <= 2 else 2
            if score >= threshold:
                scored.append({**item, "_match_type": "text", "_match_score": score,
                               "_match_coverage": score / max(len(tokens), 1)})
        if bare_number and not exact:
            detail = self.get_product_detail(int(bare_number[0]))
            return [{**detail, "_match_type": "exact", "_match_score": 100}] if detail else []
        if article_query:
            return exact[:limit]
        return (exact or sorted(scored, key=lambda item: item["_match_score"], reverse=True))[:limit]

    def get_product_detail(self, product_id, force_refresh=False):
        if type(product_id) is not int or product_id < 1:
            return None
        with self._lock:
            cached = self._details.get(product_id)
            if cached and not force_refresh and self.clock() - cached[0] < self.detail_ttl:
                return copy.deepcopy(cached[1])
        data = self._request("products/detail", {"id": product_id})
        if not isinstance(data, dict) or data.get("id") != product_id:
            return None
        checked = self.clock()
        data = self._normalise_detail(data)
        data.update(last_checked_at=utc(checked), expires_at=utc(checked + self.detail_ttl), data_source="ekt.kz")
        with self._lock:
            if len(self._details) >= 2000:
                oldest = min(self._details, key=lambda key: self._details[key][0])
                del self._details[oldest]
            self._details[product_id] = (checked, data)
        return copy.deepcopy(data)

    @staticmethod
    def _normalise_detail(raw):
        data = copy.deepcopy(raw)
        props = data.get("properties") if isinstance(data.get("properties"), dict) else {}
        data["properties"] = props
        data["name"] = str(data.get("name") or "")
        data["article"] = str(data.get("article") or props.get("CML2_ARTICLE") or "")
        data["price"], data["quantity"] = number(data.get("price")), number(data.get("quantity"))
        data["price_verified"], data["stock_verified"] = data["price"] is not None, data["quantity"] is not None
        data["unit"] = str(data.get("unit") or props.get("EDINITSA_IZMERENIYA") or "шт.")
        data["min_order_quantity"] = number(props.get("KRATNOST_MIN"))
        data["order_multiple"] = number(props.get("KRATNOST")) or data["min_order_quantity"]
        data["stores"] = [
            {"id": store.get("id"), "name": str(store.get("name", "")), "quantity": number(store.get("quantity"))}
            for store in data.get("stores", []) if isinstance(store, dict)
        ] if isinstance(data.get("stores"), list) else []
        data["specifications"] = [{"key": key, "name": label, "value": str(props[key])}
                                  for key, label in SPEC_NAMES.items() if props.get(key) not in (None, "", [])]
        cert = safe_url(data.get("certificate_url") or data.get("certificate_link"))
        for key, value in props.items():
            if re.search("CERT|SERT", key, re.I):
                values = value if isinstance(value, list) else [value]
                cert = cert or next((safe_url(v) for v in values if isinstance(v, str) and (v.startswith("http") or v.startswith("/"))), None)
        data["certificate_url"] = cert
        data["image"], data["url"] = safe_url(data.get("image")), safe_url(data.get("url"))
        name = data["name"].lower().replace("×", "x").replace("х", "x")
        kind = str(props.get("OBYEM") or "").lower() + " " + name
        family = ("rcbo" if "диф" in kind else "rcd" if "узо" in kind
                  else "breaker" if "автомат" in kind or re.search(r"\bав\b", kind)
                  else "cable" if "кабель" in kind or "провод " in kind else "unknown")
        def from_name(pattern):
            found = re.search(pattern, name, re.I)
            return number(found[1]) if found else None
        name_current = from_name(r"(\d+(?:[.,]\d+)?)\s*[aа]\b")
        current = rating(props["NOMINALNYY_TOK"], "current") if props.get("NOMINALNYY_TOK") else name_current
        poles = measure(props.get("KOLICHESTVO_POLYUSOV")) or from_name(r"(\d+)\s*(?:p|р|ф)\b")
        voltage = rating(props["NOMINALNOE_NAPRYAZHENIE"], "voltage") if props.get("NOMINALNOE_NAPRYAZHENIE") else from_name(r"(?<![\d/])(\d+)\s*[вv]\b")
        capacity_key = "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST"
        capacity = rating(props[capacity_key], "capacity") if props.get(capacity_key) else from_name(r"(\d+(?:[.,]\d+)?)\s*[кk][аa]\b")
        cores = measure(props.get("KOLICHESTVO_ZHIL")) or from_name(r"\b(\d+)\s*x\s*\d")
        section_match = re.search(r"\b\d+\s*x\s*(\d+(?:[.,]\d+)?)", name)
        section = measure(props.get("SECHENIE")) or (number(section_match[1]) if section_match else None)
        curve_match = re.search(r"\b([bcdвсд])\s*\d{1,3}\b", name)
        curve = str(props.get("KHARAKTERISTIKA_SRABATYVANIYA") or (curve_match[1] if curve_match else "")).lower()
        curve = curve.translate(str.maketrans({"в": "b", "с": "c", "д": "d"}))
        cable_type = re.search(r"(ввг[а-яa-z()\-]*|пвс|сип|кг|nym)", name)
        data["technical"] = {"family": family, "current": current, "poles": poles, "voltage": voltage,
                             "breaking_capacity": capacity, "curve": curve or None,
                             "leakage_current": rating(props.get("NOMINALNYY_OTKLYUCHAYUSHCHIY_DIFFERENTSIALNYY_TOK"), "leakage"),
                             "cores": cores, "section": section,
                             "cable_type": cable_type[1] if cable_type else None}
        warnings, warning_codes = [], []
        if name_current is not None and current is not None and props.get("NOMINALNYY_TOK") and name_current != current:
            warnings.append(f"Ток в названии ({name_current:g} А) расходится со свойством каталога ({current:g} А). Требуется уточнение.")
            warning_codes.append({"code": "current_conflict", "params": {"name_current": name_current, "property_current": current}})
        data["data_quality_warnings"] = warnings
        data["warning_codes"] = warning_codes
        return data

    @staticmethod
    def analog_match(target, candidate):
        if target.get("data_quality_warnings") or candidate.get("data_quality_warnings"):
            return []
        left, right = target.get("technical", {}), candidate.get("technical", {})
        family = left.get("family")
        if family != right.get("family"):
            return []
        required = {"breaker": ["current", "poles", "voltage", "breaking_capacity"],
                    "rcbo": ["current", "poles", "voltage", "leakage_current", "breaking_capacity"],
                    "rcd": ["current", "poles", "voltage", "leakage_current"],
                    "cable": ["cores", "section", "cable_type"]}.get(family)
        if not required:
            return []
        required = required + [key for key in ("curve", "breaking_capacity") if key not in required and family != "cable" and left.get(key) is not None]
        labels = {"current": "Ток", "poles": "Полюса", "voltage": "Напряжение",
                  "breaking_capacity": "Отключающая способность", "curve": "Характеристика",
                  "leakage_current": "Дифференциальный ток", "cores": "Число жил",
                  "section": "Сечение", "cable_type": "Тип кабеля"}
        matches = []
        for key in required:
            original, alternative = left.get(key), right.get(key)
            if original is None or alternative is None:
                return []
            if (key == "breaking_capacity" and alternative < original) or (key != "breaking_capacity" and alternative != original):
                return []
            matches.append({"key": key, "name": labels[key], "original": original, "alternative": alternative})
        return matches

    def find_analogs(self, product, limit=3):
        if product.get("data_quality_warnings"):
            return []
        if not self.catalog_index or not self.catalog_index.coverage()["indexed_products"]:
            self.preload_catalog()
        family = product.get("technical", {}).get("family")
        candidates = [item for item in self._catalog_cache
                      if item["id"] != product["id"] and item.get("technical", {}).get("family") == family]
        details = self._parallel(lambda item: self.get_product_detail(item["id"], force_refresh=True), candidates[:16])
        matches = []
        for detail in details:
            if not detail or not detail["stock_verified"] or detail["quantity"] <= 0:
                continue
            parameters = self.analog_match(product, detail)
            if parameters:
                matches.append({**detail, "matched_parameters": parameters,
                                "rationale": "; ".join(f"{p['name']}: {p['alternative']}" for p in parameters),
                                "recommendation_note": "Перед монтажом проверьте габариты и условия применения по документации производителя."})
        return matches[:limit]

    @staticmethod
    def get_purchase_terms(language="ru"):
        from knowledge_base import purchase_terms
        return purchase_terms(language)


ekt_client = EktClient()
