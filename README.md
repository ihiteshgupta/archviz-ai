# ArchViz AI

> AI-powered architectural visualization pipeline: DWG to renders to walkthroughs with LLM-guided material selection

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Project Board](https://img.shields.io/badge/Project-Roadmap-green)](https://github.com/users/ihiteshgupta/projects/3)

## Overview

ArchViz AI is an end-to-end platform that transforms architectural CAD files (DWG/DXF) into photorealistic renders and interactive walkthroughs using AI. The system features an LLM-powered material selection assistant that guides architects through texture and material choices.

**Available as both Web App and Desktop App (Electron)** for offline local rendering.

### Key Features

- **Native DWG Support**: Direct parsing of AutoCAD files without manual export
- **AI Rendering**: ControlNet + SDXL/Flux for photorealistic architectural renders
- **LLM Material Assistant**: Conversational interface for material and texture selection
- **PBR Texture Generation**: AI-generated physically-based rendering textures
- **3D Walkthroughs**: Gaussian Splatting for real-time navigable scenes
- **Video Export**: Smooth walkthrough videos with camera path control
- **Desktop App**: Native Electron app with offline rendering and local GPU support

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ARCHVIZ AI PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────────┐ │
│  │  DWG     │───▶│  Floor Plan  │───▶│  3D Model   │───▶│  Textured      │ │
│  │  Input   │    │  Extraction  │    │  Generation │    │  Scene         │ │
│  └──────────┘    └──────────────┘    └─────────────┘    └────────────────┘ │
│                                              │                    │         │
│                                              ▼                    ▼         │
│                                     ┌─────────────┐    ┌────────────────┐  │
│                                     │  LLM Chat   │───▶│  Material &    │  │
│                                     │  Assistant  │    │  Texture Gen   │  │
│                                     └─────────────┘    └────────────────┘  │
│                                                                  │         │
│                          ┌───────────────────────────────────────┘         │
│                          ▼                                                  │
│               ┌────────────────┐    ┌────────────────┐                     │
│               │  AI Renders    │───▶│  Walkthrough   │                     │
│               │  (Multi-view)  │    │  Video Gen     │                     │
│               └────────────────┘    └────────────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DESKTOP APP (ELECTRON)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Native file system access for DWG files                                  │
│  • Local GPU rendering (no upload required)                                 │
│  • File watching for auto-reload from CAD software                          │
│  • Offline mode with cached AI models                                       │
│  • macOS, Windows, Linux support                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| DWG Parsing | ezdxf, ODA File Converter, LibreDWG |
| 3D Generation | CadQuery, Blender Python API, Hunyuan3D |
| LLM Assistant | Claude API, GPT-4 |
| Texture Generation | SDXL, CHORD, ArmorLab |
| Rendering | ComfyUI, ControlNet++, Flux.1 |
| Walkthroughs | Gaussian Splatting, Stable Video Diffusion |
| Frontend | Next.js, Three.js, React Three Fiber |
| Desktop | Electron, electron-builder |
| Backend | FastAPI, Redis, PostgreSQL |

## Roadmap

### Phase 1: Core Pipeline
- [#1](../../issues/1) DWG/DXF Parser Module
- [#2](../../issues/2) 3D Model Generation from Floor Plan
- [#3](../../issues/3) Single-View ControlNet Render Pipeline
- [#4](../../issues/4) Web Interface MVP
- [#17](../../issues/17) **Electron Desktop Application** 🖥️

### Phase 2: Material System
- [#5](../../issues/5) LLM Material Recommendation Engine
- [#6](../../issues/6) PBR Texture Generation Pipeline
- [#7](../../issues/7) Material Library & Presets
- [#8](../../issues/8) Material Application to 3D Model

### Phase 3: Walkthrough
- [#9](../../issues/9) Multi-View Render Generation
- [#10](../../issues/10) Gaussian Splatting Integration
- [#11](../../issues/11) Video Walkthrough Generation
- [#12](../../issues/12) Web-Based 3D Viewer

### Phase 4: Scale
- [#13](../../issues/13) Batch Processing & Queue System
- [#14](../../issues/14) API for External Integrations
- [#15](../../issues/15) Custom Style Training (LoRA)
- [#16](../../issues/16) White-Label Solution for Firms

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- CUDA-capable GPU (12GB+ VRAM recommended)
- ODA File Converter (for DWG support)

### Installation

```bash
# Clone the repository
git clone https://github.com/ihiteshgupta/archviz-ai.git
cd archviz-ai

# Install all dependencies (Python + Node.js)
npm run setup

# Or install separately:
pip install -e .                    # Python dependencies
cd frontend && npm install          # Frontend dependencies
cd ../electron && npm install       # Desktop app dependencies
```

### Quick Start (Web)

```bash
# Start both API and frontend concurrently
npm run dev

# Or start separately:
npm run dev:api       # Start FastAPI backend (port 8000)
npm run dev:frontend  # Start Next.js frontend (port 3000)
```

Then open http://localhost:3000 in your browser.

### Quick Start (Desktop)

```bash
# Install Electron dependencies
cd electron && npm install

# Run in development mode
npm run dev

# Build for production
npm run build
npm run package:mac   # For macOS
npm run package:win   # For Windows
npm run package:linux # For Linux
```

## Project Structure

```
archviz-ai/
├── api/                    # FastAPI backend
│   ├── routes/             # API route handlers
│   │   ├── health.py       # Health check endpoints
│   │   ├── projects.py     # Project management
│   │   ├── render.py       # Render job management
│   │   └── materials.py    # Material library & presets
│   └── main.py             # FastAPI application
├── core/                   # Core processing modules
│   ├── dwg_parser/         # DWG/DXF parsing
│   │   ├── elements.py     # Architectural element models
│   │   ├── converter.py    # DWG to DXF conversion
│   │   └── parser.py       # Main parsing logic
│   ├── model_gen/          # 3D model generation (planned)
│   ├── materials/          # Material system (planned)
│   ├── render/             # AI rendering pipeline (planned)
│   └── walkthrough/        # Video/splat generation (planned)
├── frontend/               # Next.js web app
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   ├── components/     # React components
│   │   │   ├── FileUpload.tsx
│   │   │   ├── FloorPlanViewer.tsx
│   │   │   ├── FloorPlan3DViewer.tsx
│   │   │   └── ProjectCard.tsx
│   │   ├── lib/            # Utilities & API client
│   │   └── types/          # TypeScript definitions
│   └── package.json
├── electron/               # Electron desktop app
│   ├── src/
│   │   ├── main.ts         # Main process
│   │   └── preload.ts      # Preload script
│   ├── resources/          # App icons
│   └── package.json
├── pyproject.toml          # Python project config
├── package.json            # Root package.json with scripts
└── README.md
```

## Hardware Requirements

| Stage | Minimum | Recommended |
|-------|---------|-------------|
| DWG Parsing | CPU only | - |
| 3D Generation | 6GB VRAM | 16GB VRAM |
| Texture Gen | 8GB VRAM | 16GB VRAM |
| Rendering | 12GB VRAM | 24GB VRAM |
| Video Gen | 16GB VRAM | 24GB VRAM |
| Gaussian Splat | 8GB VRAM | 24GB VRAM |

## Downloads

| Platform | Download |
|----------|----------|
| macOS (Apple Silicon) | Coming Soon |
| macOS (Intel) | Coming Soon |
| Windows | Coming Soon |
| Linux (AppImage) | Coming Soon |

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ezdxf](https://github.com/mozman/ezdxf) - DXF parsing
- [Hunyuan3D](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) - 3D generation
- [ControlNet](https://github.com/lllyasviel/ControlNet) - Conditional image generation
- [3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting) - Real-time rendering
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Diffusion workflow
- [Electron](https://www.electronjs.org/) - Desktop application framework