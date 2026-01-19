# Render Pipeline Design: Single Room MVP

**Date**: 2026-01-19
**Status**: Draft
**Goal**: Accurate renders and video walkthroughs from floor plan layouts

## Problem Statement

Current render pipeline uses DALL-E 3 directly from prompts, resulting in:
- Spatial inaccuracy (room proportions don't match floor plan)
- Architectural elements in wrong positions
- Materials not respecting room boundaries
- Perspectives that don't feel grounded in the actual space

## Solution: Hybrid 3D Pipeline

Generate a geometrically accurate 3D model first, then use AI for texturing—ensuring spatial accuracy while maintaining photorealistic output.

## Pipeline Overview

```
Floor Plan (DXF)
    → Parse room (existing DWGParser)
    → Procedural 3D shell (walls, floor, ceiling, openings)
    → AI furniture placement (GPT-4 guided)
    → AI texture generation (per material selection)
    → Bake textures to glTF model
    → Output: Static renders + Interactive viewer + Video walkthrough
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SINGLE ROOM PIPELINE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│  │  PARSE   │───▶│  BUILD   │───▶│  FURNISH │───▶│   TEXTURE    │  │
│  │  Room    │    │  Shell   │    │  (AI)    │    │   (AI Gen)   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────────┘  │
│       │                                                │            │
│       │ Room geometry                                  │ Baked model│
│       │ (walls, openings)                              ▼            │
│       │                                         ┌──────────────┐   │
│       │                                         │   RENDER     │   │
│       │                                         ├──────────────┤   │
│       └────────────────────────────────────────▶│ Three.js     │   │
│                                                 │ (preview)    │   │
│                                                 ├──────────────┤   │
│                                                 │ Blender      │   │
│                                                 │ (final)      │   │
│                                                 └──────────────┘   │
│                                                        │           │
│                                                        ▼           │
│                                    ┌────────────────────────────┐  │
│                                    │ Static Renders │ 3D Viewer │  │
│                                    │ Video Walkthrough          │  │
│                                    └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Key principle**: The same glTF model serves both Three.js preview and Blender final render. What users see in preview matches final output—only quality differs.

## Stage 1: 3D Shell Generation (Procedural)

The shell generator takes parsed room data and builds watertight 3D geometry.

### Input (from existing DWGParser)

```python
Room {
  id: "room_1",
  polygon: [[0,0], [5,0], [5,4], [0,4]],  # meters
  walls: [Wall { start, end, thickness, height }],
  doors: [Door { wall_id, position, width, height }],
  windows: [Window { wall_id, position, width, height, sill_height }]
}
```

### Output

glTF file with named meshes:
- `floor` - flat plane at y=0
- `ceiling` - flat plane at y=wall_height (default 2.7m)
- `wall_north`, `wall_south`, etc. - with boolean cutouts for openings
- `door_frame_1`, `window_frame_1` - simple frame geometry

### Implementation

- Use `trimesh` for CSG operations (wall minus door/window cutouts)
- Generate UV coordinates aligned to real-world scale (1 unit = 1 meter)
- Export as glTF with separate materials per surface type

### Module

`core/model_gen/shell_builder.py`

## Stage 2: AI Furniture Placement

Two-step process: LLM plans the layout, then we place assets from a library.

### Step 1: LLM Layout Planning

GPT-4 receives room context and outputs furniture plan:

```python
# Input to LLM
{
  "room_type": "bedroom",
  "dimensions": { "width": 5, "depth": 4, "height": 2.7 },
  "doors": [{ "wall": "south", "position": 2.5 }],
  "windows": [{ "wall": "east", "position": 2.0 }],
  "style": "scandinavian"
}

# LLM Output
{
  "furniture": [
    { "type": "bed_queen", "position": [2.5, 0, 3.0], "rotation": 0 },
    { "type": "nightstand", "position": [0.8, 0, 3.0], "rotation": 0 },
    { "type": "nightstand", "position": [4.2, 0, 3.0], "rotation": 0 },
    { "type": "dresser", "position": [0.5, 0, 0.5], "rotation": 90 }
  ]
}
```

### Step 2: Asset Placement

- Maintain library of furniture glTF models (~20-30 essential pieces per room type)
- Sources: Sketchfab (CC licensed), Polyhaven, Hunyuan3D for custom pieces
- Merge furniture meshes into room glTF, preserving material slots

### Module

`core/model_gen/furniture_placer.py`

## Stage 3: AI Texture Generation

Generate unique, tileable PBR textures based on material selections.

### Flow

```
Material Selection (e.g., "white oak flooring")
    → Prompt construction
    → AI generates 512x512 tileable texture
    → Optional: Generate normal/roughness maps
    → Bake into glTF material
```

### Implementation

DALL-E 3 with tileable texture prompting:

```python
prompt = """Seamless tileable texture for {material_name},
top-down view, flat lighting, no shadows,
PBR material reference, {style} interior design style"""
```

Post-process for tileability:
- Edge-blend using cross-fade at boundaries
- Or use img2img with ControlNet tile model if quality insufficient

### Texture Slots

- `floor_diffuse`, `floor_normal` (optional)
- `wall_diffuse`, `wall_normal` (optional)
- `ceiling_diffuse` (usually plain)

### Caching

Cache generated textures by material ID + style combo. Same "scandinavian white oak" reuses cached texture across projects.

### Module

`core/materials/texture_generator.py`

## Stage 4: Interactive Preview (Three.js)

Browser-based preview for real-time exploration and waypoint editing.

### Features

1. **Orbit controls** - Pan, zoom, rotate around the room
2. **First-person mode** - WASD + mouse navigation at eye height (1.6m)
3. **Waypoint editor** - Click floor plan minimap or 3D view to place camera points
4. **Real-time material swap** - Change materials, see updated textures immediately

### Components

```tsx
<RoomViewer3D>
  <RoomShell gltfUrl={shellUrl} />
  <Furniture gltfUrl={furnishedUrl} />
  <WaypointMarkers points={waypoints} onAdd={} onRemove={} />
  <CameraPathPreview waypoints={waypoints} />
  <ViewModeToggle modes={['orbit', 'firstPerson', 'walkthrough']} />
</RoomViewer3D>
```

### Waypoint Data Structure

```typescript
interface Waypoint {
  id: string;
  position: [number, number, number];  // camera location
  lookAt: [number, number, number];    // target point
  duration?: number;                    // seconds to reach from previous
}
```

### Preview Walkthrough

Animate camera through waypoints using Three.js `CatmullRomCurve3` for smooth interpolation.

### Files

`frontend/src/components/room-viewer/`

## Stage 5: Final Rendering (Blender)

Server-side Blender produces high-quality deliverables.

### Why Blender

- Cycles renderer for photorealistic global illumination
- EEVEE for faster "good enough" renders
- Python API for full automation
- Native glTF import

### Pipeline

```
API Request (job_id, gltf_url, render_type, camera_positions)
    → Worker pulls glTF from storage
    → Blender Python script:
        1. Import glTF (room + furniture + baked textures)
        2. Set up HDRI lighting (interior presets)
        3. Position camera(s)
        4. Render via Cycles (static) or EEVEE (video frames)
    → Upload results to Azure Blob Storage
    → Notify frontend via webhook/polling
```

### Render Presets

| Type | Engine | Resolution | Samples | Est. Time |
|------|--------|------------|---------|-----------|
| Preview | EEVEE | 1024x1024 | - | ~5s |
| Final Static | Cycles | 2048x2048 | 256 | ~30s |
| Video Frame | EEVEE | 1920x1080 | - | ~2s/frame |

### Infrastructure

- Containerized Blender (Docker image with bpy)
- GPU instance for Cycles (or CPU fallback)
- Job queue via Redis

### Module

`core/render/blender_renderer.py`

## Stage 6: Video Walkthrough Generation

User-defined waypoints rendered to smooth MP4 walkthrough.

### Process

```
Waypoints array
    → Generate interpolated camera path (CatmullRomCurve3)
    → Calculate total frames (30fps × total duration)
    → Render each frame via Blender EEVEE
    → Encode frames to MP4 via FFmpeg
    → Upload final video
```

### Camera Path Interpolation

```python
path = CatmullRomSpline(waypoints)
total_duration = sum(w.duration for w in waypoints)  # e.g., 15 seconds
total_frames = total_duration * 30  # 450 frames

for frame_idx in range(total_frames):
    t = frame_idx / total_frames
    camera_pos = path.position_at(t)
    camera_lookat = path.lookat_at(t)
    render_frame(camera_pos, camera_lookat, f"frame_{frame_idx:04d}.png")
```

### Video Encoding

```bash
ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p walkthrough.mp4
```

### Optimizations

- Render frames in parallel batches (if multiple GPUs)
- Option for 15fps draft quality
- Cache identical frames if camera stationary

### Module

`core/walkthrough/video_generator.py`

## API Design

New endpoints for pipeline orchestration.

### Endpoints

```
POST /api/room-pipeline/generate-shell
  Body: { room_id, room_data }
  Returns: { job_id, status }

POST /api/room-pipeline/furnish
  Body: { job_id, room_type, style }
  Returns: { job_id, furniture_plan }

POST /api/room-pipeline/generate-textures
  Body: { job_id, material_assignments }
  Returns: { job_id, texture_urls }

POST /api/room-pipeline/render
  Body: { job_id, render_type: "static" | "video", camera_positions?, waypoints? }
  Returns: { render_job_id }

GET /api/room-pipeline/{job_id}/status
  Returns: { stage, progress, preview_url?, outputs? }
```

### Job State Machine

```
CREATED → SHELL_BUILDING → FURNISHING → TEXTURING → READY_FOR_RENDER
                                                          ↓
                           COMPLETE ← RENDERING ←─────────┘
```

### Route File

`api/routes/room_pipeline.py`

## Code Organization

```
core/
├── model_gen/                    # NEW - 3D generation
│   ├── __init__.py
│   ├── shell_builder.py          # Procedural room geometry
│   ├── furniture_placer.py       # LLM-guided furniture layout
│   └── gltf_utils.py             # Merge meshes, UV handling
│
├── materials/                    # EXTEND existing
│   ├── texture_generator.py      # NEW - AI texture generation
│   └── library.py                # Existing material database
│
├── render/                       # NEW - Blender pipeline
│   ├── blender_renderer.py       # Job orchestration
│   ├── render_queue.py           # Redis job queue
│   └── blender_scripts/
│       ├── render_room.py        # Runs inside Blender
│       └── setup_scene.py        # Lighting presets
│
└── walkthrough/                  # NEW - Video generation
    ├── video_generator.py        # Frame orchestration
    ├── camera_path.py            # Spline interpolation
    └── ffmpeg_encoder.py         # Video encoding

api/routes/
└── room_pipeline.py              # NEW - Pipeline endpoints

frontend/src/components/
└── room-viewer/                  # NEW - Interactive preview
    ├── RoomViewer3D.tsx          # Main container
    ├── WaypointEditor.tsx        # Click-to-place waypoints
    ├── CameraPathPreview.tsx     # Visualize path
    └── ViewModeToggle.tsx        # Orbit/FP/walkthrough
```

## Dependencies

### Python (pyproject.toml)

- `pygltflib` - glTF manipulation
- `ffmpeg-python` - Video encoding wrapper

### Infrastructure

- Docker image with Blender + bpy
- GPU instance for Cycles rendering (optional CPU fallback)

## MVP Scope

**Single room end-to-end**:
1. One room from floor plan
2. Shell generation with openings
3. Basic furniture placement (bedroom OR living room)
4. AI-generated floor and wall textures
5. Three.js preview with orbit controls
6. Waypoint placement (3-5 points)
7. Video export via Blender

**Not in MVP**:
- Multi-room walkthroughs
- Custom furniture uploads
- Real-time collaboration
- Normal/roughness map generation

## Success Criteria

1. Generated room shell matches floor plan dimensions within 5% tolerance
2. Doors and windows appear in correct positions
3. Preview in Three.js matches final Blender render (same geometry)
4. Video walkthrough plays smoothly at 30fps
5. End-to-end pipeline completes in under 5 minutes for single room
