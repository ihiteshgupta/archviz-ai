# Render Pipeline MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single-room pipeline that generates spatially accurate 3D renders and video walkthroughs from parsed floor plan data.

**Architecture:** Hybrid approach using procedural 3D shell generation (trimesh) for geometry, GPT-4 for furniture layout planning, DALL-E 3 for texture generation, Three.js for interactive preview, and Blender for final high-quality renders/video.

**Tech Stack:** Python (trimesh, pygltflib, ffmpeg-python), TypeScript/React (Three.js, @react-three/fiber), Blender Python API, Redis job queue

**Design Reference:** `docs/plans/2026-01-19-render-pipeline-design.md`

---

## Phase 1: 3D Shell Generation

### Task 1.1: Shell Builder Foundation

**Files:**
- Create: `core/model_gen/shell_builder.py`
- Create: `tests/test_shell_builder.py`

**Step 1: Write the failing test for basic floor generation**

```python
# tests/test_shell_builder.py
import pytest
import numpy as np
from core.model_gen.shell_builder import ShellBuilder


class TestShellBuilder:
    """Tests for procedural 3D shell generation from room data."""

    def test_generates_floor_mesh_from_rectangular_room(self):
        """Floor mesh should match room polygon dimensions."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],  # 5m x 4m
        }

        builder = ShellBuilder(room_data)
        floor_mesh = builder.build_floor()

        # Floor should be at y=0, spanning the polygon
        assert floor_mesh is not None
        bounds = floor_mesh.bounds
        assert np.isclose(bounds[0][1], 0)  # min y = 0
        assert np.isclose(bounds[1][1], 0)  # max y = 0 (flat)
        assert np.isclose(bounds[1][0] - bounds[0][0], 5, atol=0.01)  # width ~5m
        assert np.isclose(bounds[1][2] - bounds[0][2], 4, atol=0.01)  # depth ~4m
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_generates_floor_mesh_from_rectangular_room -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'core.model_gen.shell_builder'"

**Step 3: Write minimal implementation**

```python
# core/model_gen/shell_builder.py
"""Procedural 3D shell generation from parsed room data."""

import numpy as np
import trimesh
from typing import Any


class ShellBuilder:
    """Builds 3D geometry for room shell (floor, ceiling, walls) from room data."""

    def __init__(self, room_data: dict[str, Any], wall_height: float = 2.7):
        """
        Initialize shell builder with room data.

        Args:
            room_data: Dict with 'polygon' (list of [x,y] points in meters),
                      'walls', 'doors', 'windows'
            wall_height: Height of walls in meters (default 2.7m)
        """
        self.room_data = room_data
        self.wall_height = wall_height
        self.polygon = np.array(room_data["polygon"])

    def build_floor(self) -> trimesh.Trimesh:
        """Generate floor mesh at y=0 from room polygon."""
        # Create 2D polygon vertices, add z=0 (which becomes y after rotation)
        vertices_2d = self.polygon

        # Triangulate the polygon
        from scipy.spatial import Delaunay
        tri = Delaunay(vertices_2d)

        # Create 3D vertices (x, 0, z) - floor at y=0
        vertices_3d = np.zeros((len(vertices_2d), 3))
        vertices_3d[:, 0] = vertices_2d[:, 0]  # x
        vertices_3d[:, 1] = 0  # y = 0 (floor level)
        vertices_3d[:, 2] = vertices_2d[:, 1]  # z (from 2D y)

        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices_3d, faces=tri.simplices)
        return mesh
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_generates_floor_mesh_from_rectangular_room -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/model_gen/shell_builder.py tests/test_shell_builder.py
git commit -m "feat(model_gen): add ShellBuilder with floor mesh generation"
```

---

### Task 1.2: Ceiling Generation

**Files:**
- Modify: `core/model_gen/shell_builder.py`
- Modify: `tests/test_shell_builder.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_shell_builder.py TestShellBuilder class

    def test_generates_ceiling_at_wall_height(self):
        """Ceiling mesh should be at wall_height, matching floor dimensions."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        ceiling_mesh = builder.build_ceiling()

        bounds = ceiling_mesh.bounds
        assert np.isclose(bounds[0][1], 2.7, atol=0.01)  # min y = 2.7
        assert np.isclose(bounds[1][1], 2.7, atol=0.01)  # max y = 2.7
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_generates_ceiling_at_wall_height -v`

Expected: FAIL with "AttributeError: 'ShellBuilder' object has no attribute 'build_ceiling'"

**Step 3: Add ceiling implementation**

```python
# Add to core/model_gen/shell_builder.py ShellBuilder class

    def build_ceiling(self) -> trimesh.Trimesh:
        """Generate ceiling mesh at wall_height from room polygon."""
        from scipy.spatial import Delaunay

        vertices_2d = self.polygon
        tri = Delaunay(vertices_2d)

        vertices_3d = np.zeros((len(vertices_2d), 3))
        vertices_3d[:, 0] = vertices_2d[:, 0]
        vertices_3d[:, 1] = self.wall_height  # ceiling at wall height
        vertices_3d[:, 2] = vertices_2d[:, 1]

        # Reverse face winding for ceiling to face downward
        faces = tri.simplices[:, ::-1]

        mesh = trimesh.Trimesh(vertices=vertices_3d, faces=faces)
        return mesh
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_generates_ceiling_at_wall_height -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/model_gen/shell_builder.py tests/test_shell_builder.py
git commit -m "feat(model_gen): add ceiling mesh generation to ShellBuilder"
```

---

### Task 1.3: Wall Generation (No Openings)

**Files:**
- Modify: `core/model_gen/shell_builder.py`
- Modify: `tests/test_shell_builder.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_shell_builder.py TestShellBuilder class

    def test_generates_walls_from_polygon_edges(self):
        """Walls should be generated for each edge of the polygon."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],  # 4 edges
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        walls = builder.build_walls()

        assert len(walls) == 4  # One wall per edge

        # Each wall should span from y=0 to y=2.7
        for wall in walls:
            bounds = wall.bounds
            assert np.isclose(bounds[0][1], 0, atol=0.01)  # min y = 0
            assert np.isclose(bounds[1][1], 2.7, atol=0.01)  # max y = 2.7
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_generates_walls_from_polygon_edges -v`

Expected: FAIL with "AttributeError: 'ShellBuilder' object has no attribute 'build_walls'"

**Step 3: Add walls implementation**

```python
# Add to core/model_gen/shell_builder.py ShellBuilder class

    def build_walls(self) -> list[trimesh.Trimesh]:
        """Generate wall meshes for each polygon edge."""
        walls = []
        n = len(self.polygon)

        for i in range(n):
            p1 = self.polygon[i]
            p2 = self.polygon[(i + 1) % n]

            wall = self._create_wall_quad(p1, p2)
            walls.append(wall)

        return walls

    def _create_wall_quad(
        self,
        p1: np.ndarray,
        p2: np.ndarray
    ) -> trimesh.Trimesh:
        """Create a wall quad between two floor points."""
        # Four corners of the wall
        vertices = np.array([
            [p1[0], 0, p1[1]],              # bottom-left
            [p2[0], 0, p2[1]],              # bottom-right
            [p2[0], self.wall_height, p2[1]], # top-right
            [p1[0], self.wall_height, p1[1]], # top-left
        ])

        # Two triangles forming the quad (facing inward)
        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
        ])

        return trimesh.Trimesh(vertices=vertices, faces=faces)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_generates_walls_from_polygon_edges -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/model_gen/shell_builder.py tests/test_shell_builder.py
