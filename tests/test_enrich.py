import requests

from ai_outbound_engine.enrich import HomepageFetcher, html_to_text


def test_html_to_text_skips_scripts_and_reads_meta():
    html = ('<html><head><meta name="description" content="Pipeline for B2B teams">'
            "<script>var x = 1;</script></head><body><h1>Hello</h1><style>p{}</style><p>World</p></body></html>")
    assert html_to_text(html) == "Pipeline for B2B teams Hello World"


def test_fetcher_fails_gracefully(monkeypatch):
    fetcher = HomepageFetcher(timeout=0.1)

    def boom(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(fetcher.session, "get", boom)
    assert fetcher("nowhere.example") == ""

