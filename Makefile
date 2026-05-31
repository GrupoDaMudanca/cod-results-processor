# Variables

SERVICE_NAME=cod-result-processor

.PHONY: up
up:
	@docker compose up

.PHONY: up-silent
up-silent:
	@docker compose up -d

.PHONY: down
down:
	@docker compose down

.PHONY: build
build:
	@docker compose build --pull

.PHONY: build-no-cache
build-no-cache:
	@docker compose build --no-cache

.PHONY: clean
clean: clean-processed-temp clean-results

.PHONY: clean-processed-temp
clean-processed-temp:
	@rm -f processed/temp/*

.PHONY: clean-results
clean-results:
	@rm -f results/*.jpg results/*.jpeg results/*.meta.json

.PHONY: shell
shell:
	@docker compose run --rm ${SERVICE_NAME} bash
