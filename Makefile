.PHONY: up server dashboard test

up: ## Start FastAPI server + dashboard concurrently
	@echo "Starting x402 Mission Control..."
	@trap 'kill 0' EXIT; \
	  uvicorn app.main:app --host 0.0.0.0 --port 8402 --reload 2>&1 | sed 's/^/[server] /' & \
	  cd dashboard && pnpm dev 2>&1 | sed 's/^/[dashboard] /' & \
	  wait

server: ## Start FastAPI server only
	uvicorn app.main:app --host 0.0.0.0 --port 8402 --reload

dashboard: ## Start dashboard dev server only
	cd dashboard && pnpm dev

test: ## Run all tests
	cd dashboard && pnpm vitest run
	pytest -v
