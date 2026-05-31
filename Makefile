# Variables

SERVICE_NAME=cod-result-processor

# You can override these variables when calling make.
# Example: make push REGISTRY=docker.io/youruser IMAGE_TAG=v1.0
REGISTRY ?= your_dockerhub_username
IMAGE_TAG ?= latest
IMAGE_ARCH ?= linux/amd64

# If REGISTRY is set, prefix the image name. Otherwise, use just the service name.
FULL_IMAGE_NAME = $(if $(REGISTRY),$(REGISTRY)/$(SERVICE_NAME):$(IMAGE_TAG),$(SERVICE_NAME):$(IMAGE_TAG))

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

.PHONY: push
push:
	@docker build --platform ${IMAGE_ARCH} --pull -t ${FULL_IMAGE_NAME} .
	@docker push ${FULL_IMAGE_NAME}
