from __future__ import annotations

import json
import sys

from retail_price_tracker_mcp import cli


def run_cli(args, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PRICE_TRACKER_DB", str(tmp_path / "tracker.db"))
    monkeypatch.setattr(sys, "argv", ["retail-price-tracker", *args])
    code = 0
    try:
        cli.main()
    except SystemExit as exc:
        code = int(exc.code or 0)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_check_unknown_id_prints_error_not_traceback(tmp_path, monkeypatch, capsys):
    code, out, err = run_cli(["check", "999"], tmp_path, monkeypatch, capsys)
    assert code == 1
    assert "Product not found: 999" in err
    assert out == ""


def test_resolve_image_missing_file_prints_error(tmp_path, monkeypatch, capsys):
    code, out, err = run_cli(
        ["resolve-image", str(tmp_path / "missing.jpg")], tmp_path, monkeypatch, capsys
    )
    assert code == 1
    assert "missing.jpg" in err


def test_remove_check_all_and_history_subcommands(tmp_path, monkeypatch, capsys):
    code, out, _ = run_cli(
        ["add", "static://demo", "--name", "Demo"], tmp_path, monkeypatch, capsys
    )
    assert code == 0
    product_id = json.loads(out)["id"]

    code, out, _ = run_cli(["check-all"], tmp_path, monkeypatch, capsys)
    assert code == 0
    assert json.loads(out)["checked"] == 1

    code, out, _ = run_cli(["history", str(product_id)], tmp_path, monkeypatch, capsys)
    assert code == 0
    assert json.loads(out)["product_id"] == product_id

    code, out, _ = run_cli(["remove", str(product_id)], tmp_path, monkeypatch, capsys)
    assert code == 0
    assert json.loads(out)["removed"] is True
