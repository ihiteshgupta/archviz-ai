# ArchViz AI

> AI-powered architectural visualization pipeline: DWG to renders to walkthroughs with LLM-guided material selection

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Project Board](https://img.shields.io/badge/Project-Roadmap-green)](https://github.com/users/ihiteshgupta/projects/3)

## Overview

ArchViz AI is an end-to-end platform that transforms architectural CAD files (DWG/DXF) into photorealistic renders and interactive walkthroughs using AI. The system features an LLM-powered material selection assistant that guides architects through texture and material choices.

### Key Features

- **Native DWG Support**: Direct parsing of AutoCAD files without manual export
- **AI Rendering**: ControlNet + SDXL/Flux for photorealistic architectural renders
- **LLM Material Assistant**: Conversational interface for material and texture selection
- **PBR Texture Generation**: AI-generated physically-based rendering textures
- **3D Walkthroughs**: Gaussian Splatting for real-time navigable scenes
- **Video Export**: Smooth walkthrough videos with camera path control

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
| Backend | FastAPI, Redis, PostgreSQL |

## Roadmap

### Phase 1: Core Pipeline
- [#1](../../issues/1) DWG/DXF Parser Module
- [#2](../../issues/2) 3D Model Generation from Floor Plan
- [#3](../../issues/3) Single-View ControlNet Render Pipeline
- [#4](../../issues/4) Web Interface MVP

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

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
cd frontend && npm install

# Download AI models
python scripts/download_models.py
```

### Quick Start

```bash
# Start the backend
python -m uvicorn api.main:app --reload

# Start the frontend (in another terminal)
cd frontend && npm run dev
```

## Project Structure

```
archviz-ai/
├── api/                    # FastAPI backend
│   ├── routes/
│   ├── services/
│   └── main.py
├── core/                   # Core processing modules
│   ├── dwg_parser/         # DWG/DXF parsing
│   ├── model_gen/          # 3D model generation
│   ├── materials/          # Material system
│   ├── render/             # AI rendering pipeline
│   └── walkthrough/        # Video/splat generation
├── frontend/               # Next.js web app
│   ├── components/
│   ├── pages/
│   └── lib/
├── models/                 # AI model weights
├── scripts/                # Utility scripts
└── tests/                  # Test suite
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