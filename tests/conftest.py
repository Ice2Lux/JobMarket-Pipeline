import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def raw_offers() -> list[dict]:
    return json.loads((FIXTURES / "offres_page.json").read_text(encoding="utf-8"))["resultats"]
