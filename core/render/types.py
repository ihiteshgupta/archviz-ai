"""Data types for the render pipeline."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RenderConfig:
    """Configuration for render jobs."""

    size: str = "1024x1024"  # "1024x1024", "1792x1024", "1024x1792"
    quality: str = "hd"  # "standard", "hd"
    style_preset: str = "modern"  # Links to material StylePreset
    lighting: str = "natural"  # "natural", "warm", "cool", "dramatic"
    time_of_day: str = "day"  # "day", "evening", "night"
    additional_prompt: str = ""  # User additions (furniture, decor)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "size": self.size,
            "quality": self.quality,
            "style_preset": self.style_preset,
            "lighting": self.lighting,
            "time_of_day": self.time_of_day,
            "additional_prompt": self.additional_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RenderConfig":
        """Create RenderConfig from dictionary."""
        return cls(
            size=data.get("size", "1024x1024"),
            quality=data.get("quality", "hd"),
            style_preset=data.get("style_preset", "modern"),
            lighting=data.get("lighting", "natural"),
            time_of_day=data.get("time_of_day", "day"),
            additional_prompt=data.get("additional_prompt", ""),
        )


@dataclass
class RenderResult:
    """Result of a single render."""

    room_id: str
    room_name: str
    image_url: str  # DALL-E returned URL (temporary, ~1hr)
    revised_prompt: str  # DALL-E's revised prompt
    created_at: datetime = field(default_factory=datetime.now)
    config: RenderConfig = field(default_factory=RenderConfig)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "image_url": self.image_url,
            "revised_prompt": self.revised_prompt,
            "created_at": self.created_at.isoformat(),
            "config": self.config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RenderResult":
        """Create RenderResult from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            room_id=data.get("room_id", ""),
            room_name=data.get("room_name", ""),
            image_url=data.get("image_url", ""),
            revised_prompt=data.get("revised_prompt", ""),
            created_at=created_at,
            config=RenderConfig.from_dict(data.get("config", {})),
        )


@dataclass
class RenderError:
    """Error information for a failed render."""

    room_id: str
    room_name: str
    error_type: str  # "content_policy", "rate_limit", "timeout", "unknown"
    message: str
    retryable: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "error_type": self.error_type,
            "message": self.message,
            "retryable": self.retryable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RenderError":
        """Create RenderError from dictionary."""
        return cls(
            room_id=data.get("room_id", ""),
            room_name=data.get("room_name", ""),
            error_type=data.get("error_type", "unknown"),
            message=data.get("message", ""),
            retryable=data.get("retryable", False),
        )


@dataclass
class RenderJob:
    """Tracks a batch render job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "pending"  # "pending", "running", "completed", "failed", "cancelled"
    floor_plan_id: str = ""
    total_rooms: int = 0
    completed_rooms: int = 0
    results: List[RenderResult] = field(default_factory=list)
    errors: List[RenderError] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def progress(self) -> float:
        """Calculate progress as percentage."""
        if self.total_rooms == 0:
            return 0.0
        return (self.completed_rooms / self.total_rooms) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if job is complete (success or failure)."""
        return self.status in ("completed", "failed", "cancelled")

    @property
    def successful_renders(self) -> int:
        """Count of successful renders."""
        return len(self.results)

    @property
    def failed_renders(self) -> int:
        """Count of failed renders."""
        return len(self.errors)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "status": self.status,
            "floor_plan_id": self.floor_plan_id,
            "total_rooms": self.total_rooms,
            "completed_rooms": self.completed_rooms,
            "results": [r.to_dict() for r in self.results],
            "errors": [e.to_dict() for e in self.errors],
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": round(self.progress, 1),
            "successful_renders": self.successful_renders,
            "failed_renders": self.failed_renders,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RenderJob":
        """Create RenderJob from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        results = [RenderResult.from_dict(r) for r in data.get("results", [])]
        errors = [RenderError.from_dict(e) for e in data.get("errors", [])]

        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            status=data.get("status", "pending"),
            floor_plan_id=data.get("floor_plan_id", ""),
            total_rooms=data.get("total_rooms", 0),
            completed_rooms=data.get("completed_rooms", 0),
            results=results,
            errors=errors,
            created_at=created_at,
            completed_at=completed_at,
        )
