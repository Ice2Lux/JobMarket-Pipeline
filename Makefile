SHELL = /bin/bash
.PHONY: all update test generate coverage cov reports clean-reports deploy-model deploy-docs-model docs clean distclean

all: info

info:  ## Show this infomation
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

PYTHON_VERSION=3.10

REPORT_OUTPUT_DIR = ./target/report
DOCUMENT_OUTPUT_DIR = ./doc/_build
MODEL_FOLDER = model

venv:  ## Create virtualenv by Conda
	. ./ensure_conda && conda create -yq -p venv python=$(PYTHON_VERSION)
	cp -f pip.conf venv/pip.conf
	cp -f pip.conf venv/pip.ini
	. ./activate_venv && \
		python -m pip install -U -q -c constraints.txt pip && \
		pip install -U -q -c constraints.txt -e . -r requirements-dev.txt
	. ./activate_venv && azfr-spark-install-all

update: venv  ## Update dependencies
	cp -f pip.conf venv/pip.conf
	cp -f pip.conf venv/pip.ini
	. ./activate_venv && pip install -U -q -c constraints.txt -e . -r requirements-dev.txt
	. ./activate_venv && azfr-spark-install-all

test: venv  ## Run tests
	. ./activate_venv && pytest $(PYTEST_OPTIONS)

coverage: venv  ## Run tests and compute test coverage
	. ./activate_venv && \
		coverage run -m pytest --durations=0 $(PYTEST_OPTIONS) && \
		coverage report

cov: coverage

reports: clean-reports  ## Create coverage report
	. ./activate_venv && \
		coverage run -m pytest \
			--durations=0 \
			--html=$(REPORT_OUTPUT_DIR)/test/pytests.html --self-contained-html \
			--junitxml=$(REPORT_OUTPUT_DIR)/test/junit.xml $(PYTEST_OPTIONS) && \
		coverage html -d $(REPORT_OUTPUT_DIR)/coverage_html && \
		coverage xml -o $(REPORT_OUTPUT_DIR)/coverage.xml

clean-reports:  ## Clean reports
	rm -rf $(REPORT_OUTPUT_DIR)

docs: venv clean-docs  ## Generate API documents
	. ./activate_venv && \
		sphinx-apidoc -T -M --separate -o docs src && \
		$(MAKE) -C docs html

clean-docs:  ## Clean API documents
	rm -rf $(DOCUMENT_OUTPUT_DIR)

deploy: venv  ## Deploy library packages
	. ./activate_venv && \
		pip install -q twine wheel && \
		python setup.py sdist bdist_wheel && \
		twine upload \
			--repository-url $(PYPI_REPO_URL) \
			--username $(PYPI_REPO_USER) \
			--password $(PYPI_REPO_PASS) \
			dist/*

deploy-docs: docs  ## Deploy API documents
	. ./activate_venv && \
		azfr-document-deploy \
			-i docs/_build/html \
			-o $(DOC_REPO_ROOT) \
			-n `python setup.py --name` \
			-u $(DOC_REPO_USER) \
			-p $(DOC_REPO_PASS) \
			-c /etc/ssl/certs/ca-certificates.crt

clean: clean-reports clean-docs  ## Clean artifacts and temporary files
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	rm -rf .coverage

distclean: clean  ## Clean all files including virtualenv
	rm -rf .pytest_cache .tox .eggs ./src/*.egg-info build dist
	rm -rf venv
