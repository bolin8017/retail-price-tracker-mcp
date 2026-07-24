from __future__ import annotations

import subprocess
import sys


def test_importing_server_creates_no_database(tmp_path):
    # Importing the module (inspectors, docs tools, test collection) must not
    # write a tracker.db wherever the process happens to be running.
    subprocess.run(
        [sys.executable, "-c", "import retail_price_tracker_mcp.server"],
        cwd=tmp_path,
        check=True,
    )
    assert not (tmp_path / "tracker.db").exists()
