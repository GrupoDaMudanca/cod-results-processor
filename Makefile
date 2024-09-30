# Variables

SERVICE_NAME=cod-result-processor

.PHONY: all
all: clean download-images process consolidate clean

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
	@rm -f results/*

.PHONY: consolidate
consolidate:
	@docker compose run --user=$(shell id -u) --rm ${SERVICE_NAME} python consolidate.py

.PHONY: download-images
download-images:
	@docker compose run --user=$(shell id -u) --rm ${SERVICE_NAME} python download_images.py

.PHONY: process
process:
	@docker compose run --user=$(shell id -u) --rm ${SERVICE_NAME} python main.py

.PHONY: shell
shell:
	@docker compose run --rm ${SERVICE_NAME} bash
