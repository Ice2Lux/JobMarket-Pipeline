"""
Module de nettoyage et de transformation du DataFrame France Travail.

Fonctionnalités :
- Conversion des noms de colonnes CamelCase / camelCase → snake_case
- Suppression de colonnes inutiles
"""
import re
from typing import List

import pandas as pd
from prefect import get_run_logger


def camel_to_snake(name: str) -> str:
    """
    Convertit une chaîne CamelCase ou camelCase en snake_case.

    Args:
        name (str): Nom de colonne à convertir.

    Returns:
        str: Nom converti en snake_case.
    """
    # Première transformation : "CamelCase" → "Camel_Case"
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Deuxième transformation : "camelCASE" → "camel_CASE"
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def main(data: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie et formate un DataFrame :
      - Convertit les colonnes CamelCase / camelCase en snake_case
      - Supprime certaines colonnes jugées inutiles (si elles existent)

    Args:
        data (pd.DataFrame): Le DataFrame d’entrée contenant les données brutes.

    Returns:
        pd.DataFrame: Le DataFrame nettoyé et formaté.
    """

    logger = get_run_logger()
    logger.info("Nettoyage et formatage du dataframe...")

    # Renommage des colonnes
    old_cols: List[str] = list(data.columns)
    new_cols: List[str] = [camel_to_snake(col) for col in old_cols]
    data.columns = new_cols

    logger.info(f"Colonnes renommées : {dict(zip(old_cols, new_cols))}")

    # Colonnes à supprimer (seulement si elles existent)
    cols_to_drop = ["lieu_travail", "entreprise"]
    drop_existing = [c for c in cols_to_drop if c in data.columns]

    if drop_existing:
        logger.info(f"Suppression des colonnes inutiles : {drop_existing}")
        data = data.drop(columns=drop_existing)
    else:
        logger.info("Aucune colonne à supprimer trouvée.")

    logger.info("Nettoyage terminé.")
    return data
