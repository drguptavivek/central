docker-compose-dev := docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml

.PHONY: dev
dev:
	$(docker-compose-dev) up --detach

.PHONY: dev-nond
dev-nond:
	$(docker-compose-dev) up

.PHONY: dev-logs
dev-logs:
	$(docker-compose-dev) logs --tail=50 -f

.PHONY: dev-build
dev-build:
	$(docker-compose-dev) up --detach --build

.PHONY: stop dev-stop
stop dev-stop:
	$(docker-compose-dev) stop

docker-compose-prod := docker compose -f docker-compose.yml -f docker-compose.override.yml

.PHONY: prod
prod:
	$(docker-compose-prod) up --detach

.PHONY: prod-build
prod-build:
	$(docker-compose-prod) up --detach --build

.PHONY: prod-stop
prod-stop:
	$(docker-compose-prod) stop

.PHONY: prod-nond
prod-nond:
	$(docker-compose-prod) up

.PHONY: prod-logs
prod-logs:
	$(docker-compose-prod) logs --tail=50 -f