git commit -m "feat(model_gen): add wall mesh generation to ShellBuilder"
```

---

### Task 1.4: Wall Openings (Doors/Windows)

**Files:**
- Modify: `core/model_gen/shell_builder.py`
- Modify: `tests/test_shell_builder.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_shell_builder.py TestShellBuilder class

    def test_walls_have_door_cutouts(self):
        """Walls should have boolean cutouts for doors."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "doors": [
                {
                    "wall_index": 0,  # South wall (0,0 to 5,0)
                    "position": 2.0,  # 2m from start of wall
                    "width": 0.9,
                    "height": 2.1,
                }
            ],
        }

        builder = ShellBuilder(room_data, wall_height=2.7)
        walls = builder.build_walls()

        # South wall should have opening (fewer faces than solid wall)
        south_wall = walls[0]
        solid_builder = ShellBuilder({"id": "x", "polygon": room_data["polygon"]})
        solid_walls = solid_builder.build_walls()
        solid_south = solid_walls[0]

        # Wall with door should have more faces due to cutout geometry
        assert len(south_wall.faces) > len(solid_south.faces)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_walls_have_door_cutouts -v`

Expected: FAIL (walls currently ignore doors)

**Step 3: Update walls implementation to handle openings**

```python
# Update core/model_gen/shell_builder.py

    def __init__(self, room_data: dict[str, Any], wall_height: float = 2.7):
        self.room_data = room_data
        self.wall_height = wall_height
        self.polygon = np.array(room_data["polygon"])
        self.doors = room_data.get("doors", [])
        self.windows = room_data.get("windows", [])

    def build_walls(self) -> list[trimesh.Trimesh]:
        """Generate wall meshes with door/window cutouts."""
        walls = []
        n = len(self.polygon)

        for i in range(n):
            p1 = self.polygon[i]
            p2 = self.polygon[(i + 1) % n]

            # Get openings for this wall
            wall_doors = [d for d in self.doors if d.get("wall_index") == i]
            wall_windows = [w for w in self.windows if w.get("wall_index") == i]

            wall = self._create_wall_with_openings(p1, p2, wall_doors, wall_windows)
            walls.append(wall)

        return walls

    def _create_wall_with_openings(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        doors: list[dict],
        windows: list[dict],
    ) -> trimesh.Trimesh:
        """Create wall with boolean cutouts for doors and windows."""
        # Create solid wall first
        wall = self._create_wall_quad(p1, p2)

        if not doors and not windows:
            return wall

        # Calculate wall direction vector
        wall_vec = p2 - p1
        wall_length = np.linalg.norm(wall_vec)
        wall_dir = wall_vec / wall_length

        # Create cutout boxes and subtract them
        for door in doors:
            cutout = self._create_opening_box(
                p1, wall_dir,
                door["position"], door["width"],
                0, door["height"]  # Doors start at floor
            )
            wall = wall.difference(cutout)

        for window in windows:
            sill = window.get("sill_height", 0.9)
            cutout = self._create_opening_box(
                p1, wall_dir,
                window["position"], window["width"],
                sill, sill + window["height"]
            )
            wall = wall.difference(cutout)

        return wall

    def _create_opening_box(
        self,
        wall_start: np.ndarray,
        wall_dir: np.ndarray,
        position: float,
        width: float,
        bottom: float,
        top: float,
    ) -> trimesh.Trimesh:
        """Create a box for boolean subtraction (door/window opening)."""
        # Calculate opening position along wall
        start_pos = wall_start + wall_dir * position
        end_pos = wall_start + wall_dir * (position + width)

        # Create box extending through wall (0.5m thick to ensure clean cut)
        # Perpendicular direction
        perp = np.array([-wall_dir[1], wall_dir[0]])

        vertices = np.array([
            # Bottom face
            [start_pos[0] - perp[0]*0.25, bottom, start_pos[1] - perp[1]*0.25],
            [end_pos[0] - perp[0]*0.25, bottom, end_pos[1] - perp[1]*0.25],
            [end_pos[0] + perp[0]*0.25, bottom, end_pos[1] + perp[1]*0.25],
            [start_pos[0] + perp[0]*0.25, bottom, start_pos[1] + perp[1]*0.25],
            # Top face
            [start_pos[0] - perp[0]*0.25, top, start_pos[1] - perp[1]*0.25],
            [end_pos[0] - perp[0]*0.25, top, end_pos[1] - perp[1]*0.25],
            [end_pos[0] + perp[0]*0.25, top, end_pos[1] + perp[1]*0.25],
            [start_pos[0] + perp[0]*0.25, top, start_pos[1] + perp[1]*0.25],
        ])

        return trimesh.convex.convex_hull(vertices)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_walls_have_door_cutouts -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/model_gen/shell_builder.py tests/test_shell_builder.py
git commit -m "feat(model_gen): add door/window cutouts to wall generation"
```

---

### Task 1.5: Export to glTF

**Files:**
- Modify: `core/model_gen/shell_builder.py`
- Modify: `tests/test_shell_builder.py`
- Add dependency: `pygltflib` to pyproject.toml

**Step 1: Write the failing test**

```python
# Add to tests/test_shell_builder.py

import tempfile
import os

# Add to TestShellBuilder class

    def test_exports_complete_shell_to_gltf(self):
        """Complete shell should export to valid glTF file."""
        room_data = {
            "id": "room_1",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "doors": [{"wall_index": 0, "position": 2.0, "width": 0.9, "height": 2.1}],
        }

        builder = ShellBuilder(room_data)

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            output_path = f.name

        try:
            builder.export_gltf(output_path)

            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

            # Verify it's valid glTF by loading it
            import trimesh
            scene = trimesh.load(output_path)

            # Should have floor, ceiling, and walls
            mesh_names = list(scene.geometry.keys())
            assert any("floor" in name.lower() for name in mesh_names)
            assert any("ceiling" in name.lower() for name in mesh_names)
            assert any("wall" in name.lower() for name in mesh_names)
        finally:
            os.unlink(output_path)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_exports_complete_shell_to_gltf -v`

Expected: FAIL with "AttributeError: 'ShellBuilder' object has no attribute 'export_gltf'"

**Step 3: Add export implementation**

```python
# Add to core/model_gen/shell_builder.py ShellBuilder class

    def build_shell(self) -> trimesh.Scene:
        """Build complete room shell as a trimesh Scene."""
        scene = trimesh.Scene()

        # Add floor
        floor = self.build_floor()
        scene.add_geometry(floor, node_name="floor", geom_name="floor")

        # Add ceiling
        ceiling = self.build_ceiling()
        scene.add_geometry(ceiling, node_name="ceiling", geom_name="ceiling")

        # Add walls
        walls = self.build_walls()
        for i, wall in enumerate(walls):
            name = f"wall_{i}"
            scene.add_geometry(wall, node_name=name, geom_name=name)

        return scene

    def export_gltf(self, output_path: str) -> None:
        """Export complete shell to glTF/GLB file."""
        scene = self.build_shell()
        scene.export(output_path)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_shell_builder.py::TestShellBuilder::test_exports_complete_shell_to_gltf -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/model_gen/shell_builder.py tests/test_shell_builder.py
git commit -m "feat(model_gen): add glTF export for complete room shell"
```

---

## Phase 2: AI Furniture Placement

### Task 2.1: Furniture Placer Foundation

**Files:**
- Create: `core/model_gen/furniture_placer.py`
- Create: `tests/test_furniture_placer.py`

**Step 1: Write the failing test**

```python
# tests/test_furniture_placer.py
import pytest
from unittest.mock import AsyncMock, patch

from core.model_gen.furniture_placer import FurniturePlacer


class TestFurniturePlacer:
    """Tests for AI-guided furniture placement."""

    @pytest.mark.asyncio
    async def test_generates_furniture_plan_for_bedroom(self):
        """Should generate appropriate furniture list for bedroom."""
        room_context = {
            "room_type": "bedroom",
            "dimensions": {"width": 5, "depth": 4, "height": 2.7},
            "doors": [{"wall": "south", "position": 2.5}],
            "windows": [{"wall": "east", "position": 2.0}],
            "style": "scandinavian",
        }

        # Mock the OpenAI response
        mock_response = {
            "furniture": [
                {"type": "bed_queen", "position": [2.5, 0, 3.0], "rotation": 0},
                {"type": "nightstand", "position": [0.8, 0, 3.0], "rotation": 0},
            ]
        }

        with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            placer = FurniturePlacer()
            plan = await placer.generate_plan(room_context)

            assert "furniture" in plan
            assert len(plan["furniture"]) >= 1
            assert all("type" in f and "position" in f for f in plan["furniture"])
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_furniture_placer.py::TestFurniturePlacer::test_generates_furniture_plan_for_bedroom -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# core/model_gen/furniture_placer.py
"""AI-guided furniture placement using GPT-4."""

import json
from typing import Any

from core.azure.openai_service import AzureOpenAIService


FURNITURE_PROMPT = """You are an interior design assistant. Given a room's specifications,
generate a furniture placement plan.

