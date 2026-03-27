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

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | Python / FastAPI | ≥3.10 (CI: 3.11) |
| **Frontend** | Next.js 14 / React 18 | Node ≥18, npm ≥9 |
| **Desktop** | Electron | separate workspace |
| **3D Rendering** | Three.js + React Three Fiber | 0.161 / 8.x |
| **State** | TanStack React Query | v5 |
| **Styling** | Tailwind CSS | v3 |
| **AI/LLM** | Azure OpenAI (GPT-4o, DALL-E 3) | openai ≥1.12 |
| **DXF parsing** | ezdxf + LibreDWG (Docker) | ezdxf ≥1.1 |
| **3D geometry** | trimesh + shapely + scipy | — |
| **Push notifications** | Firebase Admin SDK | ≥6.4 |
| **Infra** | Azure Container Apps + Bicep | `infra/` |
| **Optional GPU** | PyTorch + Diffusers + Transformers | `pip install -e ".[gpu]"` |

## Project Structure

```
archviz-ai/
├── api/                    # FastAPI application
│   ├── main.py             # App factory, middleware, router registration
│   └── routes/             # projects, render, materials, chat, notifications, room_pipeline, health
├── core/                   # Pure business logic (no FastAPI)
│   ├── azure/              # openai_service.py, storage_service.py, config.py
│   ├── dwg_parser/         # parser.py, converter.py, elements.py, room_classifier.py,
│   │                       #   spatial_utils.py, wall_graph.py
│   ├── model_gen/          # generator.py, shell_builder.py, furniture_placer.py,
│   │                       #   furniture_library.py, extruder.py, exporter.py, openings.py
│   ├── materials/          # library.py, suggester.py, fetcher.py, presets.py,
│   │                       #   texture_generator.py, types.py
│   ├── render/             # renderer.py, blender_renderer.py, batch.py,
│   │                       #   job_manager.py, prompt_builder.py, types.py
│   └── walkthrough/        # video_generator.py, camera_path.py
├── frontend/               # Next.js workspace
│   └── src/
│       ├── app/            # Next.js App Router pages
│       ├── components/     # FloorPlan3DViewer, FloorPlanViewer, FileUpload, etc.
│       ├── lib/            # api.ts, hooks.ts, firebase.ts, utils.ts
│       └── types/          # Shared TypeScript types
├── electron/               # Electron desktop app workspace
├── tests/                  # pytest suite (unit + integration + e2e + performance)
├── infra/                  # Azure Bicep templates (main.bicep, resources.bicep, deploy.sh)
├── k8s/                    # Kubernetes manifests (namespace, configmap, deployments, ingress)
├── .github/workflows/      # ci.yml (lint + test), deploy-azure.yml (Container Apps deploy)
├── Dockerfile              # Builds LibreDWG from source + Python API
├── docker-compose.yml
├── pyproject.toml          # Python deps, Black/Ruff/mypy/pytest config
└── package.json            # npm workspaces root
```

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
make test-e2e               # End-to-end tests
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
- `health.py` - Health check endpoint (`GET /health`)

**Core Services** (`core/`):
- `azure/openai_service.py` - `AzureOpenAIService` wraps GPT-4o (chat, vision) and DALL-E 3 (image gen)
- `azure/storage_service.py` - Azure Blob Storage integration for file persistence
- `azure/config.py` - Azure service configuration and credential setup
- `dwg_parser/parser.py` - `DWGParser.parse()` extracts walls, doors, windows, rooms from DXF
- `dwg_parser/converter.py` - DWG to DXF conversion via LibreDWG
- `dwg_parser/elements.py` - Domain types for parsed DWG elements (walls, doors, windows)
- `dwg_parser/room_classifier.py` - Classifies room types from geometry and context
- `dwg_parser/spatial_utils.py` - Geometric helpers (polygon area, intersection, bounding box)
- `dwg_parser/wall_graph.py` - Builds a connectivity graph of wall segments
- `model_gen/generator.py` - Orchestrates 3D scene generation from floor plans
- `model_gen/shell_builder.py` - Creates wall, floor, ceiling meshes
- `model_gen/furniture_placer.py` - GPT-4 powered furniture layout planning
- `model_gen/furniture_library.py` - Static furniture asset library and metadata
- `model_gen/extruder.py` - Extrudes 2D floor plan outlines into 3D geometry
- `model_gen/openings.py` - Cuts door/window openings into wall meshes
- `model_gen/exporter.py` - Exports 3D scenes to glTF/OBJ formats
- `materials/library.py` - Material database with PBR textures
- `materials/suggester.py` - LLM-based material recommendations
- `materials/fetcher.py` - Fetches material assets from remote sources
- `materials/presets.py` - Named style presets (e.g. Scandinavian, Industrial)
- `materials/texture_generator.py` - Procedural texture generation helpers
- `render/renderer.py` - DALL-E render pipeline
- `render/blender_renderer.py` - Blender-based high-quality rendering
- `render/batch.py` - Concurrent multi-room batch render orchestration
- `render/job_manager.py` - In-memory job lifecycle (`pending → processing → completed/failed`)
- `render/prompt_builder.py` - Constructs DALL-E prompts from room/material context
- `walkthrough/video_generator.py` - Video export from camera paths
- `walkthrough/camera_path.py` - Generates smooth camera spline paths through rooms

**Frontend** (`frontend/src/`):
- `lib/api.ts` - Typed API client with `fetchAPI<T>()` wrapper (throws on non-2xx)
- `lib/hooks.ts` - React Query hooks wrapping every API call; centralized `queryKeys` object for cache invalidation; `useBatchJob` polls every 2s while job is running
- `lib/firebase.ts` - Firebase client initialization for push notification subscription
- `components/FloorPlan3DViewer.tsx` - React Three Fiber 3D visualization
- `components/FloorPlanViewer.tsx` - 2D SVG floor plan viewer
- `components/FloorPlanMiniMap.tsx` - Minimap overlay for 3D viewer navigation
- `components/room-viewer/` - Per-room render result components
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

### React Query Hooks Pattern
All data-fetching is centralized in `frontend/src/lib/hooks.ts`. The `queryKeys` object is the single source of truth for cache keys — always use it when calling `invalidateQueries`. Mutations invalidate related queries in `onSuccess`. Example: `useUploadFile` invalidates project, floorPlan, and preview keys after upload.

### Static File Serving
FastAPI serves `uploads/` and `output/` as static directories at `/uploads` and `/output` respectively. These paths are referenced directly by frontend image URLs returned from render endpoints.

## CI/CD

**GitHub Actions** (`.github/workflows/`):

| Workflow | File | Trigger | Jobs |
|----------|------|---------|------|
| CI | `ci.yml` | push to `main`/`develop`, PRs to `main` | ruff lint, black check, frontend ESLint, pytest (non-integration) |
| Deploy | `deploy-azure.yml` | push to `main`, manual `workflow_dispatch` | Build + push Docker image, deploy to Azure Container Apps |

CI skips integration tests (no Azure creds). Deploy workflow uses `AZURE_RESOURCE_GROUP=rg-archvizai-prod`.

## Deployment

- **Azure Container Apps**: Primary deployment target via `deploy-azure.yml`; CORS already whitelisted for `.azurecontainerapps.io` domains
- **Bicep IaC**: `infra/main.bicep` + `infra/resources.bicep` define all Azure resources; `infra/deploy.sh` for manual provisioning
- **Kubernetes**: `k8s/` directory with namespace, configmap, api/frontend deployments, ingress (alternative target)
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
