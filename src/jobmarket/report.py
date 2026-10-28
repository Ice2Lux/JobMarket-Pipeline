"""Petit rapport sur la table des offres, pour vérifier le contenu après un run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deltalake import DeltaTable

from jobmarket.config import StorageSettings


def summarize(table_path: Path, top: int = 10) -> dict[str, Any]:
    df = DeltaTable(str(table_path)).to_pandas()
    competences = df["competences"].dropna().str.split("; ").explode().str.strip()
    salaires = df[["salaire_min_annuel", "salaire_max_annuel"]].dropna().mean(axis=1)

    return {
        "offres": len(df),
        "par_contrat": df["type_contrat"].value_counts().head(top),
        "par_departement": df["departement"].value_counts().head(top),
        "competences": competences.value_counts().head(top),
        "salaire_median": float(salaires.median()) if not salaires.empty else None,
        "part_avec_salaire": len(salaires) / len(df) if len(df) else 0.0,
    }


def print_report() -> None:
    table_path = StorageSettings().table_path
    if not table_path.exists():
        print(f"Aucune table trouvée dans {table_path}. Lancez d'abord : python -m jobmarket run")
        return

    s = summarize(table_path)
    print(f"Offres en base : {s['offres']}")
    if s["salaire_median"] is not None:
        print(f"Salaire annuel médian (milieu de fourchette) : {s['salaire_median']:,.0f} €".replace(",", " "))
        print(f"Offres avec un salaire exploitable : {s['part_avec_salaire']:.0%}")
    for title, key in [
        ("Types de contrat", "par_contrat"),
        ("Départements", "par_departement"),
        ("Compétences les plus demandées", "competences"),
    ]:
        print(f"\n{title}")
        for label, count in s[key].items():
            print(f"  {label:<50} {count}")
