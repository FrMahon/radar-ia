"""Exporta los marts a JSON chico para el tablero estático."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

TABLES = ("raw_arxiv", "raw_hf", "stg_papers", "stg_hf_trending", "fct_paper_topics",
          "mart_weekly_topics", "mart_topic_growth", "mart_hf_today")


def rows(con: sqlite3.Connection, sql: str, *params) -> list[dict]:
    cur = con.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def export(con: sqlite3.Connection, out_dir: Path, checks: list[dict], seconds: float, recent_days: int = 7) -> None:
    coverage = rows(con, "SELECT * FROM mart_coverage")[0]
    radar = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "coverage": coverage,
        "papers_total": con.execute("SELECT count(*) FROM stg_papers").fetchone()[0],
        "papers_tagged": con.execute("SELECT count(DISTINCT paper_id) FROM fct_paper_topics").fetchone()[0],
        "topics": rows(con, """
            SELECT t.topic_id AS id, t.name, t.description, g.share_start, g.share_end, g.change
            FROM dim_topics AS t LEFT JOIN mart_topic_growth AS g USING (topic_id)
            ORDER BY g.share_end DESC"""),
        "weekly": rows(con, "SELECT week, topic_id AS topic, papers, total_papers AS total, share FROM mart_weekly_topics ORDER BY week, topic_id"),
        "hf": rows(con, "SELECT rank, model_id, task, likes, previous_rank, previous_date, days_trending FROM mart_hf_today ORDER BY rank"),
        "pipeline": {
            "tables": {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLES},
            "checks": checks,
            "seconds": round(seconds, 1),
        },
    }
    papers = rows(con, """
        SELECT p.paper_id AS id, p.title, p.published_date AS date, p.primary_category AS category,
               (SELECT json_group_array(topic_id) FROM fct_paper_topics AS pt WHERE pt.paper_id = p.paper_id) AS topics
        FROM stg_papers AS p
        WHERE p.published_date >= date((SELECT last_day FROM mart_coverage), ?)
        ORDER BY p.published_at DESC""", f"-{recent_days - 1} days")
    for p in papers:
        p["topics"] = json.loads(p["topics"])
    _write(out_dir / "radar.json", radar)
    _write(out_dir / "papers.json", papers)
