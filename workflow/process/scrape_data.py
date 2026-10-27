import os
import time
import requests
import pandas as pd

from typing import Dict, List, Any
from prefect import get_run_logger
import azfr_fsspec_utils as fspath

pd.set_option("display.max_colwidth", None)

MOT_CLEF_LIST = ["data", "data scientist", "data engineer", "data analyst", "data architect", "machine learning",
                 "deep learning", "IA", "intelligence artificielle", "big data", "data science", "data mining",
                 "data visualisation", "data visualization", "business intelligence"]



def get_access_token(auth_url: str) -> str:
    """
    Authenticate to the API using client credentials and return an access token.

    Args : 
    auth_url : str
        The URL of the authentication endpoint.

    Returns :
    str
        The access token returned by the authentication API.
    """

    logger = get_run_logger()

    logger.info("Authentication à l'API...")

    auth_data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("ID_CLIENT"),
        "client_secret": os.getenv("SECRET_KEY"),
        "scope": "o2dsoffre api_offresdemploiv2",
    }

    response = requests.post(auth_url, data=auth_data)
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_job_offers(base_url, headers, mot_clef, start=0, step=100)-> List[Dict[str, Any]]:
    """
    Fetch job offers from the API using a keyword, paginated via a range.

    Args:
        base_url (str): Offers API endpoint.
        headers (dict): HTTP headers including Authorization token.
        mot_clef (str): Keyword used to search job offers.
        start (int): Pagination start index.
        step (int): Number of results per page.

    Returns:
        list[dict]: A flat list of offers retrieved for this keyword.
    """

    logger = get_run_logger()

    logger.info(f"\nRecherche des offres pour le mot-clé: {mot_clef}")
    offers = []
    while True:
        end = start + step - 1
        params = {
            "motsCles": mot_clef,
            "range": f"{start}-{end}",
            "tri": "DATE_CREATION_DESC",
        }
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if "resultats" not in data or not data["resultats"]:
                break
            offers.extend(data["resultats"])
            start += step
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Une erreur est survenue en requêtant {base_url}: {str(e)}")
            break
    return offers


def get_competences(response: dict) -> str | None:
    """Extract competencies as a comma-separated string."""

    competences_list = []
    if "competences" in response:
        for competence in response["competences"]:
            competences_list.append(competence["libelle"])
        competences = ", ".join(competences_list)
    else:
        competences = None
    return competences


class Offre:
    """
    Classe représentant une offre d'emploi.
    """

    def __init__(self, response):

        self.id = response.get("id", "")
        self.intitule = response.get("intitule", "")
        self.description = response.get("description", "")
        self.dateCreation = response.get("dateCreation", "")
        self.dateActualisation = response.get("dateActualisation", "")

        self.lieuTravail = response.get("lieuTravail", {}) or {}
        self.lieuTravailLibelle = self.lieuTravail.get("libelle", "")
        self.lieuTravailCodePostal = self.lieuTravail.get("codePostal", "")
        self.lieuTravailCommune = self.lieuTravail.get("commune", "")

        self.romeCode = response.get("romeCode", "")
        self.romeLibelle = response.get("romeLibelle", "")

        self.entreprise = response.get("entreprise", {}) or {}
        self.nomEntreprise = self.entreprise.get("nom", "")
        self.descriptionEntreprise = self.entreprise.get("description", "")
        self.adapteeTravailleurHandicape = self.entreprise.get("entrepriseAdaptee", "")

        salaire_data = response.get("salaire", {}) or {}
        self.typeContrat = response.get("typeContrat", "")
        self.natureContrat = response.get("natureContrat", "")
        self.experienceExige = response.get("experienceExige", "")
        self.experienceLibelle = response.get("experienceLibelle", "")
        self.salaire = salaire_data.get("libelle", "")
        self.dureeTravailLibelle = response.get("dureeTravailLibelle", "")
        self.dureeTravailLibelleConverti = response.get("dureeTravailLibelleConverti", "")
        self.alternance = response.get("alternance", "")
        self.qualificationCode = response.get("qualificationCode", "")
        self.qualificationLibelle = response.get("qualificationLibelle", "")
        self.secteurActivite = response.get("secteurActivite", "")
        self.secteurActiviteLibelle = response.get("secteurActiviteLibelle", "")
        self.competences = get_competences(response)

    def to_dict(self) -> dict:
        """Retourne les données de l'offre sous forme de dictionnaire."""

        return self.__dict__


def offres_to_dataframe(all_offers: list) -> pd.DataFrame:
    """
    Convertit une liste d'offres JSON en DataFrame pandas.

    Args:
        all_offers (list[dict]): Liste de dictionnaires représentant les offres d'emploi.

    Returns:
        pd.DataFrame: Un DataFrame contenant une ligne par offre.
    """

    logger = get_run_logger()


    if not all_offers:
        logger.warning("Aucune offre trouvée — la liste est vide.")
        return pd.DataFrame()

    offres_instances = []

    for r in all_offers:
        try:
            offre = Offre(r)
            offres_instances.append(offre.to_dict())
        except Exception as e:
            logger.error(f"Erreur lors du traitement d'une offre : {e}")
            continue

    df = pd.DataFrame(offres_instances).reset_index(drop=True)
    df = df.replace("", pd.NA)
    return df

def main(auth_url: str, base_url: str, output_dir: str) -> pd.DataFrame:

    logger = get_run_logger()
    logger.info("Début du pipeline de collecte France Travail")

    all_offers = []
    access_token = get_access_token(auth_url)
    headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {access_token}",
    }
    for mot_clef in MOT_CLEF_LIST:
        offers = fetch_job_offers(base_url, headers, mot_clef)
        all_offers.extend(offers)
        logger.info(f"Nombre d'offres trouvées pour '{mot_clef}': {len(offers)}")
    offres = offres_to_dataframe(all_offers)
    offres.to_csv(fspath.join(
        output_dir, "france_travail_offres_data_jobs.csv"), index=False, sep=";", encoding="utf-8")
    return offres
