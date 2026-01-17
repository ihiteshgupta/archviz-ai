#!/bin/bash
# ArchViz AI - Test Runner Script

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[TEST]${NC} $1"; }
success() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

show_help() {
    echo "ArchViz AI - Test Runner"
    echo ""
    echo "Usage: ./scripts/test.sh [command]"
    echo ""
    echo "Commands:"
    echo "  all         Run all tests (default)"
    echo "  unit        Run unit tests only"
    echo "  integration Run integration tests (requires Azure)"
    echo "  api         Run API endpoint tests"
    echo "  chat        Run chat tests"
    echo "  render      Run render tests"
    echo "  e2e         Run end-to-end tests"
    echo "  coverage    Run tests with coverage report"
    echo "  quick       Run quick smoke tests"
    echo "  help        Show this help"
    echo ""
}

# Activate virtual environment
activate_venv() {
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        log "Creating virtual environment..."
        uv venv --python 3.11 2>/dev/null || python3 -m venv .venv
        source .venv/bin/activate
    fi
}

# Install test dependencies
install_deps() {
    log "Installing test dependencies..."
    uv pip install pytest pytest-asyncio pytest-cov httpx 2>/dev/null || \
        pip install pytest pytest-asyncio pytest-cov httpx
}

# Run all tests
run_all() {
    log "Running all tests..."
    python -m pytest tests/ -v --tb=short
}

# Run unit tests (excluding integration)
run_unit() {
    log "Running unit tests..."
    python -m pytest tests/ -v --tb=short -m "not integration"
}

# Run integration tests
run_integration() {
    log "Running integration tests..."
    warn "Integration tests require Azure OpenAI to be configured"
    python -m pytest tests/ -v --tb=short -m "integration"
}

# Run API tests
run_api() {
    log "Running API endpoint tests..."
    python -m pytest tests/test_api.py tests/test_projects.py tests/test_materials.py tests/test_render.py -v --tb=short
}

# Run chat tests
run_chat() {
    log "Running chat tests..."
    python -m pytest tests/test_chat.py -v --tb=short
}

# Run render tests
run_render() {
    log "Running render tests..."
    python -m pytest tests/test_render.py tests/test_dalle_integration.py -v --tb=short
}

# Run E2E tests
run_e2e() {
    log "Running end-to-end tests..."
    python -m pytest tests/test_e2e_workflow.py -v --tb=short
}

# Run with coverage
run_coverage() {
    log "Running tests with coverage..."
    python -m pytest tests/ -v --cov=api --cov=core --cov-report=term-missing --cov-report=html
    success "Coverage report generated: htmlcov/index.html"
}

# Quick smoke tests
run_quick() {
    log "Running quick smoke tests..."
    python -m pytest tests/test_api.py -v --tb=short -x
}

# Main
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ArchViz AI - Test Runner            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

activate_venv
install_deps

case "${1:-all}" in
    all)
        run_all
        ;;
    unit)
        run_unit
        ;;
    integration)
        run_integration
        ;;
    api)
        run_api
        ;;
    chat)
        run_chat
        ;;
    render)
        run_render
        ;;
    e2e)
        run_e2e
        ;;
    coverage)
        run_coverage
        ;;
    quick)
        run_quick
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        fail "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

echo ""
success "Test run complete!"
