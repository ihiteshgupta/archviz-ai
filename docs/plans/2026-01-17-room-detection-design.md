# Room Detection from Walls - Design Document

**Date**: 2026-01-17
**Status**: Approved
**Author**: Claude + Hitesh

## Overview

Auto-detect rooms from wall geometry using a hybrid approach: geometric algorithms find enclosed regions, AI classifies room types.

### Goals

- Detect rooms from wall geometry without relying on CAD layer conventions
- Handle messy CAD files with gaps and overlaps via tolerance-based snapping
- Classify room types using GPT-4 with geometry, fixtures, and text context
- Support residential and commercial room types

## Architecture

```
DXF File
    ↓
DWGParser.parse()
    ↓
Extract walls, doors, windows (existing)
    ↓
WallGraph: snap endpoints → build graph → find cycles
    ↓
RoomClassifier: gather context → GPT-4 → room types
    ↓
FloorPlan with auto-detected rooms
```

### Stage 1: Geometry Processing

A `WallGraph` class builds a planar graph from wall segments:
- Each wall endpoint becomes a node
- Edges represent wall segments
- R-tree spatial indexing for efficient proximity queries
- Endpoints within snap tolerance (default 5cm) are merged

Cycle detection uses planar graph traversal ("always turn right") to find minimal enclosed regions. Each cycle becomes a candidate room polygon.

### Stage 2: AI Classification

For each candidate polygon, gather context:
- Area, aspect ratio, perimeter
- Door and window count
- Fixture blocks inside boundary (toilet, sink, stove, etc.)
- Text labels near centroid

Send to GPT-4 for classification. Returns room type and confidence score.

## Component Design

### WallGraph

```python
@dataclass
class GraphNode:
    id: str
    position: Point2D
    edge_ids: List[str]

@dataclass
class GraphEdge:
    id: str
    node_ids: Tuple[str, str]
    wall_id: str

class WallGraph:
    nodes: Dict[str, GraphNode]
    edges: Dict[str, GraphEdge]
    spatial_index: RTree
    snap_tolerance: float = 0.05  # 5cm default

    def add_walls(self, walls: List[Wall]) -> None
    def find_cycles(self) -> List[List[Point2D]]
```

**Cycle Detection Algorithm**:
1. Start from any edge, pick a direction
2. At each node, sort outgoing edges by angle relative to incoming edge
3. Pick the next edge in clockwise order (rightmost turn)
4. Continue until returning to start node
5. Mark traversed edge-directions as used, repeat from unused edges
6. Filter: discard outer boundary (largest cycle), keep interior rooms

**Edge Cases**:
- Dangling walls (dead ends): Excluded from cycles automatically
- Self-intersecting walls: Split at intersection points before building graph
- Duplicate walls: Deduplicated during graph construction

### RoomClassifier

```python
@dataclass
class RoomContext:
    polygon: List[Point2D]
    area: float
    aspect_ratio: float
    door_count: int
    window_count: int
    fixtures: List[str]
    nearby_text: List[str]
    adjacent_rooms: List[str]

class RoomClassifier:
    def __init__(self, openai_service: AzureOpenAIService)
    def classify_batch(self, contexts: List[RoomContext]) -> List[RoomClassification]
```

**Fixture Detection Patterns**:
- Bathroom: toilet, wc, sink, basin, shower, tub, bath
- Kitchen: stove, oven, fridge, refrigerator, sink, dishwasher
- Laundry: washer, dryer, washing
- Furniture: bed, sofa, desk, table, chair

**Room Types**:
living_room, bedroom, bathroom, kitchen, hallway, closet, garage,
dining_room, office, laundry, pantry, balcony, conference_room,
reception, lobby, storage, utility, unknown

**GPT-4 Prompt**:
```
You are classifying a room in an architectural floor plan.

Room data:
- Area: {area} m²
- Dimensions: {width}m x {height}m
- Doors: {door_count}, Windows: {window_count}
- Fixtures detected: {fixtures}
- Text labels found: {nearby_text}

Classify this room. Return JSON:
{"room_type": "...", "confidence": 0.0-1.0, "reasoning": "..."}
```

Batch up to 10 rooms per API call to reduce latency.

### Parser Integration

```python
class DWGParser:
    def __init__(
        self,
        snap_tolerance: float = 0.05,
        auto_detect_rooms: bool = True,
        openai_service: Optional[AzureOpenAIService] = None,
        ...
    )

    def parse(self, file_path, auto_detect_rooms: bool = True) -> FloorPlan:
        # ... existing extraction ...
        if auto_detect_rooms:
            self._detect_rooms_from_walls()
        return self._floor_plan
```

**Fallback**: If no OpenAI service configured, rooms detected with `room_type="unknown"`.

## File Structure

```
core/dwg_parser/
├── __init__.py          # Export public API
├── parser.py            # DWGParser (modified)
├── elements.py          # Wall, Door, Window, Room (existing)
├── converter.py         # DWG→DXF conversion (existing)
├── wall_graph.py        # NEW: WallGraph, GraphNode, GraphEdge
├── room_classifier.py   # NEW: RoomClassifier, RoomContext
└── spatial_utils.py     # NEW: R-tree wrapper, geometry helpers
```

## Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "rtree>=1.2.0",      # Spatial indexing
    "shapely>=2.0.0",    # Polygon operations
]
```

## Error Handling

### Geometry Errors

| Scenario | Handling |
|----------|----------|
| No walls extracted | Return empty rooms, log warning |
| No closed cycles found | Return empty rooms, log info |
| Degenerate polygons | Skip silently |
| Self-intersecting polygons | Use Shapely `make_valid()` |
| Very small rooms (< 0.5m²) | Filter as artifacts |

### AI Classification Errors

| Scenario | Handling |
|----------|----------|
| OpenAI not configured | Skip classification, use "unknown" |
| API timeout/rate limit | Retry 3x with backoff, then "unknown" |
| Invalid JSON response | Parse what's possible, fallback "unknown" |
| Low confidence (< 0.5) | Keep but flag `confidence_low = True` |

### Validation

Check for overlapping rooms and area consistency. Attach warnings to `FloorPlan.warnings`.

## Testing

### Unit Tests

**test_wall_graph.py**:
- Graph construction (nodes, edges, snapping, deduplication)
- Cycle detection (rectangle, adjacent rooms, L-shape, no cycles)

**test_room_classifier.py**:
- Fixture detection, text extraction, aspect ratio
- Classification with mocked OpenAI
- Batch processing, error fallbacks

### Integration Tests

**test_room_detection.py** (requires `@pytest.mark.integration`):
- Full pipeline with sample DXF files
- Messy CAD tolerance testing

### Test Fixtures

Generate minimal DXF files programmatically with ezdxf in `tests/conftest.py`.

## Usage Example

```python
from core.dwg_parser import DWGParser
from core.azure import AzureOpenAIService

openai = AzureOpenAIService()
parser = DWGParser(
    snap_tolerance=0.05,
    auto_detect_rooms=True,
    openai_service=openai,
)

floor_plan = parser.parse("apartment.dxf")

for room in floor_plan.rooms:
    print(f"{room.room_type}: {room.area:.1f}m²")
```
