.DEFAULT_GOAL := help

COMPOSE := docker compose
V2_DIR := frontend/wis-digital-Twin-v2
ERP_URL := http://localhost:8000
COMMISSIONING_URL := http://localhost:8002
MQTT_HOST := localhost

.PHONY: help setup install frontend-install build build-v2 lint lint-v2 validate e2e up down restart stop logs logs-robots health mqtt order clean

help: ## Show available project commands
	@echo WIS Warehouse Integration Simulator
	@echo.
	@echo   setup                  Create .env, install dependencies, validate Compose
	@echo   up                     Build and start the Docker simulation stack
	@echo   down                   Stop and remove the Docker simulation stack
	@echo   restart                Rebuild and restart the Docker simulation stack
	@echo   logs                   Follow all Docker service logs
	@echo   logs-robots            Follow all four AMR simulator logs
	@echo   build-v2               Build the v2 frontend
	@echo   lint-v2                Lint authored v2 source
	@echo   validate               Run frontend, Python, and Compose checks
	@echo   e2e                    Run order-flow tests against the running stack
	@echo   health                 Query the commissioning health endpoint
	@echo   mqtt                   Subscribe to robot telemetry
	@echo   order                  Create a sample ERP order
	@echo   clean                  Remove v2 build output and Python caches

setup: ## Prepare the local environment and install v2 frontend dependencies
	@if not exist .env copy .env.example .env
	$(MAKE) frontend-install
	$(COMPOSE) config --quiet

install: setup ## Alias for setup

frontend-install: ## Install v2 frontend dependencies
	cd $(V2_DIR) && npm install

build: build-v2 ## Build the v2 frontend

build-v2: ## Create a production build of the v2 frontend
	cd $(V2_DIR) && npm run build

lint: lint-v2 ## Lint the v2 frontend source

lint-v2: ## Lint authored v2 source files
	cd $(V2_DIR) && npx oxlint src

validate: ## Run frontend, Python, and Compose validation
	$(MAKE) lint-v2
	$(MAKE) build-v2
	python -m py_compile services/robot-simulator/worker.py
	$(COMPOSE) config --quiet

e2e: ## Run order-flow tests against the running stack
	python -m unittest discover -s tests -p "test_*.py" -v

up: ## Start the complete Docker simulation stack
	$(COMPOSE) up -d --build

up-infra: ## Start Docker services without the frontend
	$(COMPOSE) up -d --build

down: ## Stop and remove the Docker simulation stack
	$(COMPOSE) down

stop: down ## Alias for down

restart: ## Restart the Docker simulation stack
	$(COMPOSE) down
	$(COMPOSE) up -d --build

logs: ## Follow logs from all Docker services
	$(COMPOSE) logs -f

logs-robots: ## Follow logs from all four AMR simulators
	$(COMPOSE) logs -f robot-simulator robot-simulator-02 robot-simulator-03 robot-simulator-04

health: ## Query the commissioning health endpoint
	curl --fail --silent --show-error $(COMMISSIONING_URL)/api/health-check
	@echo.

mqtt: ## Subscribe to live robot telemetry; requires mosquitto_sub
	mosquitto_sub -h $(MQTT_HOST) -p 1883 -t warehouse/robot/state -v

order: ## Create a sample ERP order and trigger the integration flow
	curl --fail --silent --show-error -X POST $(ERP_URL)/api/orders -H "Content-Type: application/json" -d "{\"order_number\":\"ORD-MAKEFILE-001\",\"customer\":\"Toyota\",\"destination_dock\":\"Dock-3\",\"items\":[{\"product_sku\":\"P100\",\"requested_qty\":1}]}"
	@echo.

clean: ## Remove frontend build output and Python caches
	-if exist "$(V2_DIR)\dist" rmdir /s /q "$(V2_DIR)\dist"
	-for /d /r services %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
