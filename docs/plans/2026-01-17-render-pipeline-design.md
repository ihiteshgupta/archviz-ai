# Render Pipeline Design

## Overview

AI-powered render pipeline using DALL-E 3 to generate photorealistic room visualizations from floor plans with applied materials.

## Requirements

- **Single room renders** - Quick preview renders on demand
- **Batch mode** - Render all rooms in a floor plan as async job
- **Single perspective** - One main view per room (v1)
- **Hybrid prompts** - Auto-generate from materials + user additions
- **Async with polling** - Non-blocking batch jobs with status polling

## Module Structure

```
core/render/
├── __init__.py           # Public API exports
├── types.py              # RenderJob, RenderResult, RenderConfig
├── prompt_builder.py     # Builds DALL-E prompts from materials/room
├── renderer.py           # RoomRenderer - single room rendering
├── batch.py              # BatchRenderer - multi-room orchestration
└── job_manager.py        # In-memory job tracking
```

## Data Types

```python
@dataclass
class RenderConfig:
    """Configuration for render jobs."""
    size: str = "1024x1024"          # "1024x1024", "1792x1024", "1024x1792"
    quality: str = "hd"               # "standard", "hd"
    style_preset: str = "modern"      # Links to material StylePreset
    lighting: str = "natural"         # "natural", "warm", "cool", "dramatic"
    time_of_day: str = "day"          # "day", "evening", "night"
    additional_prompt: str = ""       # User additions (furniture, decor)

@dataclass
class RenderResult:
    """Result of a single render."""
    room_id: str
    room_name: str
    image_url: str                    # DALL-E returned URL (temporary, ~1hr)
    revised_prompt: str               # DALL-E's revised prompt
    created_at: datetime
    config: RenderConfig

@dataclass
class RenderJob:
    """Tracks a batch render job."""
    id: str
    status: str                       # "pending", "running", "completed", "failed"
    floor_plan_id: str
    total_rooms: int
    completed_rooms: int = 0
    results: List[RenderResult] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None
```

## Prompt Builder

Constructs DALL-E prompts from room and material data.

**Template:**
```
Professional architectural interior visualization, photorealistic:

{room_type} ({area} sq m), {style} style

Materials:
- Floor: {floor_material.name}
- Walls: {wall_material.name}
- Ceiling: {ceiling_material.name}

Lighting: {lighting}, {time_of_day}

{additional_prompt}

Interior design magazine quality, realistic textures, 8K detail.
```

## Room Renderer

```python
class RoomRenderer:
    def __init__(self, openai_service, library, max_retries=2): ...

    async def render_room(self, room, assignments, config) -> RenderResult: ...
    async def render_with_custom_prompt(self, room, prompt, config) -> RenderResult: ...
```

**Error handling:**
- Content policy → return error, don't retry
- Rate limits → exponential backoff retry
- Timeout → retry once

## Batch Renderer

```python
class BatchRenderer:
    def __init__(self, openai_service, library, max_concurrent=3): ...

    async def start(self, floor_plan, assignments, config) -> str:  # Returns job_id
    def get_status(self, job_id) -> RenderJob: ...
    def cancel(self, job_id) -> bool: ...
```

**Execution flow:**
1. Create job with status "pending"
2. Return job_id immediately
3. Background: process rooms (max 3 concurrent)
4. Update progress after each room
5. Set "completed" when done

## Job Manager

```python
class JobManager:
    def create_job(self, floor_plan_id, total_rooms) -> RenderJob: ...
    def get_job(self, job_id) -> Optional[RenderJob]: ...
    def update_progress(self, job_id, result): ...
    def mark_completed(self, job_id): ...
    def mark_failed(self, job_id, error): ...
    def list_jobs(self) -> List[RenderJob]: ...
```

## Usage

```python
from core.render import RoomRenderer, BatchRenderer, RenderConfig

# Single room render
renderer = RoomRenderer(openai_service, material_library)
result = await renderer.render_room(room, assignments, RenderConfig(style_preset="modern"))

# Batch render
batch = BatchRenderer(openai_service, material_library)
job_id = await batch.start(floor_plan, assignments, config)

# Poll for status
job = batch.get_status(job_id)
print(f"Progress: {job.completed_rooms}/{job.total_rooms}")
```

## Future Enhancements

- **Azure Blob Storage** - Persist rendered images beyond DALL-E's 1-hour URL expiry
- **Multiple camera angles** - 2-3 views per room
- **Webhook notifications** - Notify when batch completes instead of polling
