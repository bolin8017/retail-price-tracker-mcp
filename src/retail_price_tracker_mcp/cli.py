from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .config import default_db_path
from .db import TrackerDB
from .service import TrackerService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Retail price tracker helper CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("url")
    add.add_argument("--name")
    add.add_argument("--target-price", type=int)
    add.add_argument("--size", action="append", default=None)
    sub.add_parser("list")
    check = sub.add_parser("check")
    check.add_argument("product_id", type=int)
    sub.add_parser("check-all")
    history = sub.add_parser("history")
    history.add_argument("product_id", type=int)
    history.add_argument("--days", type=int, default=90)
    remove = sub.add_parser("remove")
    remove.add_argument("product_id", type=int)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("query")
    resolve.add_argument("--limit", type=int, default=5)
    resolve_image = sub.add_parser("resolve-image")
    resolve_image.add_argument("image_path")
    resolve_image.add_argument("--limit", type=int, default=5)
    return parser


def _dispatch(service: TrackerService, args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "add":
        return service.add_product(args.url, args.target_price, None, args.size, args.name)
    if args.command == "list":
        return service.list_products()
    if args.command == "check":
        return service.check_product(args.product_id)
    if args.command == "check-all":
        return service.check_all()
    if args.command == "history":
        return service.price_history(args.product_id, args.days)
    if args.command == "remove":
        return service.remove_product(args.product_id)
    if args.command == "resolve":
        return service.resolve_product(args.query, args.limit)
    if args.command == "resolve-image":
        return service.resolve_product_from_image(args.image_path, args.limit)
    raise SystemExit(2)  # pragma: no cover - argparse rejects unknown commands


def main() -> None:
    args = build_parser().parse_args()
    service = TrackerService(TrackerDB(default_db_path()))
    try:
        data = _dispatch(service, args)
    # Expected user-facing failures (unknown id, missing image, OCR extra not
    # installed) become concise stderr messages instead of tracebacks.
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(data, ensure_ascii=False, indent=2))
