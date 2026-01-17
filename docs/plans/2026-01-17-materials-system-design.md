# Materials System Design

## Overview

A material library with AI-powered suggestions for assigning PBR materials to architectural surfaces based on room type and style preferences.

## Requirements

- **Material library** - Bundled materials + external fetching from ambientCG
- **Full PBR materials** - Diffuse, normal, roughness, metallic, AO maps with metadata
- **AI suggestions** - GPT-4o suggests materials based on room type and style preset
- **Manual override** - Users can swap any AI-suggested material
- **Style presets** - Modern, Rustic, Industrial, Scandinavian, Traditional, Minimalist

## Module Structure

```
core/materials/
├── __init__.py           # Public API exports
├── types.py              # Material, MaterialLibrary, MaterialAssignment dataclasses
├── library.py            # MaterialLibrary - load/search bundled + external materials
├── fetcher.py            # External texture fetcher (ambientCG integration)
├── suggester.py          # AI-powered material suggestion using Azure OpenAI
└── presets.py            # Style presets definitions
```

## Data Types

```python
@dataclass
class Material:
    """Full PBR material with metadata."""
    id: str                          # Unique identifier (e.g., "wood_oak_natural")
    name: str                        # Display name ("Natural Oak Wood")
    category: str                    # "wood", "stone", "metal", "fabric", "ceramic", etc.

    # Base properties
    base_color: Tuple[float, float, float]  # RGB fallback if no texture
    roughness: float = 0.5           # 0 = glossy, 1 = rough
    metallic: float = 0.0            # 0 = dielectric, 1 = metal

    # PBR texture paths (relative to materials directory or URLs)
    diffuse_map: Optional[str] = None
    normal_map: Optional[str] = None
    roughness_map: Optional[str] = None
    metallic_map: Optional[str] = None
    ao_map: Optional[str] = None     # Ambient occlusion

    # Metadata for AI suggestions
    tags: List[str] = field(default_factory=list)  # ["warm", "natural", "grain"]
    suitable_for: List[str] = field(default_factory=list)  # ["floor", "furniture"]
    room_affinity: List[str] = field(default_factory=list)  # ["bedroom", "living"]
    styles: List[str] = field(default_factory=list)  # ["modern", "rustic", "scandinavian"]

    # Source info
    source: str = "bundled"          # "bundled", "ambientcg", "user"
    source_url: Optional[str] = None


@dataclass
class MaterialAssignment:
    """Maps a surface to a material."""
    surface_id: str      # e.g., "room1_floor", "wall_exterior"
    material_id: str     # Reference to Material.id
    room_id: Optional[str] = None
    surface_type: str = "generic"  # "floor", "wall", "ceiling"
```

## Material Library

**Storage structure:**
```
data/materials/
├── library.json          # Material metadata index
├── bundled/              # Shipped with app (~20-30 materials)
│   ├── wood_oak_natural/
│   │   ├── diffuse.jpg
│   │   ├── normal.jpg
│   │   └── roughness.jpg
│   └── ...
└── cache/                # Downloaded external materials
    └── ambientcg/
```

**Library operations:**

```python
class MaterialLibrary:
    def __init__(self, data_dir: str = "data/materials"):
        self.materials: Dict[str, Material] = {}
        self._load_bundled()

    def get(self, material_id: str) -> Optional[Material]: ...

    def search(
        self,
        category: Optional[str] = None,      # "wood", "stone"
        tags: Optional[List[str]] = None,    # ["warm", "natural"]
        suitable_for: Optional[str] = None,  # "floor"
        style: Optional[str] = None,         # "modern"
        room_type: Optional[str] = None,     # "kitchen"
    ) -> List[Material]: ...

    def add_external(self, material: Material) -> None: ...

    def list_categories(self) -> List[str]: ...
```

**Bundled material categories (v1):**
- Wood (5): oak, walnut, pine, bamboo, parquet
- Stone (4): marble, granite, slate, travertine
- Ceramic (3): white tile, subway tile, terracotta
- Concrete (2): polished, raw
- Metal (2): brushed steel, copper
- Fabric (2): carpet neutral, carpet wool
- Paint (4): white, gray, beige, accent colors

