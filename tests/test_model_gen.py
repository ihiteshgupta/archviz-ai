"""Tests for the 3D model generation module."""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
import trimesh

from core.dwg_parser.elements import Door, DoorSwing, Room, Wall, Window, WindowType
from core.dwg_parser.parser import FloorPlan, FloorPlanMetadata
from core.model_gen import (
    FloorCeilingExtruder,
    GeneratorConfig,
    Mesh3D,
    ModelGenerator,
    OpeningProcessor,
    Scene3D,
    SceneExporter,
    WallExtruder,
    export_scene,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def simple_wall():
    """A simple two-point wall."""
    return Wall(
        id="wall1",
        points=[(0.0, 0.0), (5.0, 0.0)],
        thickness=0.2,
        height=3.0,
        is_exterior=True,
    )


@pytest.fixture
def multi_point_wall():
    """An L-shaped wall with three points."""
    return Wall(
        id="wall2",
        points=[(0.0, 0.0), (5.0, 0.0), (5.0, 3.0)],
        thickness=0.15,
        height=2.8,
        is_exterior=False,
    )


@pytest.fixture
def simple_room():
    """A simple rectangular room."""
    return Room(
        id="room1",
        name="Living Room",
        polygon=[(0.0, 0.0), (5.0, 0.0), (5.0, 4.0), (0.0, 4.0)],
        floor_level=0,
        ceiling_height=3.0,
        room_type="living",
    )


@pytest.fixture
def simple_door():
    """A simple door element."""
    return Door(
        id="door1",
        position=(2.5, 0.0),
        width=0.9,
        height=2.1,
        swing=DoorSwing.LEFT,
        angle=0.0,
        wall_id="wall1",
    )


@pytest.fixture
def simple_window():
    """A simple window element."""
    return Window(
        id="window1",
        position=(1.0, 0.0),
        width=1.2,
        height=1.5,
        sill_height=0.9,
        window_type=WindowType.SINGLE,
        angle=0.0,
        wall_id="wall1",
    )


@pytest.fixture
def simple_floor_plan(simple_wall, simple_room, simple_door, simple_window):
    """A simple floor plan with one wall, room, door, and window."""
    return FloorPlan(
        metadata=FloorPlanMetadata(
            filename="test.dxf",
            units="meters",
            scale=1.0,
        ),
        walls=[simple_wall],
        doors=[simple_door],
        windows=[simple_window],
        rooms=[simple_room],
    )


# ============================================================================
# Mesh3D Tests
# ============================================================================


class TestMesh3D:
    """Tests for Mesh3D dataclass."""

    def test_create_empty_mesh(self):
        """Test creating an empty mesh."""
        mesh = Mesh3D()
        assert mesh.vertices.size == 0
        assert mesh.faces.size == 0
        assert mesh.material_id == "default"

    def test_create_mesh_with_data(self):
        """Test creating a mesh with vertices and faces."""
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        mesh = Mesh3D(
            vertices=vertices,
            faces=faces,
            material_id="wall_exterior",
            element_type="walls",
            source_id="wall1",
        )
        assert mesh.vertices.shape == (3, 3)
        assert mesh.faces.shape == (1, 3)
        assert mesh.material_id == "wall_exterior"

    def test_to_trimesh(self):
        """Test conversion to trimesh object."""
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        mesh = Mesh3D(
            vertices=vertices,
            faces=faces,
            material_id="test_mat",
            element_type="test_type",
            source_id="test_source",
        )
        tm = mesh.to_trimesh()
        assert isinstance(tm, trimesh.Trimesh)
        assert len(tm.vertices) == 3
        assert tm.metadata["material_id"] == "test_mat"

    def test_from_trimesh(self):
        """Test creation from trimesh object."""
        tm = trimesh.creation.box(extents=[1, 1, 1])
        mesh = Mesh3D.from_trimesh(
            tm, material_id="box_mat", element_type="box", source_id="box1"
        )
        assert mesh.vertices.shape[0] == len(tm.vertices)
        assert mesh.material_id == "box_mat"


# ============================================================================
# Scene3D Tests
# ============================================================================


class TestScene3D:
    """Tests for Scene3D dataclass."""

    def test_create_empty_scene(self):
        """Test creating an empty scene."""
        scene = Scene3D()
        assert len(scene.meshes) == 0
        assert scene.floor_count == 1

    def test_add_mesh(self):
        """Test adding meshes to scene."""
        scene = Scene3D()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        mesh = Mesh3D(
            vertices=vertices, faces=faces, element_type="walls", source_id="wall1"
        )
        scene.add_mesh(mesh)
        assert "walls" in scene.meshes
        assert len(scene.meshes["walls"]) == 1

    def test_get_by_type(self):
        """Test getting meshes by element type."""
        scene = Scene3D()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])

        wall_mesh = Mesh3D(vertices=vertices, faces=faces, element_type="walls")
        floor_mesh = Mesh3D(vertices=vertices, faces=faces, element_type="floors")

        scene.add_mesh(wall_mesh)
        scene.add_mesh(floor_mesh)

        walls = scene.get_by_type("walls")
        assert len(walls) == 1
        floors = scene.get_by_type("floors")
        assert len(floors) == 1
        ceilings = scene.get_by_type("ceilings")
        assert len(ceilings) == 0

    def test_get_by_source(self):
        """Test getting meshes by source ID."""
        scene = Scene3D()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])

        mesh1 = Mesh3D(vertices=vertices, faces=faces, element_type="walls", source_id="wall1")
        mesh2 = Mesh3D(vertices=vertices, faces=faces, element_type="door_frames", source_id="door1")

        scene.add_mesh(mesh1)
        scene.add_mesh(mesh2)

        wall_meshes = scene.get_by_source("wall1")
        assert len(wall_meshes) == 1

    def test_bounds_calculation(self):
        """Test scene bounds calculation."""
        scene = Scene3D()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 2]])
        faces = np.array([[0, 1, 2], [0, 1, 3]])
        mesh = Mesh3D(vertices=vertices, faces=faces, element_type="walls")
        scene.add_mesh(mesh)

        min_bound, max_bound = scene.bounds
        assert min_bound[0] == pytest.approx(0.0)
        assert max_bound[0] == pytest.approx(1.0)
        assert max_bound[2] == pytest.approx(2.0)