Room specifications:
- Type: {room_type}
- Dimensions: {width}m x {depth}m x {height}m
- Doors: {doors}
- Windows: {windows}
- Style: {style}

Return a JSON object with a "furniture" array. Each item should have:
- "type": furniture type (e.g., "bed_queen", "nightstand", "dresser", "desk", "chair")
- "position": [x, y, z] coordinates in meters (y=0 is floor)
- "rotation": rotation in degrees around Y axis

Place furniture logically:
- Beds against walls, not blocking doors
- Nightstands beside beds
- Clear pathways to doors
- Utilize natural light from windows

Return ONLY valid JSON, no explanation."""


class FurniturePlacer:
    """Generates furniture placement plans using GPT-4."""

    def __init__(self, openai_service: AzureOpenAIService | None = None):
        self.openai_service = openai_service or AzureOpenAIService()

    async def generate_plan(self, room_context: dict[str, Any]) -> dict[str, Any]:
        """Generate furniture placement plan for a room."""
        return await self._call_llm(room_context)

    async def _call_llm(self, room_context: dict[str, Any]) -> dict[str, Any]:
        """Call GPT-4 to generate furniture plan."""
        prompt = FURNITURE_PROMPT.format(
            room_type=room_context["room_type"],
            width=room_context["dimensions"]["width"],
            depth=room_context["dimensions"]["depth"],
            height=room_context["dimensions"]["height"],
            doors=json.dumps(room_context.get("doors", [])),
            windows=json.dumps(room_context.get("windows", [])),
            style=room_context.get("style", "modern"),
        )

        response = await self.openai_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        return json.loads(response)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_furniture_placer.py::TestFurniturePlacer::test_generates_furniture_plan_for_bedroom -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/model_gen/furniture_placer.py tests/test_furniture_placer.py
git commit -m "feat(model_gen): add FurniturePlacer with GPT-4 layout planning"
```

---

### Task 2.2: Furniture Asset Loading

**Files:**
- Create: `core/model_gen/furniture_library.py`
- Create: `tests/test_furniture_library.py`
- Create: `assets/furniture/` directory structure

**Step 1: Write the failing test**

```python
# tests/test_furniture_library.py
import pytest
from core.model_gen.furniture_library import FurnitureLibrary


class TestFurnitureLibrary:
    """Tests for furniture asset library."""

    def test_lists_available_furniture_types(self):
        """Should list all available furniture types."""
        library = FurnitureLibrary()
        types = library.list_types()

        assert isinstance(types, list)
        assert len(types) > 0
        assert "bed_queen" in types or "bed" in types

    def test_returns_none_for_missing_asset(self):
        """Should return None for non-existent furniture type."""
        library = FurnitureLibrary()
        asset = library.get_asset("nonexistent_furniture_xyz")

        assert asset is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_furniture_library.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# core/model_gen/furniture_library.py
"""Furniture asset library for 3D model placement."""

import os
from pathlib import Path
from typing import Any

import trimesh


# Default furniture dimensions (meters) for placeholder generation
FURNITURE_DEFAULTS = {
    "bed_queen": {"width": 1.6, "depth": 2.0, "height": 0.5},
    "bed_king": {"width": 1.9, "depth": 2.0, "height": 0.5},
    "bed_single": {"width": 0.9, "depth": 2.0, "height": 0.5},
    "nightstand": {"width": 0.5, "depth": 0.4, "height": 0.6},
    "dresser": {"width": 1.2, "depth": 0.5, "height": 0.9},
    "desk": {"width": 1.2, "depth": 0.6, "height": 0.75},
    "chair": {"width": 0.5, "depth": 0.5, "height": 0.9},
    "sofa_3seat": {"width": 2.2, "depth": 0.9, "height": 0.85},
    "armchair": {"width": 0.9, "depth": 0.9, "height": 0.85},
    "coffee_table": {"width": 1.2, "depth": 0.6, "height": 0.45},
    "dining_table": {"width": 1.6, "depth": 0.9, "height": 0.75},
    "dining_chair": {"width": 0.45, "depth": 0.45, "height": 0.9},
    "wardrobe": {"width": 1.8, "depth": 0.6, "height": 2.2},
    "bookshelf": {"width": 0.8, "depth": 0.3, "height": 1.8},
}


class FurnitureLibrary:
    """Manages furniture 3D assets."""

    def __init__(self, assets_dir: str | None = None):
        if assets_dir:
            self.assets_dir = Path(assets_dir)
        else:
            self.assets_dir = Path(__file__).parent.parent.parent / "assets" / "furniture"

    def list_types(self) -> list[str]:
        """List all available furniture types."""
        types = list(FURNITURE_DEFAULTS.keys())

        # Add any custom assets from directory
        if self.assets_dir.exists():
            for f in self.assets_dir.glob("*.glb"):
                name = f.stem
                if name not in types:
                    types.append(name)

        return sorted(types)

    def get_asset(self, furniture_type: str) -> trimesh.Trimesh | None:
        """Get furniture mesh by type. Returns placeholder if no asset file."""
        # Try to load from file first
        asset_path = self.assets_dir / f"{furniture_type}.glb"
        if asset_path.exists():
            return trimesh.load(asset_path)

        # Generate placeholder box if we have dimensions
        if furniture_type in FURNITURE_DEFAULTS:
            dims = FURNITURE_DEFAULTS[furniture_type]
            return self._create_placeholder(dims)

        return None

    def _create_placeholder(self, dims: dict[str, float]) -> trimesh.Trimesh:
        """Create a simple box placeholder for furniture."""
        box = trimesh.creation.box(
            extents=[dims["width"], dims["height"], dims["depth"]]
        )
        # Move so bottom is at y=0
        box.apply_translation([0, dims["height"] / 2, 0])
        return box
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_furniture_library.py -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
mkdir -p assets/furniture
git add core/model_gen/furniture_library.py tests/test_furniture_library.py assets/furniture/.gitkeep
git commit -m "feat(model_gen): add FurnitureLibrary with placeholder generation"
```

---

## Phase 3: AI Texture Generation

### Task 3.1: Texture Generator Foundation

**Files:**
- Create: `core/materials/texture_generator.py`
- Create: `tests/test_texture_generator.py`

**Step 1: Write the failing test**

```python
# tests/test_texture_generator.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from PIL import Image
import io

from core.materials.texture_generator import TextureGenerator


class TestTextureGenerator:
    """Tests for AI texture generation."""

    @pytest.mark.asyncio
    async def test_generates_texture_for_material(self):
        """Should generate a texture image for a given material."""
        # Mock DALL-E response with a simple image
        mock_image = Image.new("RGB", (512, 512), color="brown")
        img_bytes = io.BytesIO()
        mock_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
            mock_dalle.return_value = img_bytes.getvalue()

            generator = TextureGenerator()
            texture = await generator.generate(
                material_name="white oak flooring",
                style="scandinavian"
            )

            assert texture is not None
            assert isinstance(texture, bytes)

            # Verify it's a valid image
            img = Image.open(io.BytesIO(texture))
            assert img.size == (512, 512)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_texture_generator.py::TestTextureGenerator::test_generates_texture_for_material -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# core/materials/texture_generator.py
"""AI-powered texture generation using DALL-E 3."""

import hashlib
import io
from pathlib import Path
from typing import Any

from PIL import Image

from core.azure.openai_service import AzureOpenAIService


TEXTURE_PROMPT = """Seamless tileable texture for {material_name},
top-down orthographic view, flat even lighting, no shadows or highlights,
PBR material reference photograph, {style} interior design style,
high resolution, uniform pattern that tiles perfectly"""


class TextureGenerator:
    """Generates tileable textures using DALL-E 3."""

    def __init__(
        self,
        openai_service: AzureOpenAIService | None = None,
        cache_dir: str | None = None
    ):
        self.openai_service = openai_service or AzureOpenAIService()
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/textures")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        material_name: str,
        style: str = "modern",
        size: int = 512,
    ) -> bytes:
        """Generate a tileable texture for the given material."""
        # Check cache first
        cache_key = self._cache_key(material_name, style, size)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Generate new texture
        texture_bytes = await self._call_dalle(material_name, style, size)

        # Post-process for better tileability
        processed = self._make_tileable(texture_bytes, size)

        # Cache result
        self._save_cache(cache_key, processed)

        return processed

    async def _call_dalle(
        self,
        material_name: str,
        style: str,
        size: int
    ) -> bytes:
        """Call DALL-E 3 to generate texture."""
        prompt = TEXTURE_PROMPT.format(
            material_name=material_name,
            style=style
        )

        image_bytes = await self.openai_service.generate_image(
            prompt=prompt,
            size=f"{size}x{size}",
        )

        return image_bytes

    def _make_tileable(self, image_bytes: bytes, size: int) -> bytes:
        """Post-process image to improve tileability via edge blending."""
        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((size, size))

        # Simple edge blend: average the edges with their opposites
        # This creates a basic seamless tile effect
        import numpy as np
        arr = np.array(img, dtype=np.float32)

        blend_width = size // 8  # 12.5% blend zone

        # Create blend weights
        weights = np.linspace(0, 1, blend_width)

        # Blend left-right edges
        for i, w in enumerate(weights):
            arr[:, i] = arr[:, i] * (1 - w) + arr[:, -(blend_width - i)] * w
            arr[:, -(blend_width - i)] = arr[:, i]

        # Blend top-bottom edges
        for i, w in enumerate(weights):
            arr[i, :] = arr[i, :] * (1 - w) + arr[-(blend_width - i), :] * w
            arr[-(blend_width - i), :] = arr[i, :]

        result = Image.fromarray(arr.astype(np.uint8))

        output = io.BytesIO()
        result.save(output, format="PNG")
        return output.getvalue()

    def _cache_key(self, material: str, style: str, size: int) -> str:
        """Generate cache key for texture."""
        key_str = f"{material}_{style}_{size}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> bytes | None:
        """Get texture from cache if exists."""
        cache_path = self.cache_dir / f"{cache_key}.png"
        if cache_path.exists():
            return cache_path.read_bytes()
        return None

    def _save_cache(self, cache_key: str, data: bytes) -> None:
        """Save texture to cache."""
        cache_path = self.cache_dir / f"{cache_key}.png"
        cache_path.write_bytes(data)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_texture_generator.py::TestTextureGenerator::test_generates_texture_for_material -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/materials/texture_generator.py tests/test_texture_generator.py
git commit -m "feat(materials): add TextureGenerator with DALL-E 3 and caching"
```

---

## Phase 4: API Endpoints

### Task 4.1: Room Pipeline Router

**Files:**
- Create: `api/routes/room_pipeline.py`
- Create: `tests/test_room_pipeline_api.py`
- Modify: `api/main.py` to register router

**Step 1: Write the failing test**

```python
# tests/test_room_pipeline_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


class TestRoomPipelineAPI:
    """Tests for room pipeline API endpoints."""

    @pytest.mark.asyncio
    async def test_generate_shell_returns_job_id(self):
        """POST /api/room-pipeline/generate-shell should return job_id."""
        room_data = {
            "room_id": "room_1",
            "room_data": {
                "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
                "doors": [],
                "windows": [],
            }
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/room-pipeline/generate-shell",
                json=room_data
            )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "status" in data
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_room_pipeline_api.py::TestRoomPipelineAPI::test_generate_shell_returns_job_id -v`

Expected: FAIL with 404 (route not found)

**Step 3: Write the router implementation**

```python
# api/routes/room_pipeline.py
"""Room pipeline API endpoints for 3D generation workflow."""

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from core.model_gen.shell_builder import ShellBuilder


router = APIRouter(prefix="/api/room-pipeline", tags=["room-pipeline"])


# In-memory job storage (replace with Redis in production)
jobs: dict[str, dict[str, Any]] = {}


class GenerateShellRequest(BaseModel):
    room_id: str
    room_data: dict[str, Any]


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    stage: str
    progress: float
    preview_url: str | None = None
    outputs: dict[str, Any] | None = None


@router.post("/generate-shell", response_model=JobResponse)
async def generate_shell(
    request: GenerateShellRequest,
    background_tasks: BackgroundTasks
) -> JobResponse:
    """Generate 3D shell from room data."""
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "stage": "SHELL_BUILDING",
        "progress": 0.0,
        "room_id": request.room_id,
        "room_data": request.room_data,
    }

    background_tasks.add_task(_build_shell, job_id, request.room_data)

    return JobResponse(job_id=job_id, status="SHELL_BUILDING")


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get status of a pipeline job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        stage=job["stage"],
        progress=job["progress"],
        preview_url=job.get("preview_url"),
        outputs=job.get("outputs"),
    )


async def _build_shell(job_id: str, room_data: dict[str, Any]) -> None:
    """Background task to build 3D shell."""
    try:
        builder = ShellBuilder(room_data)

        jobs[job_id]["progress"] = 0.5

        # Export to temp file (in production, upload to blob storage)
        output_path = f"/tmp/{job_id}_shell.glb"
        builder.export_gltf(output_path)

        jobs[job_id]["stage"] = "READY_FOR_FURNISH"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["outputs"] = {"shell_path": output_path}
    except Exception as e:
        jobs[job_id]["stage"] = "FAILED"
        jobs[job_id]["error"] = str(e)
```

**Step 4: Register router in main.py**

```python
# Add to api/main.py imports
from api.routes.room_pipeline import router as room_pipeline_router

# Add to router registration section
app.include_router(room_pipeline_router)
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_room_pipeline_api.py::TestRoomPipelineAPI::test_generate_shell_returns_job_id -v`

Expected: PASS

**Step 6: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add api/routes/room_pipeline.py tests/test_room_pipeline_api.py api/main.py
git commit -m "feat(api): add room pipeline endpoints for shell generation"
```

---

## Phase 5: Frontend Room Viewer

### Task 5.1: RoomViewer3D Component

**Files:**
- Create: `frontend/src/components/room-viewer/RoomViewer3D.tsx`
- Create: `frontend/src/components/room-viewer/index.ts`

**Step 1: Create the component**

```tsx
// frontend/src/components/room-viewer/RoomViewer3D.tsx
"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment } from "@react-three/drei";
import { Suspense, useState } from "react";
import * as THREE from "three";

interface RoomViewer3DProps {
  gltfUrl?: string;
  onWaypointAdd?: (position: [number, number, number]) => void;
  waypoints?: Waypoint[];
}

export interface Waypoint {
  id: string;
  position: [number, number, number];
  lookAt: [number, number, number];
  duration?: number;
}

function RoomModel({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

function WaypointMarkers({ waypoints }: { waypoints: Waypoint[] }) {
  return (
    <>
      {waypoints.map((wp, i) => (
        <mesh key={wp.id} position={wp.position}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshStandardMaterial color={i === 0 ? "#22c55e" : "#3b82f6"} />
        </mesh>
      ))}
    </>
  );
}

function LoadingFallback() {
  return (
    <mesh>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#666" wireframe />
    </mesh>
  );
}

export function RoomViewer3D({
  gltfUrl,
  onWaypointAdd,
  waypoints = []
}: RoomViewer3DProps) {
  const [viewMode, setViewMode] = useState<"orbit" | "firstPerson">("orbit");

  const handleCanvasClick = (event: THREE.Event) => {
    if (!onWaypointAdd) return;

    // Get click position on floor plane
    const intersect = event.intersections?.find(
      (i) => i.object.name?.includes("floor")
    );
    if (intersect) {
      const pos = intersect.point;
      onWaypointAdd([pos.x, 1.6, pos.z]); // Camera at eye height
    }
  };

  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{ position: [5, 5, 5], fov: 50 }}
        onClick={handleCanvasClick}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />

        <Suspense fallback={<LoadingFallback />}>
          {gltfUrl && <RoomModel url={gltfUrl} />}
          <WaypointMarkers waypoints={waypoints} />
          <Environment preset="apartment" />
        </Suspense>

        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          maxPolarAngle={Math.PI / 2}
        />

        <gridHelper args={[20, 20, "#444", "#222"]} />
      </Canvas>

      <div className="absolute top-4 right-4 flex gap-2">
        <button
          onClick={() => setViewMode("orbit")}
          className={`px-3 py-1 rounded ${
            viewMode === "orbit" ? "bg-blue-500 text-white" : "bg-gray-200"
          }`}
        >
          Orbit
        </button>
        <button
          onClick={() => setViewMode("firstPerson")}
          className={`px-3 py-1 rounded ${
            viewMode === "firstPerson" ? "bg-blue-500 text-white" : "bg-gray-200"
          }`}
        >
          First Person
        </button>
      </div>
    </div>
  );
}
```

**Step 2: Create index export**

```tsx
// frontend/src/components/room-viewer/index.ts
export { RoomViewer3D } from "./RoomViewer3D";
export type { Waypoint } from "./RoomViewer3D";
```

**Step 3: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add frontend/src/components/room-viewer/
git commit -m "feat(frontend): add RoomViewer3D component with orbit controls"
```

---

### Task 5.2: WaypointEditor Component

**Files:**
- Create: `frontend/src/components/room-viewer/WaypointEditor.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/room-viewer/WaypointEditor.tsx
"use client";

import { useState } from "react";
import type { Waypoint } from "./RoomViewer3D";

interface WaypointEditorProps {
  waypoints: Waypoint[];
  onWaypointsChange: (waypoints: Waypoint[]) => void;
  onPreviewWalkthrough: () => void;
}

export function WaypointEditor({
  waypoints,
  onWaypointsChange,
  onPreviewWalkthrough,
}: WaypointEditorProps) {
  const addWaypoint = (position: [number, number, number]) => {
    const newWaypoint: Waypoint = {
      id: crypto.randomUUID(),
      position,
      lookAt: [position[0], position[1], position[2] + 1], // Look forward
      duration: 3,
    };
    onWaypointsChange([...waypoints, newWaypoint]);
  };

  const removeWaypoint = (id: string) => {
    onWaypointsChange(waypoints.filter((w) => w.id !== id));
  };

  const updateDuration = (id: string, duration: number) => {
    onWaypointsChange(
      waypoints.map((w) => (w.id === id ? { ...w, duration } : w))
    );
  };

  const moveWaypoint = (id: string, direction: "up" | "down") => {
    const index = waypoints.findIndex((w) => w.id === id);
    if (
      (direction === "up" && index === 0) ||
      (direction === "down" && index === waypoints.length - 1)
    ) {
      return;
    }

    const newWaypoints = [...waypoints];
    const swapIndex = direction === "up" ? index - 1 : index + 1;
    [newWaypoints[index], newWaypoints[swapIndex]] = [
      newWaypoints[swapIndex],
      newWaypoints[index],
    ];
    onWaypointsChange(newWaypoints);
  };

  const totalDuration = waypoints.reduce((sum, w) => sum + (w.duration || 3), 0);

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold text-lg mb-4">Walkthrough Waypoints</h3>

      {waypoints.length === 0 ? (
        <p className="text-gray-500 text-sm">
          Click on the floor in the 3D view to add waypoints
        </p>
      ) : (
        <div className="space-y-2">
          {waypoints.map((wp, index) => (
            <div
              key={wp.id}
              className="flex items-center gap-2 p-2 bg-gray-50 rounded"
            >
              <span className="w-6 h-6 flex items-center justify-center bg-blue-500 text-white rounded-full text-sm">
                {index + 1}
              </span>

              <div className="flex-1">
                <span className="text-sm text-gray-600">
                  ({wp.position[0].toFixed(1)}, {wp.position[2].toFixed(1)})
                </span>
              </div>

              <input
                type="number"
                value={wp.duration || 3}
                onChange={(e) => updateDuration(wp.id, Number(e.target.value))}
                className="w-16 px-2 py-1 border rounded text-sm"
                min={1}
                max={30}
              />
              <span className="text-xs text-gray-500">sec</span>

              <button
                onClick={() => moveWaypoint(wp.id, "up")}
                disabled={index === 0}
                className="p-1 hover:bg-gray-200 rounded disabled:opacity-30"
              >
                ↑
              </button>
              <button
                onClick={() => moveWaypoint(wp.id, "down")}
                disabled={index === waypoints.length - 1}
                className="p-1 hover:bg-gray-200 rounded disabled:opacity-30"
              >
                ↓
              </button>
              <button
                onClick={() => removeWaypoint(wp.id)}
                className="p-1 hover:bg-red-100 text-red-500 rounded"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {waypoints.length >= 2 && (
        <div className="mt-4 pt-4 border-t">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm text-gray-600">
              Total duration: {totalDuration}s
            </span>
            <span className="text-sm text-gray-600">
              {waypoints.length} waypoints
            </span>
          </div>

          <button
            onClick={onPreviewWalkthrough}
            className="w-full py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Preview Walkthrough
          </button>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Update index export**

```tsx
// Update frontend/src/components/room-viewer/index.ts
export { RoomViewer3D } from "./RoomViewer3D";
export { WaypointEditor } from "./WaypointEditor";
export type { Waypoint } from "./RoomViewer3D";
```

**Step 3: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add frontend/src/components/room-viewer/
git commit -m "feat(frontend): add WaypointEditor for walkthrough path editing"
```

---

## Phase 6: Blender Integration

### Task 6.1: Blender Renderer Service

**Files:**
- Create: `core/render/blender_renderer.py`
- Create: `core/render/blender_scripts/render_room.py`
- Create: `tests/test_blender_renderer.py`

**Step 1: Write the test**

```python
# tests/test_blender_renderer.py
import pytest
from unittest.mock import patch, MagicMock
from core.render.blender_renderer import BlenderRenderer, RenderConfig


class TestBlenderRenderer:
    """Tests for Blender rendering service."""

    def test_render_config_defaults(self):
        """RenderConfig should have sensible defaults."""
        config = RenderConfig(gltf_path="/tmp/test.glb")

        assert config.engine == "EEVEE"
        assert config.resolution == (1920, 1080)
        assert config.samples == 64

    def test_generates_render_script(self):
        """Should generate valid Blender Python script."""
        renderer = BlenderRenderer()
        config = RenderConfig(
            gltf_path="/tmp/room.glb",
            output_path="/tmp/render.png",
            camera_position=(5, 2, 5),
            camera_look_at=(0, 1, 0),
        )

        script = renderer._generate_script(config)

        assert "import bpy" in script
        assert "/tmp/room.glb" in script
        assert "/tmp/render.png" in script
        assert "camera" in script.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_blender_renderer.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

```python
# core/render/blender_renderer.py
"""Blender rendering service for high-quality room renders."""

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RenderConfig:
    """Configuration for a render job."""
    gltf_path: str
    output_path: str = ""
    engine: str = "EEVEE"  # EEVEE or CYCLES
    resolution: tuple[int, int] = (1920, 1080)
    samples: int = 64  # For Cycles
    camera_position: tuple[float, float, float] = (5, 2, 5)
    camera_look_at: tuple[float, float, float] = (0, 1, 0)
    hdri_path: str | None = None


class BlenderRenderer:
    """Renders rooms using Blender in headless mode."""

    def __init__(self, blender_path: str = "blender"):
        self.blender_path = blender_path

    async def render(self, config: RenderConfig) -> bytes:
        """Render a room and return the image bytes."""
        script = self._generate_script(config)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            # Run Blender in background mode
            result = subprocess.run(
                [
                    self.blender_path,
                    "--background",
                    "--python", script_path,
                ],
                capture_output=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Blender failed: {result.stderr.decode()}")

            # Read output file
            return Path(config.output_path).read_bytes()
        finally:
            Path(script_path).unlink(missing_ok=True)

    def _generate_script(self, config: RenderConfig) -> str:
        """Generate Blender Python script for rendering."""
        return f'''
import bpy
import math

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import glTF
bpy.ops.import_scene.gltf(filepath="{config.gltf_path}")

# Set up render engine
bpy.context.scene.render.engine = "BLENDER_{config.engine}"
bpy.context.scene.render.resolution_x = {config.resolution[0]}
bpy.context.scene.render.resolution_y = {config.resolution[1]}

if "{config.engine}" == "CYCLES":
    bpy.context.scene.cycles.samples = {config.samples}
    bpy.context.scene.cycles.use_denoising = True

# Create camera
bpy.ops.object.camera_add(location={config.camera_position})
camera = bpy.context.active_object
bpy.context.scene.camera = camera

# Point camera at target
direction = mathutils.Vector({config.camera_look_at}) - mathutils.Vector({config.camera_position})
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()

# Add basic lighting
bpy.ops.object.light_add(type='SUN', location=(10, 10, 10))
sun = bpy.context.active_object
sun.data.energy = 3

# Add ambient light via world
bpy.context.scene.world = bpy.data.worlds.new("World")
bpy.context.scene.world.use_nodes = True
bg = bpy.context.scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.8, 0.8, 0.85, 1.0)  # Light gray ambient
bg.inputs[1].default_value = 0.5  # Strength

# Render
bpy.context.scene.render.filepath = "{config.output_path}"
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)

print("Render complete: {config.output_path}")
'''
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_blender_renderer.py -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/render/blender_renderer.py tests/test_blender_renderer.py
git commit -m "feat(render): add BlenderRenderer service for high-quality renders"
```

---

## Phase 7: Video Walkthrough

### Task 7.1: Camera Path Interpolation

**Files:**
- Create: `core/walkthrough/camera_path.py`
- Create: `tests/test_camera_path.py`

**Step 1: Write the failing test**

```python
# tests/test_camera_path.py
import pytest
import numpy as np
from core.walkthrough.camera_path import CameraPath, Waypoint


class TestCameraPath:
    """Tests for camera path interpolation."""

    def test_interpolates_between_two_waypoints(self):
        """Should interpolate position between two waypoints."""
        waypoints = [
            Waypoint(position=(0, 1.6, 0), look_at=(0, 1.6, 1), duration=2),
            Waypoint(position=(5, 1.6, 0), look_at=(5, 1.6, 1), duration=2),
        ]

        path = CameraPath(waypoints)

        # At t=0, should be at first waypoint
        pos, look = path.get_frame(0)
        assert np.allclose(pos, [0, 1.6, 0], atol=0.01)

        # At t=0.5, should be roughly midway
        pos, look = path.get_frame(0.5)
        assert np.allclose(pos[0], 2.5, atol=0.5)  # x should be ~2.5

        # At t=1, should be at last waypoint
        pos, look = path.get_frame(1.0)
        assert np.allclose(pos, [5, 1.6, 0], atol=0.01)

    def test_calculates_total_duration(self):
        """Should sum durations of all waypoints."""
        waypoints = [
            Waypoint(position=(0, 0, 0), look_at=(0, 0, 1), duration=3),
            Waypoint(position=(1, 0, 0), look_at=(1, 0, 1), duration=5),
            Waypoint(position=(2, 0, 0), look_at=(2, 0, 1), duration=2),
        ]

        path = CameraPath(waypoints)

        assert path.total_duration == 10
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_camera_path.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

```python
# core/walkthrough/camera_path.py
"""Camera path interpolation for video walkthroughs."""

from dataclasses import dataclass
import numpy as np
from scipy.interpolate import CubicSpline


@dataclass
class Waypoint:
    """A waypoint in the camera path."""
    position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    duration: float = 3.0  # seconds to reach this point from previous


class CameraPath:
    """Smooth camera path through waypoints using cubic spline interpolation."""

    def __init__(self, waypoints: list[Waypoint]):
        if len(waypoints) < 2:
            raise ValueError("Need at least 2 waypoints")

        self.waypoints = waypoints
        self._build_splines()

    @property
    def total_duration(self) -> float:
        """Total duration of the path in seconds."""
        return sum(w.duration for w in self.waypoints)

    def _build_splines(self) -> None:
        """Build cubic splines for position and look_at interpolation."""
        # Calculate cumulative time at each waypoint
        times = [0.0]
        for wp in self.waypoints[1:]:
            times.append(times[-1] + wp.duration)

        # Normalize times to [0, 1]
        total = times[-1]
        self.times = [t / total for t in times]

        # Extract position and look_at arrays
        positions = np.array([wp.position for wp in self.waypoints])
        look_ats = np.array([wp.look_at for wp in self.waypoints])

        # Create cubic splines for each coordinate
        self.pos_spline = CubicSpline(self.times, positions)
        self.look_spline = CubicSpline(self.times, look_ats)

    def get_frame(self, t: float) -> tuple[np.ndarray, np.ndarray]:
        """
        Get camera position and look_at at normalized time t.

        Args:
            t: Normalized time [0, 1]

        Returns:
            (position, look_at) as numpy arrays
        """
        t = np.clip(t, 0, 1)
        return self.pos_spline(t), self.look_spline(t)

    def get_frames(self, fps: int = 30) -> list[tuple[np.ndarray, np.ndarray]]:
        """
        Get all frames for the entire path at given FPS.

        Returns:
            List of (position, look_at) tuples
        """
        total_frames = int(self.total_duration * fps)
        frames = []

        for i in range(total_frames):
            t = i / (total_frames - 1) if total_frames > 1 else 0
            frames.append(self.get_frame(t))

        return frames
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_camera_path.py -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
mkdir -p core/walkthrough
git add core/walkthrough/camera_path.py tests/test_camera_path.py
git commit -m "feat(walkthrough): add CameraPath with cubic spline interpolation"
```

---

### Task 7.2: Video Generator

**Files:**
- Create: `core/walkthrough/video_generator.py`
- Create: `tests/test_video_generator.py`

**Step 1: Write the failing test**

```python
# tests/test_video_generator.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.walkthrough.video_generator import VideoGenerator
from core.walkthrough.camera_path import CameraPath, Waypoint


class TestVideoGenerator:
    """Tests for video walkthrough generation."""

    def test_calculates_frame_count_from_duration(self):
        """Should calculate correct frame count based on duration and FPS."""
        waypoints = [
            Waypoint(position=(0, 1.6, 0), look_at=(0, 1.6, 1), duration=3),
            Waypoint(position=(5, 1.6, 0), look_at=(5, 1.6, 1), duration=2),
        ]
        path = CameraPath(waypoints)

        generator = VideoGenerator(fps=30)
        frame_count = generator._calculate_frame_count(path)

        # 5 seconds at 30fps = 150 frames
        assert frame_count == 150

    @pytest.mark.asyncio
    async def test_generates_video_from_waypoints(self):
        """Should orchestrate frame rendering and video encoding."""
        waypoints = [
            Waypoint(position=(0, 1.6, 0), look_at=(0, 1.6, 1), duration=1),
            Waypoint(position=(2, 1.6, 0), look_at=(2, 1.6, 1), duration=1),
        ]

        generator = VideoGenerator(fps=10)  # Low FPS for testing

        with patch.object(generator, '_render_frame', new_callable=AsyncMock) as mock_render:
            with patch.object(generator, '_encode_video') as mock_encode:
                mock_render.return_value = b"fake_frame"
                mock_encode.return_value = "/tmp/output.mp4"

                result = await generator.generate(
                    gltf_path="/tmp/room.glb",
                    waypoints=waypoints,
                    output_path="/tmp/output.mp4",
                )

                # Should render frames (2 seconds at 10fps = 20 frames)
                assert mock_render.call_count == 20
                assert mock_encode.called
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_video_generator.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

```python
# core/walkthrough/video_generator.py
"""Video walkthrough generation from camera paths."""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from core.render.blender_renderer import BlenderRenderer, RenderConfig
from core.walkthrough.camera_path import CameraPath, Waypoint


class VideoGenerator:
    """Generates video walkthroughs by rendering frames and encoding."""

    def __init__(
        self,
        fps: int = 30,
        resolution: tuple[int, int] = (1920, 1080),
        blender_renderer: BlenderRenderer | None = None,
    ):
        self.fps = fps
        self.resolution = resolution
        self.renderer = blender_renderer or BlenderRenderer()

    async def generate(
        self,
        gltf_path: str,
        waypoints: list[Waypoint],
        output_path: str,
    ) -> str:
        """
        Generate a video walkthrough.

        Args:
            gltf_path: Path to the room glTF file
            waypoints: List of camera waypoints
            output_path: Output video file path

        Returns:
            Path to the generated video
        """
        path = CameraPath(waypoints)
        frame_count = self._calculate_frame_count(path)

        # Create temp directory for frames
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Render all frames
            frames = path.get_frames(self.fps)
            for i, (position, look_at) in enumerate(frames):
                frame_path = temp_path / f"frame_{i:05d}.png"
                await self._render_frame(
                    gltf_path=gltf_path,
                    position=tuple(position),
                    look_at=tuple(look_at),
                    output_path=str(frame_path),
                )

            # Encode video
            return self._encode_video(temp_path, output_path)

    def _calculate_frame_count(self, path: CameraPath) -> int:
        """Calculate total number of frames needed."""
        return int(path.total_duration * self.fps)

    async def _render_frame(
        self,
        gltf_path: str,
        position: tuple[float, float, float],
        look_at: tuple[float, float, float],
        output_path: str,
    ) -> bytes:
        """Render a single frame using Blender."""
        config = RenderConfig(
            gltf_path=gltf_path,
            output_path=output_path,
            engine="EEVEE",  # Fast for video frames
            resolution=self.resolution,
            camera_position=position,
            camera_look_at=look_at,
        )
        return await self.renderer.render(config)

    def _encode_video(self, frames_dir: Path, output_path: str) -> str:
        """Encode frames to video using FFmpeg."""
        frame_pattern = str(frames_dir / "frame_%05d.png")

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-framerate", str(self.fps),
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-crf", "18",  # High quality
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr.decode()}")

        return output_path
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_video_generator.py -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/walkthrough/video_generator.py tests/test_video_generator.py
git commit -m "feat(walkthrough): add VideoGenerator for walkthrough rendering"
```

---

## Phase 8: Integration

### Task 8.1: Complete Pipeline Test

**Files:**
- Create: `tests/test_room_pipeline_integration.py`

**Step 1: Write integration test**

```python
# tests/test_room_pipeline_integration.py
import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch

from core.model_gen.shell_builder import ShellBuilder
from core.model_gen.furniture_placer import FurniturePlacer
from core.materials.texture_generator import TextureGenerator


class TestRoomPipelineIntegration:
    """Integration tests for the complete room pipeline."""

    @pytest.mark.asyncio
    async def test_complete_pipeline_generates_furnished_room(self):
        """Full pipeline should produce a textured, furnished room glTF."""
        # 1. Define room
        room_data = {
            "id": "test_room",
            "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "doors": [{"wall_index": 0, "position": 2.0, "width": 0.9, "height": 2.1}],
            "windows": [{"wall_index": 2, "position": 1.5, "width": 1.2, "height": 1.4, "sill_height": 0.9}],
        }

        # 2. Build shell
        builder = ShellBuilder(room_data)

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            shell_path = f.name

        try:
            builder.export_gltf(shell_path)
            assert os.path.exists(shell_path)
            assert os.path.getsize(shell_path) > 0

            # 3. Get furniture plan (mocked)
            room_context = {
                "room_type": "bedroom",
                "dimensions": {"width": 5, "depth": 4, "height": 2.7},
                "doors": [{"wall": "south", "position": 2.0}],
                "windows": [{"wall": "north", "position": 1.5}],
                "style": "scandinavian",
            }

            mock_furniture_plan = {
                "furniture": [
                    {"type": "bed_queen", "position": [2.5, 0, 3.0], "rotation": 0},
                    {"type": "nightstand", "position": [0.8, 0, 3.0], "rotation": 0},
                ]
            }

            with patch.object(FurniturePlacer, '_call_llm', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = mock_furniture_plan

                placer = FurniturePlacer()
                plan = await placer.generate_plan(room_context)

                assert len(plan["furniture"]) == 2
                assert plan["furniture"][0]["type"] == "bed_queen"

            # 4. Generate textures (mocked)
            from PIL import Image
            import io

            mock_texture = Image.new("RGB", (512, 512), color="brown")
            img_bytes = io.BytesIO()
            mock_texture.save(img_bytes, format="PNG")

            with patch.object(TextureGenerator, '_call_dalle', new_callable=AsyncMock) as mock_dalle:
                mock_dalle.return_value = img_bytes.getvalue()

                generator = TextureGenerator()
                texture = await generator.generate("oak flooring", "scandinavian")

                assert texture is not None
                assert len(texture) > 0

        finally:
            os.unlink(shell_path)


    def test_shell_builder_handles_l_shaped_room(self):
        """Shell builder should handle non-rectangular polygons."""
        # L-shaped room
        room_data = {
            "id": "l_room",
            "polygon": [
                [0, 0], [6, 0], [6, 3], [3, 3], [3, 5], [0, 5]
            ],
        }

        builder = ShellBuilder(room_data)
        shell = builder.build_shell()

        # Should have floor, ceiling, and 6 walls
        assert "floor" in shell.geometry
        assert "ceiling" in shell.geometry
        # At least some walls
        wall_count = sum(1 for name in shell.geometry if "wall" in name)
        assert wall_count == 6
```

**Step 2: Run integration test**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/test_room_pipeline_integration.py -v`

Expected: PASS

**Step 3: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add tests/test_room_pipeline_integration.py
git commit -m "test: add integration tests for complete room pipeline"
```

---

### Task 8.2: Update Module Exports

**Files:**
- Create: `core/model_gen/__init__.py`
- Create: `core/walkthrough/__init__.py`
- Update: `core/render/__init__.py`

**Step 1: Create/update init files**

```python
# core/model_gen/__init__.py
"""3D model generation from floor plan data."""

from .shell_builder import ShellBuilder
from .furniture_placer import FurniturePlacer
from .furniture_library import FurnitureLibrary

__all__ = ["ShellBuilder", "FurniturePlacer", "FurnitureLibrary"]
```

```python
# core/walkthrough/__init__.py
"""Video walkthrough generation."""

from .camera_path import CameraPath, Waypoint
from .video_generator import VideoGenerator

__all__ = ["CameraPath", "Waypoint", "VideoGenerator"]
```

```python
# core/render/__init__.py (update if exists, create if not)
"""Rendering services."""

from .blender_renderer import BlenderRenderer, RenderConfig

__all__ = ["BlenderRenderer", "RenderConfig"]
```

**Step 2: Commit**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git add core/model_gen/__init__.py core/walkthrough/__init__.py core/render/__init__.py
git commit -m "chore: add module exports for model_gen, walkthrough, render"
```

---

### Task 8.3: Run Full Test Suite

**Step 1: Run all tests**

Run: `cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline && source .venv/bin/activate && pytest tests/ -m "not integration" -v --tb=short`

Expected: All tests pass

**Step 2: Final commit for phase completion**

```bash
cd /Users/hitesh.gupta/archviz-ai/.worktrees/render-pipeline
git log --oneline -10  # Review commits
```

---

## Summary

This plan implements the Single Room MVP in 8 phases:

1. **3D Shell Generation** (Tasks 1.1-1.5) - Procedural room geometry with trimesh
2. **AI Furniture Placement** (Tasks 2.1-2.2) - GPT-4 layout planning + asset library
3. **AI Texture Generation** (Task 3.1) - DALL-E 3 tileable textures with caching
4. **API Endpoints** (Task 4.1) - Room pipeline REST API
5. **Frontend Room Viewer** (Tasks 5.1-5.2) - Three.js viewer with waypoint editing
6. **Blender Integration** (Task 6.1) - High-quality rendering service
7. **Video Walkthrough** (Tasks 7.1-7.2) - Camera path interpolation and video encoding
8. **Integration** (Tasks 8.1-8.3) - End-to-end testing and module exports

Each task follows TDD: write failing test → verify failure → implement → verify pass → commit.
