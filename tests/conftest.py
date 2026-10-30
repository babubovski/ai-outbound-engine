from pathlib import Path

import pytest

from ai_outbound_engine.config import load_config
from ai_outbound_engine.leads import Lead

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def config():
    return load_config(EXAMPLES / "icp.yaml")


@pytest.fixture
def leads_path():
    return EXAMPLES / "leads.csv"


@pytest.fixture
def vp_sales():
    return Lead(first_name="Ada", last_name="Sample", title="VP of Sales", company="Brightloop Analytics",
                domain="brightloop.example", industry="B2B SaaS", notes="is hiring three SDRs in Austin")