# ============================================================================
# WallExtruder Tests
# ============================================================================


class TestWallExtruder:
    """Tests for WallExtruder class."""

    def test_extrude_simple_wall(self, simple_wall):
        """Test extruding a simple two-point wall."""
        extruder = WallExtruder()
        mesh = extruder.extrude_wall(simple_wall)

        assert mesh is not None
        assert mesh.vertices.shape[0] == 8  # 4 bottom + 4 top
        assert mesh.faces.shape[0] == 12  # 6 faces × 2 triangles
        assert mesh.element_type == "walls"
        assert mesh.source_id == "wall1"
        assert mesh.material_id == "wall_exterior"

    def test_extrude_multi_point_wall(self, multi_point_wall):
        """Test extruding a multi-point wall."""
        extruder = WallExtruder()
        mesh = extruder.extrude_wall(multi_point_wall)

        assert mesh is not None
        assert mesh.vertices.shape[0] > 0
        assert mesh.material_id == "wall_interior"

    def test_extrude_invalid_wall(self):
        """Test extruding a wall with insufficient points."""
        extruder = WallExtruder()
        wall = Wall(id="invalid", points=[(0.0, 0.0)])
        mesh = extruder.extrude_wall(wall)
        assert mesh is None

    def test_wall_height(self, simple_wall):
        """Test that wall mesh has correct height."""
        extruder = WallExtruder()
        mesh = extruder.extrude_wall(simple_wall)

        z_values = mesh.vertices[:, 2]
        assert np.min(z_values) == pytest.approx(0.0)
        assert np.max(z_values) == pytest.approx(simple_wall.height)


# ============================================================================
# FloorCeilingExtruder Tests
# ============================================================================


class TestFloorCeilingExtruder:
    """Tests for FloorCeilingExtruder class."""

    def test_extrude_floor(self, simple_room):
        """Test extruding a floor from room polygon."""
        extruder = FloorCeilingExtruder(floor_thickness=0.15)
        mesh = extruder.extrude_floor(simple_room)

        assert mesh is not None
        assert mesh.element_type == "floors"
        assert mesh.material_id == "floor_default"
        assert mesh.source_id == "room1"

    def test_extrude_ceiling(self, simple_room):
        """Test extruding a ceiling from room polygon."""
        extruder = FloorCeilingExtruder()
        mesh = extruder.extrude_ceiling(simple_room)

        assert mesh is not None
        assert mesh.element_type == "ceilings"
        assert mesh.material_id == "ceiling_default"

    def test_ceiling_height(self, simple_room):
        """Test that ceiling is at correct height."""
        extruder = FloorCeilingExtruder(ceiling_thickness=0.05)
        mesh = extruder.extrude_ceiling(simple_room)

        z_values = mesh.vertices[:, 2]
        assert np.min(z_values) == pytest.approx(simple_room.ceiling_height)

    def test_invalid_room(self):
        """Test extruding from invalid room polygon."""
        extruder = FloorCeilingExtruder()
        room = Room(id="invalid", polygon=[(0, 0), (1, 0)])  # Only 2 points
        mesh = extruder.extrude_floor(room)
        assert mesh is None


