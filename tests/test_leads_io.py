import csv

import pytest

from ai_outbound_engine.leads import OUTPUT_COLUMNS, load_leads, normalize_domain, write_rows


def test_loads_example_file(leads_path):
    leads = load_leads(leads_path)
    assert len(leads) == 8
    assert leads[0].first_name == "Ada"
    assert leads[2].domain == "stackwise.example"  # URL normalized to bare domain


def test_apollo_style_headers_and_full_name(tmp_path):
    path = tmp_path / "apollo.csv"
    path.write_text(
        "Name,Job Title,Company Name,Website,Person Linkedin Url\n"
        "Dana Placeholder,Head of Sales,Orbit Labs,https://www.orbit.example/about,https://linkedin.example/in/dana\n",
        encoding="utf-8",
    )
    (lead,) = load_leads(path)
    assert (lead.first_name, lead.last_name) == ("Dana", "Placeholder")
    assert lead.title == "Head of Sales"
    assert lead.company == "Orbit Labs"
    assert lead.domain == "orbit.example"
    assert lead.linkedin.endswith("/dana")


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("first_name,title,company\nAda,VP Sales,Acme\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row 2 is missing domain"):
        load_leads(path)


@pytest.mark.parametrize("raw", ["https://www.acme.example/pricing", "ACME.example", "http://acme.example"])
def test_normalize_domain(raw):
    assert normalize_domain(raw) == "acme.example"


def test_write_rows_round_trips_multiline_copy(tmp_path):
    out = tmp_path / "out.csv"
    body = "Hi Ada,\n\nLine one.\n\nMax"
    write_rows([{"first_name": "Ada", "email_1": body, "icp_score": 75, "ignored": "x"}], out)
    with open(out, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == OUTPUT_COLUMNS
        (row,) = list(reader)
    assert row["email_1"] == body
    assert row["icp_score"] == "75"
