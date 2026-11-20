"""Capa cruda: archivos JSONL comprimidos, uno por día y por fuente. Se leen y escriben línea a línea."""
from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator
from pathlib import Path

USER_AGENT = "radar-ia/0.1 (portfolio data pipeline)"


def get(url: str, tries: int = 4, wait: float = 15.0) -> bytes:
    """GET con reintentos y espera creciente (las APIs públicas fallan de vez en cuando)."""
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == tries:
                raise
            time.sleep(wait * attempt)
    raise AssertionError("unreachable")


def write_jsonl_gz(path: Path, rows: Iterable[dict]) -> int:
    """Escribe de forma atómica: si el proceso se corta, no queda un archivo a medias."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    n = 0
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    tmp.replace(path)
    return n


def read_lines(path: Path) -> Iterator[str]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield line.rstrip("\n")
