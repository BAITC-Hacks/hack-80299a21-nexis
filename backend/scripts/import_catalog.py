"""Explicit read-only paginated EKT import with checkpoint and bounded retries."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ekt_client import EktClient
from retrieval.catalog_index import CatalogIndex


def import_catalog(client, index, max_pages=100, restart=False, delay=.25, sleep=time.sleep):
    generation, page = index.start(restart)
    for _ in range(max_pages):
        result = None
        for attempt in range(4):
            result = client.get_page(page, force=True)
            if result is not None:
                break
            if client.last_error != "upstream_http_429":
                break
            sleep(min(max(getattr(client, "retry_after", 0) or 0, 2 ** attempt), 30))
        if result is None:
            index.pause(client.last_error or "page_unavailable")
            return index.coverage()
        items = result["items"]
        signature = hashlib.sha256(json.dumps(sorted(item["id"] for item in items)).encode()).hexdigest()
        try:
            index.record_page(page, items, generation, signature)
        except ValueError as exc:
            index.pause(str(exc))
            return index.coverage()
        if not items:
            index.finish(generation)
            return index.coverage()
        page += 1
        sleep(max(delay, 0))
    index.pause("page_budget_reached")
    return index.coverage()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=100, help="Bound requests in this run; resume on the next invocation")
    parser.add_argument("--restart", action="store_true", help="Start a new generation; prune obsolete IDs only on completion")
    parser.add_argument("--delay", type=float, default=.25)
    parser.add_argument("--db")
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 100000 or args.delay < 0:
        parser.error("Invalid import limits")
    client = EktClient()
    if not client.auth:
        parser.error("EKT_API_USER and EKT_API_PASS are required")
    print(json.dumps(import_catalog(client, CatalogIndex(args.db), args.max_pages, args.restart, args.delay), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
