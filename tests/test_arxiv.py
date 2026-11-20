from datetime import date

import pytest

from radar import arxiv

FEED = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults>{total}</opensearch:totalResults>
  {entries}
</feed>"""

ENTRY = """<entry>
    <id>http://arxiv.org/abs/{id}v{v}</id>
    <title>A tool-using
      agent</title>
    <summary>  We build an
      agent. </summary>
    <published>2026-11-10T13:09:11Z</published>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.CL"/>
    <author><name>A</name></author><author><name>B</name></author>
  </entry>"""


def feed(total, ids):
    return FEED.format(total=total, entries="".join(ENTRY.format(id=i, v=2) for i in ids)).encode()


def test_parse_feed_normalizes_fields():
    total, papers = arxiv.parse_feed(feed(1, ["2611.14039"]))
    assert total == 1
    assert papers == [{
        "id": "2611.14039", "version": 2, "title": "A tool-using agent", "abstract": "We build an agent.",
        "published": "2026-11-10T13:09:11Z", "primary_category": "cs.CL",
        "categories": ["cs.CL", "cs.AI"], "n_authors": 2,
    }]


def test_parse_feed_raises_on_api_error():
    error = FEED.format(total=1, entries="<entry><id>http://arxiv.org/api/errors#bad</id><summary>bad query</summary></entry>")
    with pytest.raises(RuntimeError, match="bad query"):
        arxiv.parse_feed(error.encode())


def test_fetch_day_pages_and_retries_empty_page():
    responses = [feed(3, ["1", "2"]), feed(3, []), feed(3, ["3"])]  # la segunda página llega vacía una vez
    urls = []

    def fake_get(url):
        urls.append(url)
        return responses.pop(0)

    papers = arxiv.fetch_day(date(2026, 11, 10), get=fake_get, pause=0, page=2)
    assert sorted(p["id"] for p in papers) == ["1", "2", "3"]
    assert "submittedDate" in urls[0] and "start=2" in urls[1]


def test_days_to_fetch_fills_gaps_and_refreshes_recent_days():
    today = date(2026, 11, 20)
    existing = {date(2026, 11, d) for d in range(10, 20)}  # 10 al 19 ya bajados
    days = arxiv.days_to_fetch(existing, today, window=12, refresh=3)
    assert days == [date(2026, 11, 19), date(2026, 11, 18), date(2026, 11, 17), date(2026, 11, 9), date(2026, 11, 8)]


def test_extract_prunes_only_days_outside_the_window(tmp_path, monkeypatch):
    from radar.raw import write_jsonl_gz
    today = date(2026, 11, 20)
    raw = tmp_path / "raw"
    for name in ("2026-08-01", "2026-11-10"):  # 111 días atrás (fuera) y 10 días atrás (dentro)
        write_jsonl_gz(raw / "arxiv" / f"{name}.jsonl.gz", [{"id": name}])
    monkeypatch.setattr(arxiv, "fetch_day", lambda day: [])  # sin red; un día vacío no se escribe
    arxiv.extract(raw, today, window=84, log=lambda *_: None)
    assert sorted(p.name for p in (raw / "arxiv").iterdir()) == ["2026-11-10.jsonl.gz"]