# ============================================================================
# OpeningProcessor Tests
# ============================================================================


class TestOpeningProcessor:
    """Tests for OpeningProcessor class."""

    def test_create_cutting_box(self):
        """Test creating a cutting box for openings."""
        processor = OpeningProcessor()
        box = processor.create_cutting_box(
            position=(2.5, 0.0),
            width=0.9,
            height=2.1,
            angle=0.0,
            wall_thickness=0.2,
            bottom_offset=0.0,
        )

        assert isinstance(box, trimesh.Trimesh)
        assert box.is_watertight

    def test_create_door_geometry(self, simple_door):
        """Test creating door frame and panel."""
        processor = OpeningProcessor()
        meshes = processor.create_door_geometry(simple_door, wall_thickness=0.2)

        assert len(meshes) == 4  # left jamb, right jamb, header, panel

        element_types = [m.element_type for m in meshes]
        assert "door_frames" in element_types
        assert "door_panels" in element_types

    def test_create_window_geometry(self, simple_window):
        """Test creating window frame and glass."""
        processor = OpeningProcessor()
        meshes = processor.create_window_geometry(simple_window, wall_thickness=0.2)

        assert len(meshes) == 5  # 4 frame pieces + glass

        element_types = [m.element_type for m in meshes]
        assert "window_frames" in element_types
        assert "window_glass" in element_types

        # Check glass has correct material
        glass_meshes = [m for m in meshes if m.element_type == "window_glass"]
        assert len(glass_meshes) == 1
        assert glass_meshes[0].material_id == "glass"

    def test_find_parent_wall(self, simple_wall):
        """Test finding parent wall for an opening."""
        processor = OpeningProcessor()
        walls = [simple_wall]

        # Position on the wall
        found = processor.find_parent_wall((2.5, 0.0), walls)
        assert found is not None
        assert found.id == "wall1"

        # Position far from wall
        found = processor.find_parent_wall((10.0, 10.0), walls)
        assert found is None


# ============================================================================
# ModelGenerator Tests
# ============================================================================


class TestModelGenerator:
    """Tests for ModelGenerator class."""

    def test_generate_simple_scene(self, simple_floor_plan):
        """Test generating a complete scene from floor plan."""
        generator = ModelGenerator()
        # Disable boolean cutting for simpler test
        generator.config.cut_openings = False
        scene = generator.generate(simple_floor_plan)

        assert isinstance(scene, Scene3D)
        assert len(scene.meshes) > 0
        assert "walls" in scene.meshes
        assert "floors" in scene.meshes
        assert "ceilings" in scene.meshes

    def test_generate_with_doors_windows(self, simple_floor_plan):
        """Test generation includes door and window geometry."""
        generator = ModelGenerator()
        generator.config.cut_openings = False  # Disable for test simplicity
        scene = generator.generate(simple_floor_plan)

        assert "door_frames" in scene.meshes
        assert "door_panels" in scene.meshes
        assert "window_frames" in scene.meshes
        assert "window_glass" in scene.meshes

    def test_generator_config(self):
        """Test custom generator configuration."""
        config = GeneratorConfig(
            default_wall_height=2.5,
            generate_ceilings=False,
        )
        generator = ModelGenerator(config)

        assert generator.config.default_wall_height == 2.5
        assert generator.config.generate_ceilings is False

    def test_multi_floor_support(self):
        """Test multi-floor scene generation."""
        # Create rooms on different floors
        room1 = Room(
            id="room1",
            polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
            floor_level=0,
            ceiling_height=3.0,
        )
        room2 = Room(
            id="room2",
            polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
            floor_level=1,
            ceiling_height=3.0,
        )

        floor_plan = FloorPlan(
            metadata=FloorPlanMetadata(),
            walls=[],
            rooms=[room1, room2],
        )

        generator = ModelGenerator()
        scene = generator.generate(floor_plan)

        assert scene.floor_count == 2


