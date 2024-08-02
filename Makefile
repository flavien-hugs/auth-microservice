ifneq (,$(wildcard .env))
    include .env
    export
endif

.PHONY: help
help:	## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: startapp
startapp: ## Run service
	poetry run app

.PHONY: pre-commit
pre-commit: ## Run pre-commit
	pre-commit run --all-files

.PHONY: run-up
run-up: ## Docker run
	docker compose up

.PHONY: logs
logs:	## View logs from one/all containers
	docker compose logs -f $(s)

.PHONY: down
down:	## Stop the services, remove containers and networks
	docker compose down

.PHONY: tests
tests: ## Execute test
	poetry run coverage run -m pytest -vvv tests

.PHONY: coverage
coverage: ## Execute coverage
	poetry run coverage report -m
