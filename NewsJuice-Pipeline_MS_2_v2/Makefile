.PHONY: run build scrape load retrieve up-proxy down clean rebuild

run: build up-proxy load retrieve  ## Build images, start proxy, run both steps
	@echo "✅ Pipeline finished."

build:
	docker compose build

up-proxy:
	docker compose up -d dbproxy

scrape:
	mkdir -p artifacts
	docker compose run --rm scraper

load:
	docker compose run --rm loader

retrieve:
	docker compose run --rm retriever

down:
	docker compose down

clean: down
	@echo "💥 (kept artifacts/. Delete manually if you want a fresh file)"