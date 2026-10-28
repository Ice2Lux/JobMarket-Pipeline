.PHONY: help install lint test run report docker-build docker-run clean

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Crée le venv et installe le projet avec les outils de dev
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

lint:  ## Vérifie le style et la qualité du code
	ruff check .
	ruff format --check .

test:  ## Lance les tests avec la couverture
	pytest --cov --cov-report=term-missing

run:  ## Exécute le pipeline une fois
	python -m jobmarket run

report:  ## Résume le contenu de la table des offres
	python -m jobmarket report

docker-build:  ## Construit l'image Docker
	docker build -t jobmarket-pipeline .

docker-run:  ## Exécute le pipeline dans Docker (données dans ./data)
	docker run --rm --env-file .env -v "$(PWD)/data:/data" jobmarket-pipeline run

clean:  ## Supprime les fichiers générés
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build
