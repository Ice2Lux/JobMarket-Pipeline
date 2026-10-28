# JobMarket Pipeline

![CI](https://github.com/Ice2Lux/JobMarket-Pipeline/actions/workflows/ci.yml/badge.svg)

Pipeline ETL qui collecte chaque jour les offres d'emploi **data / IA** publiées sur
[France Travail](https://francetravail.io), les nettoie et les historise dans une table
**Delta Lake**, prête pour l'analyse du marché (contrats, salaires, compétences, localisation).

**Stack :** Python 3.11 · Prefect 3 · requests · pandas · Delta Lake (delta-rs) · pydantic-settings · pytest · Docker · GitHub Actions

## Architecture

```
API France Travail ──► extract ──► raw (JSON Lines) ──► transform ──► silver (Delta Lake)
   OAuth2, pagination           partition par jour        nettoyage,      MERGE sur id
   retries, 10 req/s            rejouable                 dédup, salaires
```

| Étape | Module | Ce qu'elle fait |
|---|---|---|
| **Extract** | `extract.py` | Authentification OAuth2 (jeton réutilisé jusqu'à expiration), pagination par fenêtres de 150 offres dans les limites de l'API (1 150 résultats max par recherche), retries automatiques sur 429/5xx, une recherche par mot-clé. |
| **Raw** | `load.py` | Sauvegarde des réponses brutes en JSON Lines, partitionnées par `date_ingestion`. Un second run le même jour relit ces fichiers au lieu de rappeler l'API. |
| **Transform** | `transform.py` | Aplatissement des objets imbriqués, colonnes en snake_case, dates typées, extraction du département, **conversion des libellés de salaire en fourchette annuelle** (annuel, mensuel ou horaire), **déduplication** des offres trouvées par plusieurs mots-clés en gardant la version la plus récente et la liste des mots-clés. |
| **Load** | `load.py` | `MERGE` dans la table Delta sur `id` : nouvelle offre insérée, offre actualisée mise à jour, offre inchangée ignorée. Le pipeline est donc **idempotent**. |
| **Orchestration** | `flow.py` | Flow Prefect avec retries sur l'extraction, logs et planification quotidienne. |

## Démarrage rapide

**1. Obtenir des identifiants.** Créez une application sur [francetravail.io](https://francetravail.io)
et abonnez-la à l'API « Offres d'emploi v2 ».

**2. Installer.**

```bash
git clone https://github.com/Ice2Lux/JobMarket-Pipeline.git
cd JobMarket-Pipeline
make install && source .venv/bin/activate
cp .env.example .env   # puis renseigner FT_CLIENT_ID et FT_CLIENT_SECRET
```

**3. Lancer.**

```bash
python -m jobmarket run       # collecte du jour (ou : make run)
python -m jobmarket report    # résumé de la table
```

Exemple de sortie de `report` :

```
Offres en base : 3
Salaire annuel médian (milieu de fourchette) : 31 200 €
Offres avec un salaire exploitable : 100%

Types de contrat
  CDD                                                2
  CDI                                                1

Compétences les plus demandées
  Python                                             2
  SQL                                                1
```

### Autres usages

```bash
python -m jobmarket run --date 2026-10-27   # rejouer une journée depuis la couche brute
python -m jobmarket run --refresh           # forcer un nouvel appel à l'API
python -m jobmarket serve --cron "0 7 * * *"  # planifier (avec un serveur Prefect : prefect server start)
```

### Avec Docker

```bash
make docker-build
make docker-run   # les données sont écrites dans ./data
```

## Configuration

Toutes les options se règlent par variables d'environnement (ou dans `.env`) :

| Variable | Défaut | Rôle |
|---|---|---|
| `FT_CLIENT_ID` / `FT_CLIENT_SECRET` | *obligatoire* | Identifiants de l'application France Travail |
| `FT_KEYWORDS` | 10 mots-clés data / IA | Liste JSON des recherches à lancer |
| `FT_DATA_DIR` | `data` | Dossier racine des données |
| `FT_REQUEST_DELAY_S` | `0.2` | Pause entre deux pages (l'API autorise 10 appels/s) |

## Données produites

```
data/
├── raw/offres/date_ingestion=2026-10-28/offres.jsonl   # réponses brutes de l'API
└── silver/offres/                                      # table Delta, une ligne par offre
```

Principales colonnes de la table : `id`, `intitule`, `date_creation`, `date_actualisation`,
`departement`, `entreprise`, `type_contrat`, `experience_exigee`, `salaire_min_annuel`,
`salaire_max_annuel`, `competences`, `mots_cles`, `date_ingestion`.

La table se lit directement avec pandas, Polars, DuckDB ou Spark :

```python
from deltalake import DeltaTable

df = DeltaTable("data/silver/offres").to_pandas()
```

## Tests et qualité

```bash
make lint   # ruff
make test   # pytest + couverture
```

Les tests n'appellent jamais la vraie API : les réponses sont simulées avec `responses`.
Ils couvrent la pagination et ses limites, la réutilisation du jeton, le parsing des salaires,
la déduplication, l'idempotence du `MERGE` Delta et un run complet du flow Prefect.
La CI GitHub Actions les exécute sur Python 3.11 et 3.12 à chaque push.

## Limites et pistes

- L'API ne renvoie que 1 150 offres par recherche. Les mots-clés larges sont donc tronqués
  (un avertissement est loggé) ; découper par département ou par date de création lèverait la limite.
- Le salaire n'est renseigné que sur une partie des offres, et les libellés libres
  (« selon profil ») ne sont pas convertis.
- Piste suivante : une couche *gold* (agrégats par semaine, région, compétence) et un tableau de bord.
