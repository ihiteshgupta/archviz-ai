# 3D Model Generation Design

## Overview

Transform parsed `FloorPlan` elements (walls, doors, windows, rooms) into 3D meshes exportable as glTF (primary) and OBJ (fallback).

## Requirements

- **Output formats**: glTF/GLB (primary), OBJ + MTL (fallback)
- **Model scope**: Full architectural - walls with cutouts, floors, ceilings, door frames, door panels, window frames, glass panes
- **Floors**: Configurable - single floor default, multi-floor when `floor_level` data exists
- **Library**: trimesh (already in dependencies)
- **Mesh organization**: By element type (walls, floors, ceilings, door_frames, door_panels, window_frames, window_glass)

## Module Structure

```
core/model_gen/
├── __init__.py          # Public API exports
├── generator.py         # Main ModelGenerator class - orchestrates pipeline
├── extruder.py          # Wall/room extrusion logic - 2D polygons → 3D meshes
├── openings.py          # Door/window geometry and boolean cutouts
├── exporter.py          # glTF and OBJ export handling
└── types.py             # Data classes (Mesh3D, Scene3D)
```

## Data Types

```python
@dataclass
class Mesh3D:
    """Individual mesh with vertices, faces, and metadata."""
    id: str
    vertices: np.ndarray      # (N, 3) float array
    faces: np.ndarray         # (M, 3) int array - triangle indices
    normals: np.ndarray       # (N, 3) face normals
    material_id: str          # Reference for material assignment
    element_type: str         # "wall", "floor", "door_panel", etc.
    source_id: str            # Original element ID from FloorPlan

@dataclass
class Scene3D:
    """Complete 3D scene with organized mesh groups."""
    meshes: Dict[str, List[Mesh3D]]  # Grouped by element_type
    bounds: Tuple[Point3D, Point3D]  # Scene bounding box (min, max)
    floor_count: int
    metadata: dict                    # Source file info, generation params

    def export_gltf(self, path: str, binary: bool = True) -> None: ...
    def export_obj(self, path: str) -> None: ...
    def get_by_type(self, element_type: str) -> List[Mesh3D]: ...
    def get_by_source(self, source_id: str) -> List[Mesh3D]: ...
```

## Generation Pipeline

```
FloorPlan → Extrude → Cut Openings → Organize → Export
```

### Stage 1: Extrusion

- **Walls**: Extrude 2D polyline into 3D box using `thickness` and `height`
- **Floors**: Room polygon → flat slab (0.15m thick)
- **Ceilings**: Same as floors, positioned at `ceiling_height`

### Stage 2: Boolean Cutouts

- Find parent wall for each door/window using `wall_id` (or nearest wall)
- Create cutting box at opening position/dimensions
- Use trimesh boolean difference to cut hole in wall mesh

### Stage 3: Opening Geometry

| Element | Meshes |
|---------|--------|
| Door | Left jamb, right jamb, header (0.05m profile), panel (0.04m thick) |
| Window | 4-piece frame (0.05m profile), glass pane (0.006m thick) |

### Stage 4: Scene Assembly

- Group meshes by type
- Assign default material IDs: `wall_exterior`, `wall_interior`, `floor_default`, `ceiling_default`, `door_frame`, `door_panel`, `window_frame`, `glass`
- Multi-floor: offset Z by `level * floor_height` when `floor_level > 0`

## Wall Extrusion Algorithm

1. Take wall's 2D polyline (list of points)
2. Compute perpendicular offset vectors at ±thickness/2
3. Create inner and outer edge polylines
4. Generate 8 vertices per segment (4 bottom + 4 top corners)
5. Create faces: front, back, top, bottom, end caps

**Corner handling**: Miter joints with max 2× thickness clamp; bevel fallback for angles < 30°

## Opening Cutout Algorithm

1. Create cutting box slightly larger than opening (+2mm tolerance)
2. Position at opening.position, rotated by opening.angle
3. Extend through full wall thickness (+10mm each side)
4. `wall_mesh = wall_mesh.difference(cutting_box)`

**Wall finding** (when `wall_id` missing):
1. Project opening position onto each wall segment
2. Select wall with smallest perpendicular distance (< 0.5m threshold)

## Export Formats

### glTF/GLB

```python
scene = trimesh.Scene()
for element_type, meshes in self.meshes.items():
    combined = trimesh.util.concatenate(meshes)
    scene.add_geometry(combined, node_name=element_type)
scene.export(path, file_type="glb")
```

Scene hierarchy:
```
Scene
├── walls
├── floors
├── ceilings
├── door_frames
├── door_panels
├── window_frames
└── window_glass
```

### OBJ

```python
combined = trimesh.util.concatenate(all_meshes)
combined.export(path, file_type="obj")  # Also writes .mtl
```

## Usage

```python
from core.model_gen import ModelGenerator

generator = ModelGenerator()
scene = generator.generate(floor_plan)
scene.export_gltf("output/model.glb")
scene.export_obj("output/model.obj")
```

## Material IDs

Placeholder material IDs for future material system:
- `wall_exterior`, `wall_interior`
- `floor_default`, `ceiling_default`
- `door_frame`, `door_panel`
- `window_frame`, `glass`
