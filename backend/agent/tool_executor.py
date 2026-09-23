"""Read-only allowlist, complete tool evidence and bounded JSON serialization."""
import json
from .contracts import Evidence
from .router import city_stores


def compact_json(value, limit=24000):
    """Truncate values structurally; never emit cut, invalid JSON to the model."""
    def trim(item, depth=0):
        if isinstance(item, str): return item[:1800]
        if isinstance(item, list): return [trim(row, depth + 1) for row in item[:8]]
        if isinstance(item, dict):
            return {str(k): trim(v, depth + 1) for k, v in item.items()
                    if k not in {"properties", "offers", "image", "description"} or depth < 1}
        return item
    payload = trim(value)
    encoded = json.dumps(payload, ensure_ascii=False)
    if len(encoded) <= limit: return encoded
    if isinstance(payload, list):
        while payload and len(json.dumps(payload, ensure_ascii=False)) > limit - 100: payload.pop()
        return json.dumps({"items": payload, "truncated": True}, ensure_ascii=False)
    if isinstance(payload, dict):
        # Retain complete fields that fit instead of slicing a JSON token.
        result = {"truncated": True}
        for key, item in payload.items():
            candidate = {**result, key: item}
            if len(json.dumps(candidate, ensure_ascii=False)) <= limit: result = candidate
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"truncated": True})


class ToolExecutor:
    def __init__(self, catalog, knowledge_search):
        self.catalog, self.knowledge_search = catalog, knowledge_search

    def execute(self, name, args, language="ru", deadline=None):
        if deadline: deadline.require()
        if not isinstance(args, dict): return {"error": "invalid_arguments"}
        if name in {"get_product_detail", "find_analogs", "check_city_stock"}:
            pid = args.get("product_id")
            if type(pid) is not int or pid < 1: return {"error": "invalid_product_id"}
            detail = self.catalog.get_product_detail(pid)
            if not detail: return {"error": "catalog_unavailable"}
            if name == "get_product_detail": return detail
            if name == "find_analogs": return self.catalog.find_analogs(detail, limit=3)
            place = args.get("city")
            if not isinstance(place, str) or not place.strip(): return {"error": "city_required"}
            return {"product_id": pid, "product": detail, "city": place, "matched_stores": city_stores(detail, place)}
        if name == "search_products" and isinstance(args.get("query"), str):
            return self.catalog.search_products(args["query"][:500], limit=5)
        if name == "query_knowledge_base" and isinstance(args.get("topic"), str):
            return self.knowledge_search(args["topic"][:500], language=language)
        return {"error": "tool_not_allowed"}

    @staticmethod
    def collect(evidence: Evidence, name, output, args=None):
        if isinstance(output, dict) and output.get("error"):
            evidence.errors.append(output["error"])
            return
        if name in {"search_products", "get_product_detail", "find_analogs"}:
            target = evidence.selected if name == "get_product_detail" else evidence.analogs if name == "find_analogs" else evidence.products
            for item in output if isinstance(output, list) else [output]:
                if isinstance(item, dict) and type(item.get("id")) is int: target[item["id"]] = item
            if name == "find_analogs" and isinstance(args, dict) and type(args.get("product_id")) is int:
                evidence.analogs_by_target[args["product_id"]] = {
                    item["id"]: item for item in output if isinstance(item, dict) and type(item.get("id")) is int}
        elif name == "check_city_stock" and isinstance(output, dict) and output.get("product_id"):
            pid = output["product_id"]
            evidence.cities[pid] = {"city": output["city"], "stores": output.get("matched_stores", [])}
            if output.get("product"): evidence.selected[pid] = output["product"]
        elif name == "query_knowledge_base" and isinstance(output, list):
            evidence.articles.update({item["id"]: item for item in output if isinstance(item, dict) and item.get("id")})
