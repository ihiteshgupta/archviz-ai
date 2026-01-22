# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ArchViz AI transforms DWG/DXF CAD files into photorealistic renders and interactive walkthroughs using Azure OpenAI (GPT-4o + DALL-E 3). Available as web app and Electron desktop app.

**Architecture**: FastAPI (8000) ← Next.js proxy (3000) → React/Three.js UI

**Data Flow**:
```
DWG Upload → DWG→DXF Conversion → Floor Plan Parse → 3D Model Gen →
Material Selection (LLM) → DALL-E Render → Video Walkthrough
```

**Workspaces**: Monorepo with npm workspaces (`frontend/`, `electron/`) orchestrated from root `package.json`

## Development Commands

### Setup & Run
```bash
npm run setup               # Install all deps (Python + Node.js)
npm run dev                 # Start API + Frontend together (via concurrently)
npm run dev:api             # FastAPI only (port 8000)
npm run dev:frontend        # Next.js only (port 3000)
npm run dev:electron        # Electron desktop app

# Or use Makefile shortcuts
make start                  # Start backend and frontend
make backend                # Backend only
make frontend               # Frontend only
```

### Testing
```bash
# Backend (pytest)
pytest tests/                               # All tests
pytest tests/ -m "not integration"          # Skip Azure-dependent tests
pytest tests/test_chat.py::test_name -v     # Single test
pytest tests/ --cov=api --cov=core          # With coverage
pytest tests/ --cov-report=html             # HTML coverage report

# Frontend (Jest)
cd frontend && npm test                     # Run all tests
cd frontend && npm run test:watch           # Watch mode
cd frontend && npm run test:coverage        # With coverage

# Makefile shortcuts
make test                   # Run all backend tests
make test-unit              # Unit tests only
make test-integration       # Integration tests only
make test-coverage          # Tests with HTML coverage report
make test-quick             # Quick smoke test
```

### Linting & Formatting
```bash
# Python (configured in pyproject.toml)
black api/ core/            # Format Python code (100 char line length)
ruff check api/ core/       # Lint Python code
mypy api/ core/             # Type checking (strict mode)

# TypeScript
cd frontend && npm run lint # ESLint for Next.js/React
```

### Build & Package
```bash
npm run build               # Build frontend + electron
npm run build:frontend      # Next.js production build
npm run build:electron      # Electron build

# Desktop app packaging
npm run package:mac         # macOS .app bundle
npm run package:win         # Windows installer
npm run package:linux       # Linux AppImage
```

### Utility Commands
```bash
make clean                  # Remove generated files, caches
make render-test            # Test quick render endpoint
make chat-test              # Test chat endpoint
make status                 # Show service status
```

## Key Architecture

**API Routing**: Frontend calls `/api/*` → Next.js rewrites to `localhost:8000/api/*` (see `frontend/next.config.js`)

**Route Structure** (`api/routes/`):
- `projects.py` - CRUD for projects, file upload, floor plan parsing
- `render.py` - Single room renders, batch render jobs, pipeline status
- `materials.py` - Material library, categories, style presets
- `chat.py` - LLM chat with project context
- `room_pipeline.py` - Room shell generation pipeline
- `notifications.py` - Firebase push notifications

**Core Services** (`core/`):
- `azure/openai_service.py` - `AzureOpenAIService` wraps GPT-4o (chat, vision) and DALL-E 3 (image gen)
- `dwg_parser/parser.py` - `DWGParser.parse()` extracts walls, doors, windows, rooms from DXF
- `dwg_parser/converter.py` - DWG to DXF conversion via LibreDWG
- `model_gen/generator.py` - Orchestrates 3D scene generation from floor plans
- `model_gen/shell_builder.py` - Creates wall, floor, ceiling meshes
- `model_gen/furniture_placer.py` - GPT-4 powered furniture layout planning
- `materials/library.py` - Material database with PBR textures
- `materials/suggester.py` - LLM-based material recommendations
- `render/renderer.py` - DALL-E render pipeline
- `render/blender_renderer.py` - Blender-based high-quality rendering
- `walkthrough/video_generator.py` - Video export from camera paths

**Frontend** (`frontend/src/`):
- `lib/api.ts` - Typed API client with `fetchAPI<T>()` wrapper
- `components/FloorPlan3DViewer.tsx` - React Three Fiber 3D visualization
- State: React Query (`@tanstack/react-query`) for server state

