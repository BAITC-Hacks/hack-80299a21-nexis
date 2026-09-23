"""Offline retrieval evaluation: ten topics in RU/KK/EN, no model/API calls.

Run python -m backend.evals.retrieval [--output path.json]. This is a development
regression set, not a held-out claim about broad language or model quality.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retrieval.store import KnowledgeIndex

TOPICS = [
    ("returns", "Мне нужно вернуть купленный кабель", "Сатып алған кабельді қалай қайтаруға болады?", "How can I return a cable?"),
    ("delivery", "Как вы отправляете товары в другой город?", "Басқа қалаға тауарды қалай жеткізесіздер?", "How do you ship items to another city?"),
    ("payment", "Какими способами я могу заплатить?", "Төлемді қалай жасаймын?", "What payment methods can I use?"),
    ("minimum_order", "Какой минимальный объём заказа?", "Тапсырыстың ең аз саны қанша?", "Is there a minimum order quantity?"),
    ("certificates", "Где найти сертификат соответствия?", "Тауардың сәйкестік сертификатын қайдан аламын?", "Where can I obtain a product certificate?"),
    ("warranty", "Где уточнить гарантию на изделие?", "Тауар кепілдігін қайдан нақтылаймын?", "Who can confirm the product warranty?"),
    ("rcd_definition", "Что такое УЗО?", "ҚАҚ деген не?", "What is an RCD?"),
    ("rcbo", "Что представляет собой дифавтомат?", "Дифавтомат деген не?", "What is an RCBO?"),
    ("mcb_rcd", "В чём разница между УЗО и автоматом?", "Автомат пен ҚАҚ айырмашылығы қандай?", "What is the difference between an MCB and an RCD?"),
    ("selectivity", "Объясните селективность защиты", "Қорғаныс селективтілігі деген не?", "Explain protection selectivity"),
]


def run():
    outcomes = []
    with tempfile.TemporaryDirectory(prefix="nexis-retrieval-eval-") as workspace, patch.dict(
            os.environ, {"NEXIS_EMBEDDINGS_ENABLED": "false", "OPENAI_API_KEY": ""}), patch(
            "retrieval.store.embed", side_effect=AssertionError("Network forbidden in offline retrieval evaluation")):
        index = KnowledgeIndex(Path(workspace) / "knowledge.sqlite3")
        for expected, *phrases in TOPICS:
            for language, query in zip(("ru", "kk", "en"), phrases):
                results = index.search(query, limit=5, language=language)
                identifiers = [item["id"] for item in results]
                outcomes.append({"query": query, "language": language, "expected": expected,
                                 "retrieved": identifiers, "top1": bool(identifiers and identifiers[0] == expected),
                                 "recall_at_5": expected in identifiers})
        corpus = index.status()
    summary = {}
    for language in ("ru", "kk", "en", "all"):
        selected = [row for row in outcomes if language == "all" or row["language"] == language]
        summary[language] = {"total": len(selected), "top1_correct": sum(row["top1"] for row in selected),
                             "top1_accuracy": sum(row["top1"] for row in selected) / len(selected),
                             "recall_at_5": sum(row["recall_at_5"] for row in selected) / len(selected)}
    return {"mode": "offline_lexical", "dataset": "development_retrieval_regressions", "model_calls": 0,
            "note": "Curated-corpus retrieval only; not held-out model accuracy or production reliability.",
            "corpus": corpus, "summary": summary, "cases": outcomes}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "summary": report["summary"],
                      "failures": [item for item in report["cases"] if not item["top1"]]}, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["all"]["top1_accuracy"] == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
