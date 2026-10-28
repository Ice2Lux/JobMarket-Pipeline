"""Orchestration Prefect du pipeline : extract → transform → load."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from prefect import flow, get_run_logger, task

from jobmarket.config import Settings
from jobmarket.extract import FranceTravailClient
from jobmarket.load import load_raw, save_raw, upsert_offers
from jobmarket.transform import clean_offers


@task(retries=2, retry_delay_seconds=30)
def extract(settings: Settings, ingestion_date: date, refresh: bool) -> list[dict[str, Any]]:
    logger = get_run_logger()

    cached = None if refresh else load_raw(settings.raw_dir, ingestion_date)
    if cached is not None:
        logger.info("Données brutes du %s déjà présentes (%d offres) : API non rappelée", ingestion_date, len(cached))
        return cached

    client = FranceTravailClient(
        client_id=settings.client_id,
        client_secret=settings.client_secret.get_secret_value(),
        auth_url=settings.auth_url,
        search_url=settings.search_url,
        scope=settings.scope,
        page_size=settings.page_size,
        request_delay_s=settings.request_delay_s,
        timeout_s=settings.timeout_s,
    )
    records = client.search(settings.keywords)
    path = save_raw(records, settings.raw_dir, ingestion_date)
    logger.info("%d offres brutes sauvegardées dans %s", len(records), path)
    return records


@task
def transform(records: list[dict[str, Any]], ingestion_date: date) -> pd.DataFrame:
    df = clean_offers(records, ingestion_date)
    get_run_logger().info("%d offres brutes → %d offres uniques", len(records), len(df))
    return df


@task
def load(df: pd.DataFrame, settings: Settings) -> dict[str, int]:
    result = upsert_offers(df, settings.table_path)
    get_run_logger().info(
        "Table %s : %d insérées, %d mises à jour", settings.table_path, result["inserted"], result["updated"]
    )
    return result


@flow(name="jobmarket-france-travail", log_prints=True)
def jobmarket_flow(ingestion_date: date | None = None, refresh: bool = False) -> dict[str, int]:
    """Collecte les offres data du jour et met à jour la table Delta.

    Args:
        ingestion_date: date de la partition brute à produire ou rejouer (par défaut aujourd'hui).
        refresh: force un nouvel appel à l'API même si les données du jour existent déjà.
    """
    settings = Settings()
    ingestion_date = ingestion_date or date.today()

    records = extract(settings, ingestion_date, refresh)
    df = transform(records, ingestion_date)
    return load(df, settings)
