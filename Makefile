# Variables

SERVICE_NAME=cod-result-processor

.PHONY: build
build:
	@docker-compose build --pull

.PHONY: build-no-cache
build-no-cache:
	@docker-compose build --no-cache

.PHONY: process-results
process-results:
	@docker-compose run --user=$(shell id -u) --rm ${SERVICE_NAME} python main.py

.PHONY: shell
shell:
	@docker-compose run --rm ${SERVICE_NAME} bash
