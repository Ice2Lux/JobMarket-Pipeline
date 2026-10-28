"""Configuration du pipeline, lue depuis les variables d'environnement (ou un fichier .env)."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_KEYWORDS = [
    "data engineer",
    "data scientist",
    "data analyst",
    "data architect",
    "machine learning",
    "deep learning",
    "intelligence artificielle",
    "big data",
    "business intelligence",
    "data visualisation",
]


class StorageSettings(BaseSettings):
    """Emplacement des données. Suffit pour lire les tables, sans identifiants API.

    Toutes les valeurs peuvent être surchargées par une variable d'environnement
    préfixée par ``FT_`` (ex. ``FT_DATA_DIR``).
    """

    model_config = SettingsConfigDict(env_prefix="FT_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")

    @property
    def raw_dir(self) -> Path:
        """Couche bronze : réponses brutes de l'API, une partition par jour d'ingestion."""
        return self.data_dir / "raw" / "offres"

    @property
    def table_path(self) -> Path:
        """Couche silver : table Delta des offres nettoyées et dédupliquées."""
        return self.data_dir / "silver" / "offres"


class Settings(StorageSettings):
    """Paramètres complets du pipeline (``FT_CLIENT_ID``, ``FT_CLIENT_SECRET``, ``FT_KEYWORDS``…)."""

    # Identifiants de l'application créée sur https://francetravail.io
    client_id: str
    client_secret: SecretStr

    auth_url: str = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
    search_url: str = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    scope: str = "api_offresdemploiv2 o2dsoffre"

    keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_KEYWORDS))

    page_size: int = Field(default=150, ge=1, le=150)
    request_delay_s: float = Field(default=0.2, ge=0)
    timeout_s: float = 30.0