## External Material Fetcher

```python
class MaterialFetcher:
    """Fetches PBR materials from ambientCG (CC0 license)."""

    BASE_URL = "https://ambientcg.com/api/v2"

    def __init__(self, cache_dir: str, resolution: str = "1K"):
        self.cache_dir = cache_dir
        self.resolution = resolution  # "1K", "2K", "4K"

    async def search(
        self,
        query: str,              # "wood floor"
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[dict]: ...

    async def download(self, asset_id: str) -> Material:
        """Download and cache a material, return Material object."""
        ...

    def is_cached(self, asset_id: str) -> bool: ...
```

**Download flow:**
1. Query ambientCG API for matching assets
2. Download ZIP with PBR maps (diffuse, normal, roughness, etc.)
3. Extract to `cache/ambientcg/{asset_id}/`
4. Create `Material` object with local paths and metadata

## AI Material Suggester

```python
class MaterialSuggester:
    def __init__(self, library: MaterialLibrary, openai_service: AzureOpenAIService):
        self.library = library
        self.openai = openai_service

    async def suggest(
        self,
        floor_plan: FloorPlan,
        style: StylePreset,
    ) -> Dict[str, MaterialAssignment]:
        """Suggest materials for all surfaces in floor plan."""
        ...

    async def suggest_for_room(
        self,
        room: Room,
        style: StylePreset,
    ) -> Dict[str, Material]:
        """Suggest floor, wall, ceiling materials for one room."""
        ...
```

**Prompt structure:**
```
Room: Kitchen (25 sq m)
Style: Modern - clean lines, neutral palette, minimal texture
Surfaces to assign: floor, walls, ceiling

Available floor materials: ceramic_white_tile, wood_oak_natural, concrete_polished
Available wall materials: paint_white, paint_gray, ceramic_subway_tile
Available ceiling materials: paint_white, paint_off_white

Select the best material ID for each surface. Return JSON:
{"floor": "...", "walls": "...", "ceiling": "..."}
```

**Fallback:** Hardcoded defaults per room type if API fails.

## Style Presets

```python
@dataclass
class StylePreset:
    id: str
    name: str
    description: str
    color_palette: List[str]      # ["neutral", "warm", "earth tones"]
    texture_preference: str        # "minimal", "natural", "heavy"
    material_affinity: List[str]  # Preferred categories
    avoid_materials: List[str]    # Categories to avoid
    prompt_description: str        # For LLM context
```

**Built-in presets (v1):**
- Modern: clean lines, neutral colors, smooth surfaces
- Rustic: natural wood, stone, warm earth tones
- Industrial: concrete, metal, exposed materials
- Scandinavian: light wood, white, minimal
- Traditional: rich wood, classic patterns
- Minimalist: monochrome, ultra-clean, no texture

## Integration with Model Generation

**Material application flow:**

1. Generate `Scene3D` from `FloorPlan` (existing)
2. Get `MaterialAssignment` dict from `MaterialSuggester`
3. On export, resolve each mesh's material_id to actual Material
4. Embed PBR textures in glTF

**Resolution logic:**

```python
def resolve_material(mesh: Mesh3D, assignments: Dict, library: MaterialLibrary) -> Material:
    # Try room-specific: "room1_floor"
    key = f"{mesh.source_id}_{mesh.element_type}"
    if key in assignments:
        return library.get(assignments[key].material_id)

    # Fall back to type default
    if mesh.material_id in assignments:
        return library.get(assignments[mesh.material_id].material_id)

    # Ultimate fallback
    return library.get("default")
```

## Usage

```python
from core.materials import MaterialLibrary, MaterialSuggester, StylePreset

library = MaterialLibrary()
suggester = MaterialSuggester(library)

# Get AI suggestions for a floor plan
assignments = await suggester.suggest(floor_plan, style=StylePreset.MODERN)

# Export with materials
exporter.export_gltf_with_materials(scene, assignments, library, "output/model.glb")
```
