.PHONY: backend frontend install dev

# --- Backend ---
install-backend:
	cd backend && pip install -e ".[dev]"

backend:
	cd backend && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# --- Frontend ---
install-frontend:
	cd frontend && npm install

frontend:
	cd frontend && npm run dev

# --- Both ---
install: install-backend install-frontend

dev:
	@echo "Start backend and frontend in separate terminals:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make frontend"

# --- Lint ---
lint:
	cd backend && ruff check src/
	cd frontend && npm run lint

format:
	cd backend && ruff format src/
