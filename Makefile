# Development tasks. Everything runs through Poetry
# (https://python-poetry.org/docs/#installation).

EXAMPLE := examples/local
PULUMI := PULUMI_CONFIG_PASSPHRASE= poetry run pulumi -C $(EXAMPLE)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Install dependencies
	poetry install

.PHONY: lint
lint: ## Lint and check formatting
	poetry run ruff check .
	poetry run ruff format --check .

.PHONY: format
format: ## Auto-fix lint and format
	poetry run ruff check --fix .
	poetry run ruff format .

.PHONY: types
types: ## Type-check with mypy
	poetry run mypy pltui

.PHONY: metadata
metadata: ## Validate pyproject.toml and the lock file
	poetry check --strict

.PHONY: check
check: metadata lint types ## Everything CI checks on a pull request

.PHONY: example-init
example-init: ## Create the example stacks with sample state
	mkdir -p $(EXAMPLE)/.pulumi-state
	@for stack in dev sandbox; do \
		$(PULUMI) stack select --create $$stack && $(PULUMI) up --yes || exit 1; \
	done

.PHONY: run
run: ## Run pltui against the example project
	PULUMI_CONFIG_PASSPHRASE= poetry run pltui -C $(EXAMPLE)

.PHONY: example-clean
example-clean: ## Remove the example project's local state
	rm -rf $(EXAMPLE)/.pulumi-state $(EXAMPLE)/.pulumi-home $(EXAMPLE)/Pulumi.*.yaml

.PHONY: build
build: ## Build the wheel and sdist
	poetry build

.PHONY: clean
clean: ## Remove build and tool artefacts
	rm -rf dist build .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
