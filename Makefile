.DEFAULT_GOAL := help

COMPOSE := docker compose
REALISTIC_DIR := frontend/realistic-wis-hmi
ERP_URL := http://localhost:8000
COMMISSIONING_URL := http://localhost:8002
MQTT_HOST := localhost

.PHONY: help setup install frontend-install build build-realistic lint lint-realistic validate e2e traffic-test up down restart stop logs logs-robots health mqtt order order-realistic clean

help: ## Show available project commands
	@echo WIS Warehouse Integration Simulator
	@echo.
	@echo   setup                  Create .env, install dependencies, validate Compose
	@echo   up                     Build and start the Docker simulation stack
	@echo   down                   Stop and remove the Docker simulation stack
	@echo   restart                Rebuild and restart the Docker simulation stack
	@echo   logs                   Follow all Docker service logs
	@echo   logs-robots            Follow all four AMR simulator logs
	@echo   build-realistic       Build the realistic HMI frontend
	@echo   lint-realistic        Lint realistic HMI source
	@echo   traffic-test          Run traffic reservation and collision tests
	@echo   validate               Run frontend, Python, and Compose checks
	@echo   e2e                    Run order-flow tests against the running stack
	@echo   health                 Query the commissioning health endpoint
	@echo   mqtt                   Subscribe to robot telemetry
	@echo   order                  Create a sample ERP order
	@echo   clean                  Remove frontend build output and Python caches

setup: ## Prepare the local environment and install frontend dependencies
	@if not exist .env copy .env.example .env
	$(MAKE) frontend-install
	$(COMPOSE) config --quiet

install: setup ## Alias for setup

frontend-install: ## Install realistic HMI dependencies
	cd $(REALISTIC_DIR) && npm install

build: build-realistic ## Build the realistic HMI frontend

build-realistic: ## Create a production build of the realistic HMI frontend
	cd $(REALISTIC_DIR) && npm run build

lint: lint-realistic ## Lint the realistic HMI frontend source

lint-realistic: ## Lint realistic HMI source files
	cd $(REALISTIC_DIR) && npm run lint

validate: ## Run frontend, Python, and Compose validation
	$(MAKE) lint-realistic
	$(MAKE) build-realistic
	python -m py_compile services/robot-simulator/worker.py services/robot-simulator/simulation.py services/wms-api/app/main.py services/opcua-plc-simulator/server.py services/opcua-gateway/gateway.py services/traffic-manager/manager.py services/simulation-control/manager.py
	python -m unittest tests/test_simulation_contract.py tests/test_traffic_manager.py tests/test_simulation_control.py -v
	python -m py_compile services/integration-engine/worker.py
	$(COMPOSE) config --quiet
	cd $(REALISTIC_DIR) && npm run test:e2e

traffic-test: ## Run deterministic traffic reservation tests
	python -m unittest tests/test_traffic_manager.py -v

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
	curl --fail --silent --show-error -X POST $(ERP_URL)/api/orders -H "Content-Type: application/json" -d "{\"order_number\":\"ORD-MAKEFILE-001\",\"customer\":\"Acme Manufacturing\",\"destination_dock\":\"Dock-3\",\"items\":[{\"product_sku\":\"P100\",\"requested_qty\":1}]}"
	@echo.

order-realistic: ## Create an in-stock order for the realistic task route
	curl --fail --silent --show-error -X POST $(ERP_URL)/api/orders -H "Content-Type: application/json" -d "{\"order_number\":\"ORD-MAKEFILE-REALISTIC-001\",\"customer\":\"Acme Manufacturing\",\"destination_dock\":\"Dock-3\",\"items\":[{\"product_sku\":\"P200\",\"requested_qty\":1}]}"
	@echo.

clean: ## Remove frontend build output and Python caches
	-if exist "$(REALISTIC_DIR)\dist" rmdir /s /q "$(REALISTIC_DIR)\dist"
	-for /d /r services %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
