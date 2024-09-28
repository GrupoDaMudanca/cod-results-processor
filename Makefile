# Variables

SERVICE_NAME=cod-result-processor

.PHONY: all
all: process consolidate

.PHONY: build
build:
	@docker compose build --pull

.PHONY: build-no-cache
build-no-cache:
	@docker compose build --no-cache

.PHONY: consolidate
consolidate:
	@docker compose run --user=$(shell id -u) --rm ${SERVICE_NAME} python consolidate.py

.PHONY: process
process:
	@docker compose run --user=$(shell id -u) --rm ${SERVICE_NAME} python main.py

.PHONY: shell
shell:
	@docker compose run --rm ${SERVICE_NAME} bash
