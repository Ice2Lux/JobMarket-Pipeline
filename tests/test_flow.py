"""Test de bout en bout : le flow Prefect complet contre une API France Travail simulée."""

import json
from datetime import date

import pytest
import responses
from deltalake import DeltaTable
from prefect.testing.utilities import prefect_test_harness

from jobmarket.config import Settings
from jobmarket.flow import jobmarket_flow


@pytest.fixture(scope="module", autouse=True)
def prefect_harness():
    with prefect_test_harness():
        yield


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "id")
    monkeypatch.setenv("FT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("FT_KEYWORDS", json.dumps(["data engineer", "data analyst"]))
    monkeypatch.setenv("FT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FT_REQUEST_DELAY_S", "0")
    return Settings()


def test_flow_end_to_end(env, raw_offers):
    with responses.RequestsMock(assert_all_requests_are_fired=False) as api:
        api.post(env.auth_url, json={"access_token": "tok", "expires_in": 1499})
        api.get(env.search_url, json={"resultats": raw_offers[:2]}, status=200)
        api.get(env.search_url, json={"resultats": raw_offers[1:]}, status=200)

        result = jobmarket_flow(ingestion_date=date(2026, 10, 28))

        api_calls = len(api.calls)

    assert result == {"inserted": 3, "updated": 0}
    assert (env.raw_dir / "date_ingestion=2026-10-28" / "offres.jsonl").exists()

    df = DeltaTable(str(env.table_path)).to_pandas().set_index("id")
    assert len(df) == 3
    assert df.loc["198XKQM", "mots_cles"] == "data analyst; data engineer"

    # Second run le même jour : relu depuis la couche brute, sans appel API ni doublon.
    with responses.RequestsMock() as api:
        assert jobmarket_flow(ingestion_date=date(2026, 10, 28)) == {"inserted": 0, "updated": 0}
        assert len(api.calls) == 0
    assert api_calls == 3
