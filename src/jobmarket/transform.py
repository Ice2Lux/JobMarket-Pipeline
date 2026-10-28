"""Nettoyage des offres brutes : aplatissement, typage, salaires, déduplication."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import pandas as pd

# Heures mensuelles d'un temps plein à 35 h (35 × 52 / 12).
MONTHLY_HOURS = 151.67

COLUMNS = [
    "id",
    "intitule",
    "description",
    "date_creation",
    "date_actualisation",
    "lieu_travail",
    "departement",
    "code_postal",
    "commune_insee",
    "latitude",
    "longitude",
    "rome_code",
    "rome_libelle",
    "entreprise",
    "type_contrat",
    "nature_contrat",
    "experience_exigee",
    "experience_libelle",
    "salaire_libelle",
    "salaire_min_annuel",
    "salaire_max_annuel",
    "duree_travail",
    "alternance",
    "qualification_libelle",
    "secteur_activite",
    "competences",
    "mots_cles",
    "date_ingestion",
]

_SALARY = re.compile(
    r"(?P<period>Annuel|Mensuel|Horaire)\s+de\s+(?P<low>[\d.]+)\s*Euros"
    r"(?:\s+à\s+(?P<high>[\d.]+)\s*Euros)?"
    r"(?:\s+sur\s+(?P<months>[\d.]+)\s*mois)?",
    re.IGNORECASE,
)
_DEPARTEMENT = re.compile(r"^\s*(\d{2,3}|2[AB])\s*-")


def parse_salary(libelle: str | None) -> tuple[float | None, float | None]:
    """Convertit un libellé de salaire France Travail en fourchette annuelle brute.

    >>> parse_salary("Mensuel de 3000.0 Euros à 3500.0 Euros sur 12.0 mois")
    (36000.0, 42000.0)
    """
    if not libelle:
        return None, None
    match = _SALARY.search(libelle)
    if not match:
        return None, None

    months = float(match["months"] or 12)
    factor = {
        "annuel": 1.0,
        "mensuel": months,
        "horaire": MONTHLY_HOURS * months,
    }[match["period"].lower()]

    low = round(float(match["low"]) * factor, 2)
    high = round(float(match["high"]) * factor, 2) if match["high"] else low
    return low, high


def parse_departement(lieu: str | None) -> str | None:
    """Extrait le département d'un libellé du type ``75 - Paris 8e``."""
    if not lieu:
        return None
    match = _DEPARTEMENT.match(lieu)
    return match.group(1) if match else None


def flatten_offer(raw: dict[str, Any]) -> dict[str, Any]:
    """Aplatit une offre JSON en une ligne à plat, en snake_case."""
    lieu = raw.get("lieuTravail") or {}
    entreprise = raw.get("entreprise") or {}
    salaire = raw.get("salaire") or {}
    salaire_libelle = salaire.get("libelle")
    salaire_min, salaire_max = parse_salary(salaire_libelle)
    competences = [c["libelle"] for c in raw.get("competences") or [] if c.get("libelle")]

    return {
        "id": raw.get("id"),
        "intitule": raw.get("intitule"),
        "description": raw.get("description"),
        "date_creation": raw.get("dateCreation"),
        "date_actualisation": raw.get("dateActualisation"),
        "lieu_travail": lieu.get("libelle"),
        "departement": parse_departement(lieu.get("libelle")),
        "code_postal": lieu.get("codePostal"),
        "commune_insee": lieu.get("commune"),
        "latitude": lieu.get("latitude"),
        "longitude": lieu.get("longitude"),
        "rome_code": raw.get("romeCode"),
        "rome_libelle": raw.get("romeLibelle"),
        "entreprise": entreprise.get("nom"),
        "type_contrat": raw.get("typeContrat"),
        "nature_contrat": raw.get("natureContrat"),
        "experience_exigee": raw.get("experienceExige"),
        "experience_libelle": raw.get("experienceLibelle"),
        "salaire_libelle": salaire_libelle,
        "salaire_min_annuel": salaire_min,
        "salaire_max_annuel": salaire_max,
        "duree_travail": raw.get("dureeTravailLibelleConverti"),
        "alternance": raw.get("alternance"),
        "qualification_libelle": raw.get("qualificationLibelle"),
        "secteur_activite": raw.get("secteurActiviteLibelle"),
        "competences": "; ".join(competences) or None,
        "mot_cle": raw.get("_mot_cle"),
    }


def clean_offers(raw_offers: list[dict[str, Any]], ingestion_date: date) -> pd.DataFrame:
    """Transforme les offres brutes en DataFrame propre, une ligne par offre.

    Une même offre peut remonter pour plusieurs mots-clés : on garde la version la plus
    récemment actualisée et on conserve la liste des mots-clés qui l'ont trouvée.
    """
    if not raw_offers:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame([flatten_offer(o) for o in raw_offers])
    df = df[df["id"].notna()]
    df = df.replace("", None)

    for col in ("date_creation", "date_actualisation"):
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    for col in ("latitude", "longitude", "salaire_min_annuel", "salaire_max_annuel"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["experience_exigee"] = df["experience_exigee"].map({"D": "Débutant accepté", "S": "Souhaitée", "E": "Exigée"})
    df["alternance"] = df["alternance"].astype("boolean")

    mots_cles = (
        df.dropna(subset=["mot_cle"])
        .groupby("id")["mot_cle"]
        .agg(lambda s: "; ".join(sorted(set(s))))
        .rename("mots_cles")
    )
    df = (
        df.sort_values("date_actualisation", ascending=False, na_position="last")
        .drop_duplicates("id")
        .drop(columns="mot_cle")
        .merge(mots_cles, how="left", left_on="id", right_index=True)
    )
    df["date_ingestion"] = pd.Timestamp(ingestion_date)

    return df[COLUMNS].sort_values("id").reset_index(drop=True)
