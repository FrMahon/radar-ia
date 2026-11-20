"""Pipeline de punta a punta sobre datos sintéticos: crudo → SQLite → marts → controles → JSON."""
import json
from datetime import date, timedelta

import pytest

from radar.export import export
from radar.raw import write_jsonl_gz
from radar.warehouse import connect, load, run_checks, transform

MONDAY = date(2026, 10, 5)


def paper(pid, day, title, version=1):
    return {"id": pid, "version": version, "title": title, "abstract": "Some abstract.",
            "published": f"{day}T10:00:00Z", "primary_category": "cs.CL", "categories": ["cs.CL"], "n_authors": 3}


def model(mid, task="text-generation"):
    return {"id": mid, "likes": 10, "downloads": 100, "trendingScore": 5, "pipeline_tag": task,
            "createdAt": "2026-11-01T00:00:00.000Z"}


@pytest.fixture
def raw(tmp_path):
    raw = tmp_path / "raw"
    # 8 semanas completas, 4 papers por semana; "agentes" crece de 1 de 4 a 3 de 4.
    for week in range(8):
        day = MONDAY + timedelta(weeks=week)
        agents = 1 if week < 4 else 3
        rows = [paper(f"{week}.{i}", day, "An LLM agent" if i < agents else "A diffusion model") for i in range(4)]
        write_jsonl_gz(raw / "arxiv" / f"{day}.jsonl.gz", rows)
    # el domingo de la última semana: cierra la cobertura y trae una versión nueva de un paper repetido
    last = MONDAY + timedelta(weeks=7, days=6)
    write_jsonl_gz(raw / "arxiv" / f"{last}.jsonl.gz", [paper("7.0", MONDAY + timedelta(weeks=7), "An LLM agent", version=2)])
    write_jsonl_gz(raw / "hf" / "2026-11-19.jsonl.gz", [{"rank": 1, **model("a/x")}, {"rank": 2, **model("b/y")}])
    write_jsonl_gz(raw / "hf" / "2026-11-20.jsonl.gz",
                   [{"rank": 1, **model("b/y")}, {"rank": 2, **model("c/z", "text-to-image")}, {"rank": 3, **model("a/x")}])
    return raw


@pytest.fixture
def con(raw, tmp_path):
    con = connect(tmp_path / "w.db")
    load(con, raw)
    transform(con)
    return con


def test_staging_keeps_latest_version_once(con):
    assert con.execute("SELECT count(*) FROM stg_papers").fetchone()[0] == 32
    assert con.execute("SELECT version FROM stg_papers WHERE paper_id = '7.0'").fetchone()[0] == 2


def test_weekly_share_and_growth(con):
    shares = con.execute("SELECT week, share FROM mart_weekly_topics WHERE topic_id = 'agentes' ORDER BY week").fetchall()
    assert len(shares) == 8
    assert shares[0] == (str(MONDAY), 0.25) and shares[-1][1] == 0.75
    growth = con.execute("SELECT share_start, share_end, change FROM mart_topic_growth WHERE topic_id = 'agentes'").fetchone()
    assert growth == (0.25, 0.75, 0.5)


def test_regex_tagging_uses_word_boundaries(con):
    # "agent" etiqueta; "diffusion" no se cuela en agentes
    assert con.execute("SELECT count(*) FROM fct_paper_topics WHERE topic_id = 'agentes'").fetchone()[0] == 16
    assert con.execute("SELECT count(*) FROM fct_paper_topics WHERE topic_id = 'difusion'").fetchone()[0] == 16


def test_hf_movers_compare_with_previous_snapshot(con):
    rows = con.execute("SELECT model_id, rank, previous_rank, days_trending FROM mart_hf_today ORDER BY rank").fetchall()
    assert rows == [("b/y", 1, 2, 2), ("c/z", 2, None, 1), ("a/x", 3, 1, 2)]


def test_checks_pass_on_clean_data(con):
    results = {c["name"]: c for c in run_checks(con)}
    assert all(c["passed"] for c in results.values() if c["severity"] == "error")
    assert results["unique_paper"]["description"] == "Cada paper aparece una sola vez"


def test_checks_catch_duplicate_rank(con):
    con.execute("INSERT INTO stg_hf_trending (snapshot_date, rank, model_id) VALUES ('2026-11-20', 1, 'd/w')")
    failing = {c["name"] for c in run_checks(con) if not c["passed"]}
    assert "hf_unique_rank" in failing


def test_export_writes_dashboard_json(con, tmp_path):
    out = tmp_path / "site"
    export(con, out, run_checks(con), seconds=1.0)
    radar = json.loads((out / "radar.json").read_text(encoding="utf-8"))
    assert radar["papers_total"] == 32
    assert radar["topics"][0]["id"] in {"agentes", "difusion"}
    assert {"week", "topic", "share"} <= set(radar["weekly"][0])
    papers = json.loads((out / "papers.json").read_text(encoding="utf-8"))
    assert len(papers) == 4 and ["agentes"] in [p["topics"] for p in papers]