# ============================================================================
# Export Tests
# ============================================================================


class TestExport:
    """Tests for export functionality."""

    def test_export_gltf(self, simple_floor_plan):
        """Test exporting scene to GLB format."""
        generator = ModelGenerator()
        generator.config.cut_openings = False
        scene = generator.generate(simple_floor_plan)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.glb")
            scene.export_gltf(path, binary=True)

            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

    def test_export_obj(self, simple_floor_plan):
        """Test exporting scene to OBJ format."""
        generator = ModelGenerator()
        generator.config.cut_openings = False
        scene = generator.generate(simple_floor_plan)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.obj")
            scene.export_obj(path)

            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

    def test_export_scene_function(self, simple_floor_plan):
        """Test convenience export function."""
        generator = ModelGenerator()
        generator.config.cut_openings = False
        scene = generator.generate(simple_floor_plan)

        with tempfile.TemporaryDirectory() as tmpdir:
            results = export_scene(scene, tmpdir, name="test_model")

            assert "glb" in results
            assert "obj" in results
            assert os.path.exists(results["glb"])
            assert os.path.exists(results["obj"])

    def test_scene_exporter_materials(self, simple_floor_plan):
        """Test that exported files include material information."""
        generator = ModelGenerator()
        generator.config.cut_openings = False
        scene = generator.generate(simple_floor_plan)

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = SceneExporter()
            obj_path = os.path.join(tmpdir, "model.obj")
            exporter.export_obj(scene, obj_path)

            mtl_path = os.path.join(tmpdir, "model.mtl")
            assert os.path.exists(mtl_path)

            # Check MTL file has material definitions
            with open(mtl_path) as f:
                content = f.read()
                assert "newmtl" in content


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for full pipeline."""

    def test_full_pipeline(self):
        """Test complete pipeline from floor plan to export."""
        # Create a simple house floor plan
        walls = [
            Wall(id="w1", points=[(0, 0), (10, 0)], thickness=0.3, height=3.0, is_exterior=True),
            Wall(id="w2", points=[(10, 0), (10, 8)], thickness=0.3, height=3.0, is_exterior=True),
            Wall(id="w3", points=[(10, 8), (0, 8)], thickness=0.3, height=3.0, is_exterior=True),
            Wall(id="w4", points=[(0, 8), (0, 0)], thickness=0.3, height=3.0, is_exterior=True),
            Wall(id="w5", points=[(5, 0), (5, 8)], thickness=0.15, height=3.0, is_exterior=False),
        ]

        rooms = [
            Room(
                id="r1",
                name="Living Room",
                polygon=[(0, 0), (5, 0), (5, 8), (0, 8)],
                ceiling_height=3.0,
                room_type="living",
            ),
            Room(
                id="r2",
                name="Bedroom",
                polygon=[(5, 0), (10, 0), (10, 8), (5, 8)],
                ceiling_height=3.0,
                room_type="bedroom",
            ),
        ]

        doors = [
            Door(id="d1", position=(5, 4), width=0.9, height=2.1, wall_id="w5"),
        ]

        windows = [
            Window(id="win1", position=(2.5, 0), width=1.5, height=1.5, sill_height=0.9, wall_id="w1"),
            Window(id="win2", position=(7.5, 0), width=1.5, height=1.5, sill_height=0.9, wall_id="w1"),
        ]

        floor_plan = FloorPlan(
            metadata=FloorPlanMetadata(filename="house.dxf", units="meters"),
            walls=walls,
            rooms=rooms,
            doors=doors,
            windows=windows,
        )

        # Generate model
        config = GeneratorConfig(cut_openings=False)  # Disable for test stability
        generator = ModelGenerator(config)
        scene = generator.generate(floor_plan)

        # Verify scene structure
        assert len(scene.meshes) > 0
        assert len(scene.get_by_type("walls")) == 5
        assert len(scene.get_by_type("floors")) == 2
        assert len(scene.get_by_type("ceilings")) == 2

        # Export and verify
        with tempfile.TemporaryDirectory() as tmpdir:
            results = export_scene(scene, tmpdir, name="house")

            # Verify GLB can be loaded
            loaded = trimesh.load(results["glb"])
            assert loaded is not None

    def test_empty_floor_plan(self):
        """Test handling of empty floor plan."""
        floor_plan = FloorPlan(metadata=FloorPlanMetadata())

        generator = ModelGenerator()
        scene = generator.generate(floor_plan)

        assert len(scene.get_all_meshes()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