**Storage**: In-memory dict for development (`PROJECTS` in `api/routes/projects.py`). Files in `uploads/` and `output/` directories.

## Environment Variables

Copy `.env.example` to `.env`:
```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4o
AZURE_OPENAI_DALLE_DEPLOYMENT=dall-e-3
AZURE_STORAGE_ACCOUNT_NAME=...  # For file uploads
```

## Code Style & Validation

### Python
- **Formatter**: Black (100 char line length)
- **Linter**: Ruff (E, F, I, N, W rules enabled)
- **Type Checker**: mypy (strict mode)
- **Config**: `pyproject.toml`

### TypeScript
- **Linter**: ESLint via Next.js defaults
- **Config**: `frontend/.eslintrc.json`

### Input Validation (Critical)
All API endpoints use Pydantic models with field validators:
- **File uploads**: Path traversal prevention via `sanitize_filename()`
- **Project names**: Non-empty, max 255 chars, trimmed
- **Resolutions**: Positive integers, max 4096
- **Render sizes**: Valid DALL-E sizes only (`1024x1024`, `1792x1024`, `1024x1792`)
- **Material categories**: Return 404 for invalid categories

See `api/routes/projects.py`, `api/routes/render.py`, `api/routes/materials.py` for examples.

### Testing Conventions
- **Test markers**: `@pytest.mark.integration` (needs Azure), `@pytest.mark.slow`
- **Coverage target**: >80% for API routes, >70% for core modules
- **Frontend**: Jest with React Testing Library
- **Test files**: Follow `test_*.py` pattern, classes `Test*`, functions `test_*`

## Hardware Requirements (GPU Features)

| Stage | Minimum | Recommended |
|-------|---------|-------------|
| DWG Parsing | CPU only | - |
| 3D Generation | 6GB VRAM | 16GB VRAM |
| Rendering | 12GB VRAM | 24GB VRAM |
| Video Gen | 16GB VRAM | 24GB VRAM |

## Important Implementation Details

### Request/Response Flow
1. Frontend makes request to `/api/*`
2. Next.js proxy rewrites to `localhost:8000/api/*` (see `frontend/next.config.js`)
3. FastAPI handles request, returns JSON
4. Frontend uses typed `fetchAPI<T>()` wrapper from `lib/api.ts`
5. React Query manages server state caching

### State Management
- **Server state**: React Query (`@tanstack/react-query`)
- **Client state**: React hooks (useState, useContext)
- **3D viewer**: React Three Fiber with imperative refs

### In-Memory Storage (Development)
Projects stored in `PROJECTS` dict in `api/routes/projects.py`. Files saved to:
- `uploads/{project_id}/` - Uploaded DWG/DXF files
- `output/{job_id}/` - Render outputs

**Note**: No database in MVP. Production will use PostgreSQL + Redis.

### Azure OpenAI Integration
Lazy-loaded services (only initialized when needed):
- `get_dalle_service()` - DALL-E 3 image generation
- `get_openai_service()` - GPT-4o chat completions
- Graceful fallback when Azure not configured (returns 503)

### Render Pipeline Architecture
Two render modes:
1. **Quick render** (`/api/render/quick`) - Direct DALL-E 3 generation
2. **Batch pipeline** (`/api/render/batch`) - Multi-room concurrent rendering with job tracking

Job manager tracks: `pending → processing → completed/failed`

### DWG/DXF Parsing
LibreDWG compiles from source in Docker for native DWG support. Falls back to ezdxf for DXF-only parsing.

## Deployment

- **Kubernetes**: `k8s/` directory with namespace, configmap, api/frontend deployments
- **Azure Container Apps**: Configured via GitHub Actions (`.github/workflows/`)
- Build outputs: `frontend/.next/standalone` (Next.js standalone mode)
- **Docker**: `Dockerfile` builds LibreDWG from source for native DWG parsing

## Known Issues & Gotchas

1. **Batch render timeout**: `test_batch_many_rooms` times out in CI with large batches - use smaller batch sizes in production
2. **Firebase notifications**: Currently low coverage (28%) - integration tests needed
3. **Electron desktop app**: Separate workspace, development in progress
4. **GPU requirements**: Some features require CUDA (12GB+ VRAM for rendering)

## Documentation

- **Test Plan**: `docs/TEST_PLAN.md` - Comprehensive QA document
- **Test Execution Report**: `docs/TEST_EXECUTION_REPORT.md` - Latest test run results
- **Architecture**: See README.md for high-level pipeline diagram
