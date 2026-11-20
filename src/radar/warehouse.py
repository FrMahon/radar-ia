"""Warehouse en SQLite: carga lo crudo, corre los modelos SQL en orden y los controles de calidad."""
from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path

from radar.raw import read_lines

SQL_DIR = Path(__file__).parent / "sql"


@lru_cache(maxsize=None)
def _compiled(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


def _regexp(pattern: str, text: str | None) -> bool:
    return text is not None and _compiled(pattern).search(text) is not None


def connect(path: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.create_function("regexp", 2, _regexp, deterministic=True)  # habilita `texto REGEXP patrón` en SQL
    return con


def load(con: sqlite3.Connection, raw_dir: Path) -> None:
    """Recarga completa desde los archivos crudos: idempotente y sin estado escondido en la base."""
    con.executescript("""
        DROP TABLE IF EXISTS raw_arxiv;
        CREATE TABLE raw_arxiv (day TEXT NOT NULL, payload TEXT NOT NULL);
        DROP TABLE IF EXISTS raw_hf;
        CREATE TABLE raw_hf (snapshot_date TEXT NOT NULL, payload TEXT NOT NULL);
    """)
    for source, table in (("arxiv", "raw_arxiv"), ("hf", "raw_hf")):
        for path in sorted((raw_dir / source).glob("*.jsonl.gz")):
            day = path.name[:10]
            con.executemany(f"INSERT INTO {table} VALUES (?, ?)", ((day, line) for line in read_lines(path)))
    con.commit()


def transform(con: sqlite3.Connection, sql_dir: Path = SQL_DIR) -> list[str]:
    models = sorted(sql_dir.glob("*.sql"))
    for path in models:
        con.executescript(path.read_text(encoding="utf-8"))
    con.commit()
    return [p.stem for p in models]


def run_checks(con: sqlite3.Connection, checks_dir: Path = SQL_DIR / "checks") -> list[dict]:
    """Cada control es un SELECT que devuelve las filas que lo rompen; pasa si no devuelve ninguna.
    Los que empiezan con `warn_` avisan pero no frenan la publicación."""
    results = []
    for path in sorted(checks_dir.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        first = sql.splitlines()[0]
        failing = len(con.execute(sql).fetchall())
        results.append({
            "name": path.stem,
            "description": first.removeprefix("--").strip() if first.startswith("--") else path.stem,
            "severity": "warn" if path.stem.startswith("warn_") else "error",
            "failing_rows": failing,
            "passed": failing == 0,
        })
    return results
