"""radar extract | build | run"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from radar import arxiv, hf
from radar.export import export
from radar.warehouse import connect, load, run_checks, transform


def cmd_extract(data: Path, window: int) -> int:
    today = datetime.now(timezone.utc).date()
    return arxiv.extract(data / "raw", today, window=window) + hf.extract(data / "raw", today)


def cmd_build(data: Path, site_data: Path) -> int:
    start = time.perf_counter()
    db = data / "warehouse.db"
    db.unlink(missing_ok=True)
    con = connect(db)
    load(con, data / "raw")
    for model in transform(con):
        print(f"modelo {model}: ok")
    checks = run_checks(con)
    for c in checks:
        mark = "ok" if c["passed"] else ("AVISO" if c["severity"] == "warn" else "FALLA")
        print(f"control {c['name']}: {mark} ({c['failing_rows']} filas)")
    if any(not c["passed"] and c["severity"] == "error" for c in checks):
        print("Hay controles que fallan: no se publica.", file=sys.stderr)
        return 1
    export(con, site_data, checks, time.perf_counter() - start)
    con.close()
    print(f"exportado a {site_data}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description="Pipeline de papers y modelos de IA")
    parser.add_argument("command", choices=["extract", "build", "run"])
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--site-data", type=Path, default=Path("site/data"))
    parser.add_argument("--window", type=int, default=84, help="días de arXiv a mantener (por defecto 12 semanas)")
    args = parser.parse_args(argv)

    failed = 0
    if args.command in ("extract", "run") and not os.environ.get("RADAR_SKIP_EXTRACT"):
        failed = cmd_extract(args.data, args.window)
        if failed:
            print(f"{failed} extracciones fallaron; se reintentan en la próxima corrida.", file=sys.stderr)
    if args.command in ("build", "run"):
        return cmd_build(args.data, args.site_data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
