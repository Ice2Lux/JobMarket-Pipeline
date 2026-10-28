from datetime import date

from deltalake import DeltaTable

from jobmarket.load import load_raw, save_raw, upsert_offers
from jobmarket.transform import clean_offers


def test_raw_layer_roundtrip(tmp_path, raw_offers):
    day = date(2026, 10, 28)
    assert load_raw(tmp_path, day) is None

    path = save_raw(raw_offers, tmp_path, day)

    assert path.parent.name == "date_ingestion=2026-10-28"
    assert load_raw(tmp_path, day) == raw_offers


def test_upsert_is_idempotent_and_updates_changed_offers(tmp_path, raw_offers):
    table = tmp_path / "offres"
    day1 = clean_offers(raw_offers, date(2026, 10, 27))

    assert upsert_offers(day1, table) == {"inserted": 3, "updated": 0}
    # Relancer avec les mêmes données ne change rien.
    assert upsert_offers(day1, table) == {"inserted": 0, "updated": 0}

    # Le lendemain : une offre actualisée et une nouvelle offre.
    updated = {**raw_offers[0], "intitule": "Senior Data Engineer", "dateActualisation": "2026-10-28T08:00:00.000Z"}
    new = {**raw_offers[1], "id": "NOUVELLE"}
    day2 = clean_offers([updated, new], date(2026, 10, 28))

    assert upsert_offers(day2, table) == {"inserted": 1, "updated": 1}

    df = DeltaTable(str(table)).to_pandas().set_index("id")
    assert len(df) == 4
    assert df.loc["198XKPL", "intitule"] == "Senior Data Engineer"


def test_upsert_empty_dataframe_does_nothing(tmp_path):
    table = tmp_path / "offres"
    assert upsert_offers(clean_offers([], date(2026, 10, 28)), table) == {"inserted": 0, "updated": 0}
    assert not table.exists()
