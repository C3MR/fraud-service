install:                      ## Editable install
	pip install -e .

run-batch:                    ## Lab 1: batch scoring
	python -m fraud_service.batch

lint:                         ## ruff check
	ruff check src tests

IMAGE := fraud-service
TAG   := $(shell git rev-parse --short HEAD)

image:                        ## Build production image tagged with git SHA
	docker build -t $(IMAGE):$(TAG) -t $(IMAGE):dev .

image-size: image             ## Report image size (course benchmark)
	docker images $(IMAGE):$(TAG) --format "{{.Repository}}:{{.Tag}} {{.Size}}"

up:                           ## Full dev stack
	docker compose up --build -d && docker compose ps

smoke: up                     ## End-to-end smoke test against the container
	sleep 2 && curl -fsS localhost:8000/v1/ready \
	&& curl -fsS localhost:8000/v1/predict -d @payloads/sample.json \
	     -H "content-type: application/json" | python -m json.tool