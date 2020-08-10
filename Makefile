#
# fastapi-rfc7807
#

PKG_NAME    := $(shell python setup.py --name)
PKG_VERSION := $(shell python setup.py --version)

.PHONY: clean deps fmt github-tag lint test unit-test version help ci-pypi-release
.DEFAULT_GOAL := help

clean:  ## Clean up build artifacts
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage* .pytest_cache/ \
		fastapi-rfc7807/__pycache__ tests/__pycache__

deps: ## Update pinned project dependencies (requirements.txt)
	tox -e deps

fmt:  ## Automatic source code formatting
	tox -e fmt

github-tag:  ## Create and push a GitHub tag with the current version
	git tag -a ${PKG_VERSION} -m "${PKG_NAME} version ${PKG_VERSION}"
	git push -u origin ${PKG_VERSION}

lint:  ## Run linting checks on the project source code
	tox -e lint

test:  ## Run the project unit tests
	tox

version:  ## Print the package version
	@echo "${PKG_VERSION}"

help:  ## Print usage information
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort


# Needed for Jenkins CI Pipeline
unit-test: test

ci-pypi-release:
	tox -e release
