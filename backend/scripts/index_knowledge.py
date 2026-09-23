"""Build curated RAG index. --embeddings explicitly allows paid API calls."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import settings  # load root .env before reading configuration
from retrieval.store import KnowledgeIndex


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embeddings", action="store_true", help="Make paid embedding API calls for changed chunks")
    parser.add_argument("--db", help="SQLite index path")
    parser.add_argument("--corpus", help="Approved JSON corpus path; never user uploads")
    args = parser.parse_args()
    if args.embeddings and not os.getenv("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required for --embeddings")
    index = KnowledgeIndex(**{key: value for key, value in {"path": args.db, "corpus_path": args.corpus}.items() if value})
    print(json.dumps(index.build(with_embeddings=args.embeddings), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
