"""Run: python -m backend.evals.run [--output report.json] [--repeat 1].

Always offline: fake catalog transport, no LLM, embeddings disabled and ephemeral DBs.
This development set measures rules/contract regressions, not model accuracy or live latency.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def verify(response, expect):
    if "sources" in expect:
        assert [item["id"] for item in response["sources"]] == expect["sources"], "product ids"
    if expect.get("no_sources"): assert not response["sources"], "unexpected products"
    if expect.get("no_offer"): assert response["pending_offer"] is None, "unexpected offer"
    if "pending_quantity" in expect: assert response["pending_offer"]["quantity"] == expect["pending_quantity"], "offer quantity"
    if "pending_product" in expect: assert response["pending_offer"]["product_id"] == expect["pending_product"], "offer product"
    if "stock" in expect: assert response["sources"][0]["quantity"] == expect["stock"], "stock preservation"
    if "price" in expect: assert response["sources"][0]["price"] == expect["price"], "price preservation"
    if "updated" in expect: assert response["cart_updated"] == expect["updated"], "cart mutation"
    if "cart_count" in expect: assert response["cart_items_count"] == expect["cart_count"], "cart count"
    if "warning" in expect: assert expect["warning"] in response["warning_codes"], "warning code"
    if "contains" in expect: assert expect["contains"] in response["answer"], "required sourced text"
    if "clarification" in expect: assert response["clarification"]["kind"] == expect["clarification"], "clarification kind"
    if "city" in expect: assert response["sources"][0]["city_stock"]["city"] == expect["city"], "city preservation"
    if "analogs" in expect: assert [p["id"] for p in response["sources"][0]["analogs"]] == expect["analogs"], "verified analogs"
    if expect.get("knowledge"): assert response["knowledge_sources"], "knowledge sources"


def run(repeat=1):
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["NEXIS_EMBEDDINGS_ENABLED"] = "false"
    with tempfile.TemporaryDirectory(prefix="nexis-eval-") as workspace:
        os.environ["NEXIS_KNOWLEDGE_DB_PATH"] = str(Path(workspace) / "knowledge.sqlite3")
        from backend.tests.support import APIHarness
        from backend.evals.cases import CASES
        outcomes = []
        for run_number in range(repeat):
            for case in CASES:
                harness = APIHarness()
                started = time.perf_counter()
                try:
                    harness.setUp()
                    harness.agent.client = None
                    if case["setup"].get("barcode"):
                        harness.transport.products[1001]["properties"]["CML2_BAR_CODE"] = case["setup"]["barcode"]
                    for turn in case["turns"]:
                        before = harness.carts.snapshot(harness.sid)["total_items"]
                        response = harness.agent.process_message(turn["message"], [], harness.sid, case["language"])
                        assert response["answer_language"] == case["language"], "answer language"
                        assert response["answer"], "empty answer"
                        verify(response, turn["expect"])
                        if not response["cart_updated"]:
                            assert harness.carts.snapshot(harness.sid)["total_items"] == before, "unconfirmed mutation"
                    outcome = {"id": case["id"], "language": case["language"], "run": run_number + 1, "passed": True}
                except Exception as error:
                    outcome = {"id": case["id"], "language": case["language"], "run": run_number + 1,
                               "passed": False, "error": f"{type(error).__name__}: {error}"}
                finally:
                    harness.doCleanups()
                outcome["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
                outcomes.append(outcome)
    summary = {}
    for language in ("ru", "kk", "en"):
        rows = [row for row in outcomes if row["language"] == language]
        times = sorted(row["elapsed_ms"] for row in rows)
        summary[language] = {"passed": sum(row["passed"] for row in rows), "total": len(rows),
                             "synthetic_case_p50_ms": round(statistics.median(times), 2),
                             "synthetic_case_p95_ms": times[max(0, int(len(times) * .95) - 1)]}
    return {"mode": "offline_rules", "dataset": "development_regressions", "model_calls": 0,
            "note": "Synthetic catalog; not a held-out LLM quality score or live API latency measurement.",
            "summary": summary, "passed": all(row["passed"] for row in outcomes), "cases": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeat", type=int, default=1, choices=range(1, 11))
    args = parser.parse_args()
    report = run(args.repeat)
    if args.output: args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "summary": report["summary"], "failed": [row for row in report["cases"] if not row["passed"]]}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
