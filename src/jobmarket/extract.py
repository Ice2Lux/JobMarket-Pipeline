"""Extraction des offres d'emploi depuis l'API Offres d'emploi v2 de France Travail."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Limites de pagination imposées par l'API : l'index de début ne peut pas dépasser 1000,
# l'index de fin ne peut pas dépasser 1149. Une recherche renvoie donc au plus 1150 offres.
MAX_RANGE_START = 1000
MAX_RANGE_END = 1149

_CONTENT_RANGE = re.compile(r"(\d+)-(\d+)/(\d+)")


def build_session() -> requests.Session:
    """Session HTTP qui réessaie automatiquement sur 429 et erreurs 5xx (en respectant Retry-After)."""
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["Accept"] = "application/json"
    return session


class FranceTravailClient:
    """Client minimal de l'API Offres d'emploi, avec gestion du jeton OAuth2."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_url: str,
        search_url: str,
        scope: str,
        *,
        page_size: int = 150,
        request_delay_s: float = 0.2,
        timeout_s: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self.auth_url = auth_url
        self.search_url = search_url
        self.scope = scope
        self.page_size = page_size
        self.request_delay_s = request_delay_s
        self.timeout_s = timeout_s
        self.session = session or build_session()
        self._token: str | None = None
        self._token_expires_at = 0.0

    # --- Authentification -------------------------------------------------

    def _get_token(self) -> str:
        # Le jeton est réutilisé jusqu'à 60 s avant son expiration.
        if self._token and time.monotonic() < self._token_expires_at - 60:
            return self._token

        response = self.session.post(
            self.auth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": self.scope,
            },
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.monotonic() + float(payload.get("expires_in", 1500))
        logger.info("Jeton d'accès obtenu")
        return self._token

    # --- Recherche --------------------------------------------------------

    def iter_offers(self, keyword: str) -> Iterator[dict[str, Any]]:
        """Parcourt toutes les pages de résultats pour un mot-clé."""
        start, skip = 0, 0
        while True:
            end = min(start + self.page_size - 1, MAX_RANGE_END)
            response = self.session.get(
                self.search_url,
                headers={"Authorization": f"Bearer {self._get_token()}"},
                params={"motsCles": keyword, "range": f"{start}-{end}", "sort": 1},
                timeout=self.timeout_s,
            )

            # 204 : aucun résultat pour cette recherche.
            if response.status_code == 204:
                return
            response.raise_for_status()  # 200 (dernière page) ou 206 (contenu partiel)

            results = response.json().get("resultats") or []
            yield from results[skip:]

            total = _parse_total(response.headers.get("Content-Range"))
            if start == 0 and total is not None and total > MAX_RANGE_END + 1:
                logger.warning(
                    "'%s' : %d offres trouvées, l'API n'en expose que %d. "
                    "Affiner la recherche (département, dates) pour tout récupérer.",
                    keyword,
                    total,
                    MAX_RANGE_END + 1,
                )

            last_page = len(results) < (end - start + 1) or (total is not None and end + 1 >= total)
            if last_page or end >= MAX_RANGE_END:
                return

            # Page suivante. Si son début dépasse la limite de l'API, on redemande la dernière
            # fenêtre autorisée et on saute les offres déjà renvoyées.
            start, skip = end + 1, 0
            if start > MAX_RANGE_START:
                start, skip = MAX_RANGE_START, start - MAX_RANGE_START
            time.sleep(self.request_delay_s)  # l'API limite à 10 appels par seconde

    def search(self, keywords: list[str]) -> list[dict[str, Any]]:
        """Récupère les offres pour chaque mot-clé et note le mot-clé qui a remonté l'offre."""
        records: list[dict[str, Any]] = []
        for keyword in keywords:
            offers = list(self.iter_offers(keyword))
            logger.info("'%s' : %d offres", keyword, len(offers))
            records.extend({**offer, "_mot_cle": keyword} for offer in offers)
        return records


def _parse_total(content_range: str | None) -> int | None:
    """Extrait le nombre total de résultats d'un en-tête du type ``offres 0-149/2345``."""
    if not content_range:
        return None
    match = _CONTENT_RANGE.search(content_range)
    return int(match.group(3)) if match else None
