#!/bin/bash
# ArchViz AI - Local Development Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_dependencies() {
    log_info "Checking dependencies..."

    # Check for uv or pip
    if command -v uv &> /dev/null; then
        PIP_CMD="uv pip"
        log_success "Using uv for Python package management"
    elif command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        log_warn "Using pip3 (uv recommended for faster installs)"
    else
        log_error "Neither uv nor pip3 found. Please install Python."
        exit 1
    fi

    # Check for Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found. Please install Node.js 18+."
        exit 1
    fi

    # Check for npm
    if ! command -v npm &> /dev/null; then
        log_error "npm not found. Please install npm."
        exit 1
    fi

    log_success "All dependencies found"
}

setup_backend() {
    log_info "Setting up backend..."

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        if command -v uv &> /dev/null; then
            uv venv --python 3.11
        else
            python3 -m venv .venv
        fi
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Install dependencies
    log_info "Installing Python dependencies..."
    $PIP_CMD install -e . > /dev/null 2>&1

    log_success "Backend setup complete"
}

setup_frontend() {
    log_info "Setting up frontend..."

    cd "$PROJECT_ROOT/frontend"

    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install > /dev/null 2>&1
    fi

    # Create .env.local if it doesn't exist
    if [ ! -f ".env.local" ]; then
        echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
        log_info "Created .env.local"
    fi

    cd "$PROJECT_ROOT"
    log_success "Frontend setup complete"
}

start_backend() {
    log_info "Starting backend API on port 8000..."

    source .venv/bin/activate

    # Kill existing process on port 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true

    # Start backend in background
    cd "$PROJECT_ROOT"
    nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > .backend.pid

    # Wait for backend to start
    sleep 3

    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Backend started (PID: $BACKEND_PID)"
    else
        log_error "Backend failed to start. Check logs/backend.log"
        exit 1
    fi
}

start_frontend() {
    log_info "Starting frontend on port 3000..."

    # Kill existing process on port 3000
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true

    cd "$PROJECT_ROOT/frontend"
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../.frontend.pid

    # Wait for frontend to start
    sleep 5

    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_success "Frontend started (PID: $FRONTEND_PID)"
    else
        log_error "Frontend failed to start. Check logs/frontend.log"
        exit 1
    fi

    cd "$PROJECT_ROOT"
}

stop_services() {
    log_info "Stopping services..."

    # Stop backend
    if [ -f ".backend.pid" ]; then
        kill $(cat .backend.pid) 2>/dev/null || true
        rm .backend.pid
    fi
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true

    # Stop frontend
    if [ -f ".frontend.pid" ]; then
        kill $(cat .frontend.pid) 2>/dev/null || true
        rm .frontend.pid
    fi
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true

    log_success "Services stopped"
}

run_tests() {
    log_info "Running tests..."

    source .venv/bin/activate

    # Install pytest if needed
    $PIP_CMD install pytest pytest-asyncio > /dev/null 2>&1

    # Run tests
    python -m pytest tests/ -v

    log_success "Tests complete"
}

show_status() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}       ArchViz AI - Status${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Check backend
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "Backend:  ${GREEN}Running${NC} (http://localhost:8000)"
        echo -e "API Docs: ${GREEN}Available${NC} (http://localhost:8000/docs)"
    else
        echo -e "Backend:  ${RED}Not Running${NC}"
    fi

    # Check frontend
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "Frontend: ${GREEN}Running${NC} (http://localhost:3000)"
    else
        echo -e "Frontend: ${RED}Not Running${NC}"
    fi

    # Check Azure services
    CHAT_STATUS=$(curl -s http://localhost:8000/api/chat/status 2>/dev/null || echo '{}')
    if echo "$CHAT_STATUS" | grep -q '"available":true'; then
        echo -e "Azure AI: ${GREEN}Connected${NC} (GPT-4o + DALL-E 3)"
    else
        echo -e "Azure AI: ${YELLOW}Not Configured${NC}"
    fi

    echo -e "${BLUE}========================================${NC}"
    echo ""
}

show_help() {
    echo "ArchViz AI - Local Development Script"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start     Start both backend and frontend"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  backend   Start only backend"
    echo "  frontend  Start only frontend"
    echo "  test      Run tests"
    echo "  status    Show service status"
    echo "  setup     Install dependencies only"
    echo "  logs      Tail logs"
    echo "  help      Show this help"
    echo ""
}

tail_logs() {
    log_info "Tailing logs (Ctrl+C to exit)..."
    tail -f logs/backend.log logs/frontend.log 2>/dev/null || log_warn "No logs found"
}

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Main command handler
case "${1:-start}" in
    start)
        check_dependencies
        setup_backend
        setup_frontend
        start_backend
        start_frontend
        show_status
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        check_dependencies
        start_backend
        start_frontend
        show_status
        ;;
    backend)
        check_dependencies
        setup_backend
        start_backend
        ;;
    frontend)
        check_dependencies
        setup_frontend
        start_frontend
        ;;
    test)
        check_dependencies
        setup_backend
        run_tests
        ;;
    status)
        show_status
        ;;
    setup)
        check_dependencies
        setup_backend
        setup_frontend
        log_success "Setup complete"
        ;;
    logs)
        tail_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
