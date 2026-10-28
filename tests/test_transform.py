from datetime import date

import pandas as pd
import pytest

from jobmarket.transform import COLUMNS, clean_offers, flatten_offer, parse_departement, parse_salary

INGESTION = date(2026, 10, 28)


@pytest.mark.parametrize(
    ("libelle", "expected"),
    [
        ("Annuel de 45000.0 Euros à 55000.0 Euros sur 12.0 mois", (45000.0, 55000.0)),
        ("Mensuel de 2600.0 Euros sur 12.0 mois", (31200.0, 31200.0)),
        ("Mensuel de 3000.0 Euros à 3500.0 Euros sur 13.0 mois", (39000.0, 45500.0)),
        ("Horaire de 12.0 Euros sur 12 mois", (21840.48, 21840.48)),
        ("Selon profil", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_salary(libelle, expected):
    assert parse_salary(libelle) == expected


@pytest.mark.parametrize(
    ("lieu", "expected"),
    [
        ("75 - Paris 9e Arrondissement", "75"),
        ("2A - Ajaccio", "2A"),
        ("974 - Saint-Denis", "974"),
        ("Ile-de-France", None),
        (None, None),
    ],
)
def test_parse_departement(lieu, expected):
    assert parse_departement(lieu) == expected


def test_flatten_offer_handles_missing_nested_objects():
    row = flatten_offer({"id": "X1", "intitule": "Data Engineer"})
    assert row["id"] == "X1"
    assert row["entreprise"] is None
    assert row["competences"] is None
    assert row["salaire_min_annuel"] is None


def test_clean_offers_schema_and_types(raw_offers):
    df = clean_offers([{**o, "_mot_cle": "data"} for o in raw_offers], INGESTION)

    assert list(df.columns) == COLUMNS
    assert len(df) == 3
    assert isinstance(df["date_creation"].dtype, pd.DatetimeTZDtype)

    engineer = df.set_index("id").loc["198XKPL"]
    assert engineer["departement"] == "75"
    assert engineer["entreprise"] == "DATAFLOW SAS"
    assert engineer["experience_exigee"] == "Exigée"
    assert engineer["competences"] == "Concevoir des pipelines de données; Python"
    assert engineer["salaire_max_annuel"] == 55000.0


def test_clean_offers_deduplicates_and_keeps_latest_version(raw_offers):
    offer = raw_offers[0]
    older = {**offer, "intitule": "Ancien intitulé", "dateActualisation": "2026-10-21T00:00:00.000Z"}
    records = [
        {**older, "_mot_cle": "big data"},
        {**offer, "_mot_cle": "data engineer"},
        {**offer, "_mot_cle": "data engineer"},
    ]

    df = clean_offers(records, INGESTION)

    assert len(df) == 1
    assert df.loc[0, "intitule"] == "Data Engineer H/F"
    assert df.loc[0, "mots_cles"] == "big data; data engineer"


def test_clean_offers_empty_input():
    df = clean_offers([], INGESTION)
    assert df.empty
    assert list(df.columns) == COLUMNS
