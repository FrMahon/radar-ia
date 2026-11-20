"""Extracción de Hugging Face: una foto diaria de los 100 modelos en tendencia."""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

from radar.raw import get as http_get
from radar.raw import write_jsonl_gz

API = "https://huggingface.co/api/models?sort=trendingScore&limit=100"


def fetch_trending(get: Callable[[str], bytes] = http_get) -> list[dict]:
    models = json.loads(get(API))
    return [{"rank": i, **m} for i, m in enumerate(models, start=1)]


def extract(raw_dir: Path, today: date, log=print) -> int:
    path = raw_dir / "hf" / f"{today}.jsonl.gz"
    if path.exists():  # la foto del día se saca una sola vez
        log(f"hf {today}: ya existe")
        return 0
    try:
        n = write_jsonl_gz(path, fetch_trending())
    except Exception as err:
        log(f"hf {today}: falló ({err})")
        return 1
    log(f"hf {today}: {n} modelos")
    return 0
