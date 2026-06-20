from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import CheckResult, Product, utc_now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  adapter TEXT NOT NULL,
  name TEXT,
  target_price INTEGER,
  notify_on_sale INTEGER NOT NULL DEFAULT 1,
  sizes_json TEXT NOT NULL DEFAULT '[]',
  current_price INTEGER,
  currency TEXT NOT NULL DEFAULT 'TWD',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id),
  price INTEGER,
  currency TEXT NOT NULL DEFAULT 'TWD',
  sale_label TEXT,
  stock_status TEXT,
  checked_at TEXT NOT NULL,
  raw_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id),
  event_type TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  created_at TEXT NOT NULL,
  raw_json TEXT NOT NULL DEFAULT '{}'
);
"""


class TrackerDB:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        # WAL lets the MCP server and a cron job read/write concurrently; the
        # busy timeout makes a contending writer wait instead of failing fast.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def add_product(self, product: Product) -> Product:
        now = utc_now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO products
                  (url, adapter, name, target_price, notify_on_sale, sizes_json,
                   current_price, currency, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                  adapter=excluded.adapter,
                  name=COALESCE(excluded.name, products.name),
                  target_price=excluded.target_price,
                  notify_on_sale=excluded.notify_on_sale,
                  sizes_json=excluded.sizes_json,
                  active=1,
                  updated_at=excluded.updated_at
                RETURNING *
                """,
                (
                    product.url,
                    product.adapter,
                    product.name,
                    product.target_price,
                    int(product.notify_on_sale),
                    json.dumps(product.sizes),
                    product.current_price,
                    product.currency,
                    now,
                    now,
                ),
            )
            row = cur.fetchone()
        return self._row_to_product(row)

    def list_products(self, active_only: bool = True) -> list[Product]:
        sql = "SELECT * FROM products"
        params: tuple[Any, ...] = ()
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY id"
        with self.connect() as conn:
            return [self._row_to_product(row) for row in conn.execute(sql, params)]

    def get_product(self, product_id: int) -> Product | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return self._row_to_product(row) if row else None

    def deactivate_product(self, product_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE products SET active = 0, updated_at = ? WHERE id = ?",
                (utc_now_iso(), product_id),
            )
            return cur.rowcount > 0

    def record_check(self, result: CheckResult) -> None:
        with self.connect() as conn:
            previous = conn.execute(
                "SELECT current_price FROM products WHERE id = ?", (result.product_id,)
            ).fetchone()
            old_price = previous["current_price"] if previous else None
            conn.execute(
                """
                INSERT INTO price_history
                  (product_id, price, currency, sale_label, stock_status, checked_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.product_id,
                    result.current_price,
                    result.currency,
                    result.sale_label,
                    result.stock_status,
                    result.checked_at,
                    json.dumps(result.raw, ensure_ascii=False),
                ),
            )
            conn.execute(
                "UPDATE products SET current_price = ?, currency = ?, updated_at = ? WHERE id = ?",
                (result.current_price, result.currency, result.checked_at, result.product_id),
            )
            for event in result.events:
                conn.execute(
                    """
                    INSERT INTO events
                      (product_id, event_type, old_value, new_value, created_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.product_id,
                        str(event.get("event_type", "unknown")),
                        None if old_price is None else str(old_price),
                        None if result.current_price is None else str(result.current_price),
                        result.checked_at,
                        json.dumps(event, ensure_ascii=False),
                    ),
                )

    def history(self, product_id: int, limit: int = 200) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT price, currency, sale_label, stock_status, checked_at, raw_json
                FROM price_history
                WHERE product_id = ?
                ORDER BY checked_at DESC, id DESC
                LIMIT ?
                """,
                (product_id, limit),
            ).fetchall()
        return [dict(row) | {"raw": json.loads(row["raw_json"])} for row in rows]

    @staticmethod
    def _row_to_product(row: sqlite3.Row) -> Product:
        return Product(
            id=int(row["id"]),
            url=str(row["url"]),
            adapter=str(row["adapter"]),
            name=row["name"],
            target_price=row["target_price"],
            notify_on_sale=bool(row["notify_on_sale"]),
            sizes=json.loads(row["sizes_json"] or "[]"),
            current_price=row["current_price"],
            currency=str(row["currency"]),
            active=bool(row["active"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
