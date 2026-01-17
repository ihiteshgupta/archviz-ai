# ArchViz AI - Makefile
# Quick commands for local development

.PHONY: start stop restart test demo status setup logs clean help

# Default target
help:
	@echo "ArchViz AI - Development Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  start     Start backend and frontend"
	@echo "  stop      Stop all services"
	@echo "  restart   Restart all services"
	@echo "  test      Run all tests"
	@echo "  demo      Run demo workflow"
	@echo "  status    Show service status"
	@echo "  setup     Install all dependencies"
	@echo "  logs      Tail service logs"
	@echo "  clean     Clean generated files"
	@echo ""

# Start all services
start:
	@./scripts/dev.sh start

# Stop all services
stop:
	@./scripts/dev.sh stop

# Restart all services
restart:
	@./scripts/dev.sh restart

# Run all tests
test:
	@./scripts/test.sh all

# Run unit tests only
test-unit:
	@./scripts/test.sh unit

# Run integration tests
test-integration:
	@./scripts/test.sh integration

# Run E2E tests
test-e2e:
	@./scripts/test.sh e2e

# Run tests with coverage
test-coverage:
	@./scripts/test.sh coverage

# Quick smoke test
test-quick:
	@./scripts/test.sh quick

# Run demo flow
demo:
	@./scripts/demo.sh

# Show status
status:
	@./scripts/dev.sh status

# Setup dependencies
setup:
	@./scripts/dev.sh setup

# Tail logs
logs:
	@./scripts/dev.sh logs

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@rm -rf .venv __pycache__ .pytest_cache
	@rm -rf frontend/.next frontend/node_modules
	@rm -rf logs/*.log
	@rm -f .backend.pid .frontend.pid
	@echo "Clean complete"

# Backend only
backend:
	@./scripts/dev.sh backend

# Frontend only
frontend:
	@./scripts/dev.sh frontend

# Quick render test
render-test:
	@echo "Testing quick render..."
	@curl -s -X POST http://localhost:8000/api/render/quick \
		-H "Content-Type: application/json" \
		-d '{"room_type": "bedroom", "style": "scandinavian", "size": "1024x1024"}' | \
		python3 -m json.tool

# Chat test
chat-test:
	@echo "Testing chat..."
	@curl -s -X POST http://localhost:8000/api/chat/ \
		-H "Content-Type: application/json" \
		-d '{"message": "Suggest materials for a kitchen", "conversation_history": []}' | \
		python3 -m json.tool
