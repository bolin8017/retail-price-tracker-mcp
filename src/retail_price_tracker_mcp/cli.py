from __future__ import annotations

import argparse
import json

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
    add.add_argument("--size", action="append", default=[])
    sub.add_parser("list")
    check = sub.add_parser("check")
    check.add_argument("product_id", type=int)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("query")
    resolve.add_argument("--limit", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = TrackerService(TrackerDB(default_db_path()))
    if args.command == "add":
        data = service.add_product(args.url, args.target_price, True, args.size, args.name)
    elif args.command == "list":
        data = service.list_products()
    elif args.command == "check":
        data = service.check_product(args.product_id)
    elif args.command == "resolve":
        data = service.resolve_product(args.query, args.limit)
    else:  # pragma: no cover
        raise SystemExit(2)
    print(json.dumps(data, ensure_ascii=False, indent=2))
