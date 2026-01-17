"""Data types for 3D model generation."""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import trimesh

Point3D = Tuple[float, float, float]


@dataclass
class Mesh3D:
    """Individual mesh with vertices, faces, and metadata."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    vertices: np.ndarray = field(default_factory=lambda: np.array([]))
    faces: np.ndarray = field(default_factory=lambda: np.array([]))
    normals: Optional[np.ndarray] = None
    material_id: str = "default"
    element_type: str = "generic"  # wall, floor, ceiling, door_frame, etc.
    source_id: str = ""  # Original element ID from FloorPlan

    def to_trimesh(self) -> trimesh.Trimesh:
        """Convert to trimesh object."""
        if self.vertices.size == 0 or self.faces.size == 0:
            return trimesh.Trimesh()
        mesh = trimesh.Trimesh(vertices=self.vertices, faces=self.faces)
        mesh.metadata["material_id"] = self.material_id
        mesh.metadata["element_type"] = self.element_type
        mesh.metadata["source_id"] = self.source_id
        return mesh

    @classmethod
    def from_trimesh(
        cls,
        mesh: trimesh.Trimesh,
        material_id: str = "default",
        element_type: str = "generic",
        source_id: str = "",
    ) -> "Mesh3D":
        """Create Mesh3D from trimesh object."""
        return cls(
            vertices=np.array(mesh.vertices),
            faces=np.array(mesh.faces),
            normals=np.array(mesh.vertex_normals) if hasattr(mesh, "vertex_normals") else None,
            material_id=material_id,
            element_type=element_type,
            source_id=source_id,
        )


@dataclass
class Scene3D:
    """Complete 3D scene with organized mesh groups."""

    meshes: Dict[str, List[Mesh3D]] = field(default_factory=dict)
    bounds: Tuple[Point3D, Point3D] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    floor_count: int = 1
    metadata: dict = field(default_factory=dict)

    def add_mesh(self, mesh: Mesh3D) -> None:
        """Add a mesh to the scene, grouped by element_type."""
        if mesh.element_type not in self.meshes:
            self.meshes[mesh.element_type] = []
        self.meshes[mesh.element_type].append(mesh)
        self._update_bounds()

    def _update_bounds(self) -> None:
        """Recalculate scene bounding box."""
        all_vertices = []
        for mesh_list in self.meshes.values():
            for mesh in mesh_list:
                if mesh.vertices.size > 0:
                    all_vertices.append(mesh.vertices)

        if not all_vertices:
            self.bounds = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
            return

        combined = np.vstack(all_vertices)
        min_pt = tuple(combined.min(axis=0))
        max_pt = tuple(combined.max(axis=0))
        self.bounds = (min_pt, max_pt)

    def get_by_type(self, element_type: str) -> List[Mesh3D]:
        """Get all meshes of a specific element type."""
        return self.meshes.get(element_type, [])

    def get_by_source(self, source_id: str) -> List[Mesh3D]:
        """Get all meshes from a specific source element."""
        result = []
        for mesh_list in self.meshes.values():
            for mesh in mesh_list:
                if mesh.source_id == source_id:
                    result.append(mesh)
        return result

    def get_all_meshes(self) -> List[Mesh3D]:
        """Get flat list of all meshes."""
        result = []
        for mesh_list in self.meshes.values():
            result.extend(mesh_list)
        return result

    def to_trimesh_scene(self) -> trimesh.Scene:
        """Convert to trimesh Scene for export."""
        scene = trimesh.Scene()
        for element_type, mesh_list in self.meshes.items():
            if not mesh_list:
                continue
            # Combine all meshes of same type
            trimeshes = [m.to_trimesh() for m in mesh_list if m.vertices.size > 0]
            if trimeshes:
                combined = trimesh.util.concatenate(trimeshes)
                scene.add_geometry(combined, node_name=element_type)
        return scene

    def export_gltf(self, path: str, binary: bool = True) -> None:
        """Export scene to glTF/GLB format."""
        scene = self.to_trimesh_scene()
        file_type = "glb" if binary else "gltf"
        scene.export(path, file_type=file_type)

    def export_obj(self, path: str) -> None:
        """Export scene to OBJ format."""
        all_meshes = self.get_all_meshes()
        if not all_meshes:
            return
        trimeshes = [m.to_trimesh() for m in all_meshes if m.vertices.size > 0]
        if trimeshes:
            combined = trimesh.util.concatenate(trimeshes)
            combined.export(path, file_type="obj")
