"""Extracción de arXiv: un archivo crudo por día de envío, con los papers de IA de ese día."""
from __future__ import annotations

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

from radar.raw import get as http_get
from radar.raw import write_jsonl_gz

API = "https://export.arxiv.org/api/query"
CATEGORIES = ("cs.AI", "cs.CL", "cs.LG", "cs.CV")
PAGE = 500
PAUSE = 3.0  # arXiv pide no más de un pedido cada 3 segundos
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "os": "http://a9.com/-/spec/opensearch/1.1/",
}


def parse_feed(xml: bytes) -> tuple[int, list[dict]]:
    """Devuelve (total de resultados de la búsqueda, papers de esta página)."""
    root = ET.fromstring(xml)
    papers = []
    for entry in root.findall("a:entry", NS):
        url = entry.findtext("a:id", "", NS)
        if "/api/errors" in url:
            raise RuntimeError(f"arXiv devolvió un error: {entry.findtext('a:summary', '', NS).strip()}")
        m = re.search(r"/abs/(.+)v(\d+)$", url)
        if not m:
            continue
        primary = entry.find("arxiv:primary_category", NS)
        papers.append({
            "id": m.group(1),
            "version": int(m.group(2)),
            "title": " ".join(entry.findtext("a:title", "", NS).split()),
            "abstract": " ".join(entry.findtext("a:summary", "", NS).split()),
            "published": entry.findtext("a:published", "", NS),
            "primary_category": primary.get("term") if primary is not None else None,
            "categories": [c.get("term") for c in entry.findall("a:category", NS)],
            "n_authors": len(entry.findall("a:author", NS)),
        })
    return int(root.findtext("os:totalResults", "0", NS)), papers


def fetch_day(day: date, get: Callable[[str], bytes] = http_get, pause: float = PAUSE, page: int = PAGE) -> list[dict]:
    d = day.strftime("%Y%m%d")
    cats = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    query = f"({cats}) AND submittedDate:[{d}0000 TO {d}2359]"
    papers: dict[str, dict] = {}
    start, total = 0, 1
    while start < total:
        url = API + "?" + urllib.parse.urlencode({
            "search_query": query, "start": start, "max_results": page,
            "sortBy": "submittedDate", "sortOrder": "ascending",
        })
        # arXiv a veces devuelve una página vacía aunque haya resultados: se reintenta.
        for attempt in range(3):
            total, rows = parse_feed(get(url))
            time.sleep(pause)
            if rows or start >= total:
                break
        else:
            raise RuntimeError(f"arXiv devolvió páginas vacías para {day} (start={start}, total={total})")
        for p in rows:
            papers[p["id"]] = p
        start += page
    return list(papers.values())


def days_to_fetch(existing: set[date], today: date, window: int, refresh: int) -> list[date]:
    """Días que faltan en la ventana, más los últimos `refresh` días: arXiv publica con 1 a 3 días de demora."""
    days = [today - timedelta(days=n) for n in range(1, window + 1)]
    return [d for d in days if d not in existing or (today - d).days <= refresh]


def extract(raw_dir: Path, today: date, window: int = 84, refresh: int = 3, log=print) -> int:
    out = raw_dir / "arxiv"
    out.mkdir(parents=True, exist_ok=True)
    existing = {date.fromisoformat(p.name[:10]): p for p in out.glob("*.jsonl.gz")}
    # La ventana se mueve: los días viejos se borran para que la caché no crezca sin límite.
    for d, path in existing.items():
        if (today - d).days > window + 7:
            path.unlink()
    failed = 0
    for day in days_to_fetch(set(existing), today, window, refresh):
        try:
            papers = fetch_day(day)
        except Exception as err:  # un día que falla no frena al resto; se reintenta en la próxima corrida
            failed += 1
            log(f"arxiv {day}: falló ({err})")
            continue
        if papers:  # un día vacío no se guarda: así se vuelve a pedir en la próxima corrida
            write_jsonl_gz(out / f"{day}.jsonl.gz", papers)
        log(f"arxiv {day}: {len(papers)} papers")
    return failed
