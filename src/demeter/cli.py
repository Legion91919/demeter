"""Command-line entry point for scheduled or manual loads.

    PYTHONPATH=src python -m demeter.cli load samples/*.csv [--layout keelridge]
Exit code 0 when every file loaded, 1 when any file was quarantined or failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from demeter.config import Settings
from demeter.jobs import run_load
from demeter.model import Warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="demeter")
    sub = parser.add_subparsers(dest="command", required=True)
    load = sub.add_parser("load", help="land, reconcile and load rent-roll files")
    load.add_argument("files", nargs="+", type=Path)
    load.add_argument("--layout", default=None)
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    wh = Warehouse(settings.warehouse_path)
    ok = True
    try:
        for path in args.files:
            run = run_load(wh, settings, path.read_bytes(), path.name, args.layout)
            ok &= run["status"] == "succeeded"
            print(
                json.dumps(
                    {
                        k: run[k]
                        for k in ("original_name", "status", "rows_read", "rows_written", "rows_rejected", "message")
                    },
                    default=str,
                )
            )
    finally:
        wh.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
