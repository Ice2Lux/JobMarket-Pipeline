"""Persistance : couche brute (JSON Lines) et table Delta Lake des offres nettoyées."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

logger = logging.getLogger(__name__)


# --- Couche bronze ----------------------------------------------------------


def raw_partition(raw_dir: Path, ingestion_date: date) -> Path:
    return raw_dir / f"date_ingestion={ingestion_date.isoformat()}" / "offres.jsonl"


def save_raw(records: list[dict[str, Any]], raw_dir: Path, ingestion_date: date) -> Path:
    """Sauvegarde les réponses brutes de l'API, telles quelles, pour pouvoir rejouer le pipeline."""
    path = raw_partition(raw_dir, ingestion_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(path)  # écriture atomique : pas de fichier à moitié écrit en cas d'erreur
    return path


def load_raw(raw_dir: Path, ingestion_date: date) -> list[dict[str, Any]] | None:
    """Relit la couche brute du jour si elle existe (re-run sans rappeler l'API)."""
    path = raw_partition(raw_dir, ingestion_date)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --- Couche silver ----------------------------------------------------------


def upsert_offers(df: pd.DataFrame, table_path: Path) -> dict[str, int]:
    """Fusionne les offres dans la table Delta (clé : ``id``).

    - offre inconnue : insérée ;
    - offre connue et actualisée depuis : mise à jour ;
    - offre connue et inchangée : ignorée.

    Relancer le pipeline sur les mêmes données ne crée donc aucun doublon.
    """
    if df.empty:
        logger.info("Aucune offre à écrire")
        return {"inserted": 0, "updated": 0}

    table = pa.Table.from_pandas(df, preserve_index=False)

    if not DeltaTable.is_deltatable(str(table_path)):
        table_path.parent.mkdir(parents=True, exist_ok=True)
        write_deltalake(str(table_path), table, mode="error")
        return {"inserted": len(df), "updated": 0}

    metrics = (
        DeltaTable(str(table_path))
        .merge(source=table, predicate="t.id = s.id", source_alias="s", target_alias="t")
        .when_matched_update_all(predicate="s.date_actualisation > t.date_actualisation")
        .when_not_matched_insert_all()
        .execute()
    )
    return {
        "inserted": int(metrics.get("num_target_rows_inserted", 0)),
        "updated": int(metrics.get("num_target_rows_updated", 0)),
    }
