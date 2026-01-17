# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ArchViz AI is an AI-powered architectural visualization platform that transforms DWG/DXF CAD files into photorealistic renders and interactive walkthroughs. It features an LLM-powered material selection assistant using Azure OpenAI.

**Three-Tier Architecture:**
- **Backend**: FastAPI (Python) on port 8000 - API server, DWG parsing, AI orchestration
- **Frontend**: Next.js + React (TypeScript) on port 3000 - Web UI with Three.js 3D visualization
- **Desktop**: Electron - Native app with local GPU rendering and offline mode

## Development Commands

### Quick Start
```bash
npm run setup           # Install all dependencies (Python + Node.js)
npm run dev             # Start API + Frontend concurrently
```

### Running Services
```bash
npm run dev:api         # FastAPI backend only (port 8000)
npm run dev:frontend    # Next.js frontend only (port 3000)
npm run dev:electron    # Electron in dev mode
make start              # Alternative: start all services
make stop               # Stop all services
```

### Testing
```bash
# Python tests (from project root)
pytest tests/                              # All tests
pytest tests/ -m "not integration"         # Skip integration tests (no Azure required)
pytest tests/test_chat.py -v               # Specific test file
pytest tests/ --cov=api --cov=core         # With coverage

# Test script shortcuts
./scripts/test.sh unit          # Unit tests only
./scripts/test.sh integration   # Integration tests (requires Azure)
./scripts/test.sh coverage      # Generate coverage report
./scripts/test.sh quick         # Quick smoke test
```

### Building
```bash
npm run build                   # Build frontend + electron
npm run package:mac             # Build macOS app
npm run package:win             # Build Windows app
npm run package:linux           # Build Linux app
```

### API Testing
```bash
make render-test    # Test render endpoint
make chat-test      # Test chat endpoint
```

## Architecture

```
archviz-ai/
├── api/                    # FastAPI backend
│   ├── main.py             # App initialization, router registration
│   ├── routes/             # API endpoints
│   │   ├── health.py       # Health checks, GPU status
│   │   ├── projects.py     # Project CRUD
│   │   ├── render.py       # Render job orchestration
│   │   ├── materials.py    # Material library
│   │   ├── chat.py         # LLM chat interface
│   │   └── notifications.py
│   └── services/           # Business logic
├── core/                   # Core processing modules
│   ├── dwg_parser/         # DWG/DXF parsing with ezdxf
│   │   ├── parser.py       # Main parsing logic
│   │   ├── elements.py     # Wall, Door, Window, Room models
│   │   └── converter.py    # DWG to DXF conversion
│   ├── azure/              # Azure integration
│   │   ├── config.py       # Configuration
│   │   ├── openai_service.py   # GPT-4o, DALL-E 3 client
│   │   └── storage_service.py  # Blob storage
│   ├── materials/          # Material system (planned)
│   ├── model_gen/          # 3D model generation (planned)
│   ├── render/             # AI rendering pipeline (planned)
│   └── walkthrough/        # Video/splat generation (planned)
├── frontend/               # Next.js App Router
│   └── src/
│       ├── app/            # Pages (page.tsx, layout.tsx)
│       ├── components/     # React components
│       │   ├── FloorPlan3DViewer.tsx  # Three.js visualization
│       │   ├── FileUpload.tsx
│       │   └── ProjectCard.tsx
│       ├── lib/            # API client, utilities
│       └── types/          # TypeScript definitions
├── electron/               # Desktop app
│   └── src/
│       ├── main.ts         # Main process
│       └── preload.ts      # Preload script
├── tests/                  # pytest test suite
└── scripts/                # dev.sh, test.sh, demo.sh
```

## Key Patterns

**API Layer**: Routes define endpoints, delegate to services. All routes use async/await.

**DWG Parsing Flow**: `DWGParser.parse()` → extracts architectural elements → returns `FloorPlan` with walls, doors, windows, rooms.

**Azure Integration**: `AzureOpenAIService` wraps GPT-4o for chat and DALL-E 3 for image generation. Config loaded from environment variables.

**Frontend State**: React hooks + API client (`lib/api.ts`). Three.js rendering via React Three Fiber.

## Environment Setup

Copy `.env.example` to `.env` and configure:
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` - Required for LLM/image features
- `AZURE_OPENAI_GPT4_DEPLOYMENT`, `AZURE_OPENAI_DALLE_DEPLOYMENT` - Model deployment names
- `AZURE_STORAGE_*` - Blob storage for file uploads

## Code Style

**Python**: Black (100 char), Ruff linter, mypy strict mode
**TypeScript**: ESLint via Next.js

**Test Markers**:
- `@pytest.mark.integration` - Tests requiring Azure services
- `@pytest.mark.slow` - Long-running tests

## Tech Stack Reference

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, uvicorn, ezdxf, trimesh, numpy |
| LLM/Vision | Azure OpenAI (GPT-4o, DALL-E 3) |
| Frontend | Next.js 14, React 18, Three.js, Tailwind CSS |
| Desktop | Electron 28, electron-builder |
| Testing | pytest, pytest-asyncio, pytest-cov |
