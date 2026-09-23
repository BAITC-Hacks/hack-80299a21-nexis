"""Resumable product discovery index. Never an authority for price or stock."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


class CatalogIndex:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("NEXIS_CATALOG_DB_PATH", str(ROOT / "database" / "catalog.sqlite3")))

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS catalog_products (id INTEGER PRIMARY KEY,payload TEXT NOT NULL,generation INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS catalog_meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS catalog_pages (generation INTEGER,page INTEGER,page_hash TEXT,PRIMARY KEY(generation,page));
            """)
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def meta(db):
        return dict(db.execute("SELECT key,value FROM catalog_meta"))

    def coverage(self):
        if not self.path.exists():
            return {"indexed_products": 0, "complete_catalog": False, "next_page": 1, "status": "not_imported"}
        with self.connect() as db:
            meta = self.meta(db)
            count = db.execute("SELECT COUNT(*) FROM catalog_products").fetchone()[0]
        return {"indexed_products": count, "complete_catalog": meta.get("complete") == "true",
                "next_page": int(meta.get("next_page", 1)), "status": meta.get("status", "not_imported"),
                "indexed_at": meta.get("updated_at"), "completed_at": meta.get("completed_at"),
                "last_error": meta.get("last_error") or None}

    def start(self, restart=False):
        with self.connect() as db:
            meta = self.meta(db)
            generation = int(meta.get("generation", 0))
            if restart or not generation:
                generation += 1
                self._set(db, generation=generation, next_page=1, complete="false", status="importing", last_error="")
            else:
                self._set(db, status="importing", last_error="")
        return generation, 1 if restart else int(meta.get("next_page", 1))

    @staticmethod
    def _set(db, **values):
        db.executemany("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)", [(key,str(value)) for key,value in values.items()])

    def record_page(self, page, items, generation, page_hash):
        with self.connect() as db:
            meta = self.meta(db)
            if int(meta.get("generation", 0)) != generation or int(meta.get("next_page", 1)) != page:
                raise ValueError("import_checkpoint_changed")
            repeat = db.execute("SELECT page FROM catalog_pages WHERE generation=? AND page_hash=? AND page<>?",
                                (generation, page_hash, page)).fetchone()
            if items and repeat:
                raise ValueError("repeated_page")
            for item in items:
                clean = {key:value for key,value in item.items() if key not in {
                    "price", "quantity", "stores", "price_verified", "stock_verified", "expires_at"}}
                clean.update(price=None, quantity=None, stores=[], price_verified=False, stock_verified=False,
                             data_source="ekt.kz_catalog_index", discovery_only=True)
                db.execute("INSERT OR REPLACE INTO catalog_products VALUES (?,?,?)",
                           (item["id"], json.dumps(clean, ensure_ascii=False), generation))
            db.execute("INSERT OR REPLACE INTO catalog_pages VALUES (?,?,?)", (generation,page,page_hash))
            self._set(db, next_page=page+1, updated_at=now(), status="importing", complete="false", last_error="")

    def finish(self, generation):
        with self.connect() as db:
            db.execute("DELETE FROM catalog_products WHERE generation<>?", (generation,))
            self._set(db, complete="true", status="complete", completed_at=now(), last_error="")

    def pause(self, reason):
        with self.connect() as db:
            self._set(db, status="paused", complete="false", last_error=reason, updated_at=now())

    def products(self):
        if not self.path.exists():
            return []
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM catalog_products").fetchall()
        return [json.loads(row[0]) for row in rows]
