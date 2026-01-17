"""Tests for the render pipeline."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.dwg_parser.elements import Room
from core.dwg_parser.parser import FloorPlan, FloorPlanMetadata
from core.materials.library import MaterialLibrary
from core.materials.types import Material, MaterialAssignment
from core.render import (
    BatchRenderer,
    ContentPolicyError,
    JobManager,
    PromptBuilder,
    RateLimitError,
    RenderConfig,
    RenderError,
    RenderException,
    RenderJob,
    RenderResult,
    RoomRenderer,
    TimeoutError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_room():
    """Create a sample room for testing."""
    return Room(
        id="room1",
        name="Living Room",
        room_type="living",
        polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
        floor_level=0,
        ceiling_height=3.0,
    )


@pytest.fixture
def sample_rooms():
    """Create multiple sample rooms for batch testing."""
    return [
        Room(
            id="room1",
            name="Living Room",
            room_type="living",
            polygon=[(0, 0), (5, 0), (5, 4), (0, 4)],
        ),
        Room(
            id="room2",
            name="Bedroom",
            room_type="bedroom",
            polygon=[(6, 0), (10, 0), (10, 4), (6, 4)],
        ),
        Room(
            id="room3",
            name="Kitchen",
            room_type="kitchen",
            polygon=[(0, 5), (4, 5), (4, 8), (0, 8)],
        ),
    ]


@pytest.fixture
def sample_floor_plan(sample_rooms):
    """Create a sample floor plan for testing."""
    return FloorPlan(
        metadata=FloorPlanMetadata(filename="test_plan.dxf"),
        rooms=sample_rooms,
    )


@pytest.fixture
def sample_materials():
    """Create sample materials."""
    return [
        Material(
            id="wood_oak",
            name="Oak Hardwood",
            category="wood",
            suitable_for=["floor"],
        ),
        Material(
            id="paint_white",
            name="Matte White Paint",
            category="paint",
            suitable_for=["wall", "ceiling"],
        ),
    ]


@pytest.fixture
def sample_assignments():
    """Create sample material assignments."""
    return [
        MaterialAssignment(
            surface_id="room1_floor",
            material_id="wood_oak",
            room_id="room1",
            surface_type="floor",
        ),
        MaterialAssignment(
            surface_id="room1_wall",
            material_id="paint_white",
            room_id="room1",
            surface_type="wall",
        ),
    ]


@pytest.fixture
def mock_library(sample_materials):
    """Create a mock material library."""
    library = MagicMock(spec=MaterialLibrary)
    library.get.side_effect = lambda id: next(
        (m for m in sample_materials if m.id == id), None
    )
    return library


@pytest.fixture
def mock_openai_service():
    """Create a mock Azure OpenAI service."""
    service = MagicMock()
    service.generate_concept_render = AsyncMock(
        return_value={
            "url": "https://example.com/render.png",
            "revised_prompt": "A beautiful living room...",
        }
    )
    return service


@pytest.fixture
def render_config():
    """Create a default render config."""
    return RenderConfig(
        size="1024x1024",
        quality="hd",
        style_preset="modern",
        lighting="natural",
        time_of_day="day",
    )


# ============================================================================
# RenderConfig Tests
# ============================================================================


class TestRenderConfig:
    """Tests for RenderConfig dataclass."""

    def test_default_values(self):
        """Test default config values."""
        config = RenderConfig()
        assert config.size == "1024x1024"
        assert config.quality == "hd"
        assert config.style_preset == "modern"
        assert config.lighting == "natural"
        assert config.time_of_day == "day"
        assert config.additional_prompt == ""

    def test_custom_values(self):
        """Test custom config values."""
        config = RenderConfig(
            size="1792x1024",
            quality="standard",
            style_preset="rustic",
            lighting="warm",
            time_of_day="evening",
            additional_prompt="Add a cozy fireplace",
        )
        assert config.size == "1792x1024"
        assert config.style_preset == "rustic"
        assert config.additional_prompt == "Add a cozy fireplace"

    def test_to_dict(self):
        """Test serialization to dict."""
        config = RenderConfig(style_preset="industrial")
        data = config.to_dict()
        assert data["style_preset"] == "industrial"
        assert "size" in data
        assert "quality" in data

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {"size": "1024x1792", "lighting": "dramatic"}
        config = RenderConfig.from_dict(data)
        assert config.size == "1024x1792"
        assert config.lighting == "dramatic"
        assert config.quality == "hd"  # Default value


# ============================================================================
# RenderResult Tests
# ============================================================================


class TestRenderResult:
    """Tests for RenderResult dataclass."""

    def test_create_result(self):
        """Test creating a render result."""
        result = RenderResult(
            room_id="room1",
            room_name="Living Room",
            image_url="https://example.com/image.png",
            revised_prompt="A modern living room...",
        )
        assert result.room_id == "room1"
        assert result.room_name == "Living Room"
        assert result.image_url == "https://example.com/image.png"

    def test_to_dict(self):
        """Test serialization."""
        result = RenderResult(
            room_id="room1",
            room_name="Test Room",
            image_url="https://test.com/img.png",
            revised_prompt="Test prompt",
        )
        data = result.to_dict()
        assert data["room_id"] == "room1"
        assert data["image_url"] == "https://test.com/img.png"
        assert "created_at" in data
        assert "config" in data

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "room_id": "r1",
            "room_name": "Kitchen",
            "image_url": "https://x.com/k.png",
            "revised_prompt": "A kitchen",
            "created_at": "2024-01-15T10:30:00",
        }
        result = RenderResult.from_dict(data)
        assert result.room_id == "r1"
        assert result.room_name == "Kitchen"


# ============================================================================
# RenderError Tests
# ============================================================================


class TestRenderError:
    """Tests for RenderError dataclass."""

    def test_create_error(self):
        """Test creating a render error."""
        error = RenderError(
            room_id="room1",
            room_name="Living Room",
            error_type="content_policy",
            message="Content policy violation",
            retryable=False,
        )
        assert error.room_id == "room1"
        assert error.error_type == "content_policy"
        assert not error.retryable

    def test_retryable_error(self):
        """Test retryable error."""
        error = RenderError(
            room_id="room1",
            room_name="Room",
            error_type="rate_limit",
            message="Rate limit exceeded",
            retryable=True,
        )
        assert error.retryable

    def test_to_dict(self):
        """Test serialization."""
        error = RenderError(
            room_id="r1",
            room_name="Test",
            error_type="timeout",
            message="Request timed out",
            retryable=True,
        )
        data = error.to_dict()
        assert data["error_type"] == "timeout"
        assert data["retryable"] is True


# ============================================================================
# RenderJob Tests
# ============================================================================


class TestRenderJob:
    """Tests for RenderJob dataclass."""

    def test_default_values(self):
        """Test default job values."""
        job = RenderJob()
        assert job.status == "pending"
        assert job.total_rooms == 0
        assert job.completed_rooms == 0
        assert len(job.results) == 0
        assert len(job.errors) == 0

    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        job = RenderJob(total_rooms=10, completed_rooms=5)
        assert job.progress == 50.0

    def test_progress_zero_rooms(self):
        """Test progress with zero rooms."""
        job = RenderJob(total_rooms=0)
        assert job.progress == 0.0

    def test_is_complete(self):
        """Test completion status check."""
        pending_job = RenderJob(status="pending")
        running_job = RenderJob(status="running")
        completed_job = RenderJob(status="completed")
        failed_job = RenderJob(status="failed")
        cancelled_job = RenderJob(status="cancelled")

        assert not pending_job.is_complete
        assert not running_job.is_complete
        assert completed_job.is_complete
        assert failed_job.is_complete
        assert cancelled_job.is_complete

    def test_counts(self):
        """Test successful and failed render counts."""
        job = RenderJob()
        job.results.append(
            RenderResult(room_id="r1", room_name="R1", image_url="x", revised_prompt="y")
        )
        job.results.append(
            RenderResult(room_id="r2", room_name="R2", image_url="x", revised_prompt="y")
        )
        job.errors.append(
            RenderError(room_id="r3", room_name="R3", error_type="timeout", message="err")
        )

        assert job.successful_renders == 2
        assert job.failed_renders == 1

    def test_to_dict(self):
        """Test serialization."""
        job = RenderJob(
            floor_plan_id="plan1",
            total_rooms=5,
            completed_rooms=2,
        )
        data = job.to_dict()
        assert data["floor_plan_id"] == "plan1"
        assert data["total_rooms"] == 5
        assert "progress" in data


# ============================================================================
# PromptBuilder Tests
# ============================================================================


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    def test_build_prompt_basic(self, mock_library, sample_room, sample_assignments):
        """Test basic prompt building."""
        builder = PromptBuilder(mock_library)
        config = RenderConfig(style_preset="modern", lighting="natural", time_of_day="day")

        prompt = builder.build_prompt(sample_room, sample_assignments, config)

        assert "Professional architectural interior visualization" in prompt
        assert "Living Room" in prompt or "living" in prompt.lower()
        assert "modern" in prompt.lower()
        assert "natural" in prompt.lower()
        assert "8K detail" in prompt

    def test_build_prompt_with_materials(self, mock_library, sample_room, sample_assignments):
        """Test prompt includes material names."""
        builder = PromptBuilder(mock_library)
        config = RenderConfig()

        prompt = builder.build_prompt(sample_room, sample_assignments, config)

        # Materials section should be present
        assert "Materials:" in prompt

    def test_build_prompt_different_lighting(self, mock_library, sample_room):
        """Test different lighting descriptions."""
        builder = PromptBuilder(mock_library)

        for lighting in ["natural", "warm", "cool", "dramatic"]:
            config = RenderConfig(lighting=lighting)
            prompt = builder.build_prompt(sample_room, [], config)
            assert lighting in prompt.lower() or PromptBuilder.LIGHTING_DESCRIPTIONS.get(lighting, "") in prompt

    def test_build_prompt_time_of_day(self, mock_library, sample_room):
        """Test different time of day descriptions."""
        builder = PromptBuilder(mock_library)

        for time in ["day", "evening", "night"]:
            config = RenderConfig(time_of_day=time)
            prompt = builder.build_prompt(sample_room, [], config)
            assert time in prompt.lower() or "sun" in prompt.lower() or "light" in prompt.lower()

    def test_build_prompt_with_additional(self, mock_library, sample_room):
        """Test prompt with additional user text."""
        builder = PromptBuilder(mock_library)
        config = RenderConfig(additional_prompt="Include a large sectional sofa")

        prompt = builder.build_prompt(sample_room, [], config)
        assert "sectional sofa" in prompt

    def test_build_custom_prompt(self, mock_library, sample_room):
        """Test custom prompt building."""
        builder = PromptBuilder(mock_library)
        custom = "A minimalist space with concrete floors and white walls"
        config = RenderConfig()

        prompt = builder.build_custom_prompt(sample_room, custom, config)

        assert "Professional architectural" in prompt
        assert "minimalist" in prompt
        assert "concrete" in prompt

    def test_build_minimal_prompt(self, mock_library):
        """Test minimal prompt without Room object."""
        builder = PromptBuilder(mock_library)

        prompt = builder.build_minimal_prompt("bedroom", "scandinavian")

        assert "bedroom" in prompt.lower()
        assert "scandinavian" in prompt.lower()
        assert "8K detail" in prompt


# ============================================================================
# JobManager Tests
# ============================================================================


class TestJobManager:
    """Tests for JobManager."""

    def test_create_job(self):
        """Test job creation."""
        manager = JobManager()
        job = manager.create_job("plan1", 5)

        assert job.floor_plan_id == "plan1"
        assert job.total_rooms == 5
        assert job.status == "pending"

    def test_get_job(self):
        """Test getting a job by ID."""
        manager = JobManager()
        job = manager.create_job("plan1", 3)

        retrieved = manager.get_job(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id

    def test_get_nonexistent_job(self):
        """Test getting a non-existent job."""
        manager = JobManager()
        assert manager.get_job("nonexistent") is None

    def test_start_job(self):
        """Test starting a job."""
        manager = JobManager()
        job = manager.create_job("plan1", 5)

        assert manager.start_job(job.id)
        retrieved = manager.get_job(job.id)
        assert retrieved.status == "running"

    def test_start_nonexistent_job(self):
        """Test starting a non-existent job."""
        manager = JobManager()
        assert not manager.start_job("nonexistent")

    def test_update_progress_with_result(self):
        """Test updating progress with a successful result."""
        manager = JobManager()
        job = manager.create_job("plan1", 2)
        manager.start_job(job.id)

        result = RenderResult(
            room_id="room1",
            room_name="Living Room",
            image_url="https://test.com/img.png",
            revised_prompt="Test",
        )
        assert manager.update_progress(job.id, result=result)

        updated = manager.get_job(job.id)
        assert updated.completed_rooms == 1
        assert len(updated.results) == 1

    def test_update_progress_with_error(self):
        """Test updating progress with an error."""
        manager = JobManager()
        job = manager.create_job("plan1", 2)
        manager.start_job(job.id)

        error = RenderError(
            room_id="room1",
            room_name="Living Room",
            error_type="timeout",
            message="Request timed out",
        )
        assert manager.update_progress(job.id, error=error)

        updated = manager.get_job(job.id)
        assert updated.completed_rooms == 1
        assert len(updated.errors) == 1

    def test_mark_completed(self):
        """Test marking a job as completed."""
        manager = JobManager()
        job = manager.create_job("plan1", 1)
        manager.start_job(job.id)

        assert manager.mark_completed(job.id)
        updated = manager.get_job(job.id)
        assert updated.status == "completed"
        assert updated.completed_at is not None

    def test_mark_failed(self):
        """Test marking a job as failed."""
        manager = JobManager()
        job = manager.create_job("plan1", 1)
        manager.start_job(job.id)

        assert manager.mark_failed(job.id, "Test failure")
        updated = manager.get_job(job.id)
        assert updated.status == "failed"

    def test_cancel_job(self):
        """Test cancelling a job."""
        manager = JobManager()
        job = manager.create_job("plan1", 5)
        manager.start_job(job.id)

        assert manager.cancel_job(job.id)
        updated = manager.get_job(job.id)
        assert updated.status == "cancelled"

    def test_cancel_completed_job(self):
        """Test that completed jobs cannot be cancelled."""
        manager = JobManager()
        job = manager.create_job("plan1", 1)
        manager.start_job(job.id)
        manager.mark_completed(job.id)

        assert not manager.cancel_job(job.id)

    def test_list_jobs(self):
        """Test listing all jobs."""
        manager = JobManager()
        manager.create_job("plan1", 2)
        manager.create_job("plan2", 3)
        manager.create_job("plan1", 1)

        all_jobs = manager.list_jobs()
        assert len(all_jobs) == 3

    def test_list_jobs_filtered_by_floor_plan(self):
        """Test listing jobs filtered by floor plan ID."""
        manager = JobManager()
        manager.create_job("plan1", 2)
        manager.create_job("plan2", 3)
        manager.create_job("plan1", 1)

        filtered = manager.list_jobs(floor_plan_id="plan1")
        assert len(filtered) == 2

    def test_list_jobs_filtered_by_status(self):
        """Test listing jobs filtered by status."""
        manager = JobManager()
        job1 = manager.create_job("plan1", 2)
        job2 = manager.create_job("plan2", 3)
        manager.start_job(job1.id)

        running = manager.list_jobs(status="running")
        assert len(running) == 1
        assert running[0].id == job1.id

    def test_delete_job(self):
        """Test deleting a job."""
        manager = JobManager()
        job = manager.create_job("plan1", 1)
        job_id = job.id

        assert manager.delete_job(job_id)
        assert manager.get_job(job_id) is None

    def test_clear_all(self):
        """Test clearing all jobs."""
        manager = JobManager()
        manager.create_job("plan1", 1)
        manager.create_job("plan2", 2)

        count = manager.clear_all()
        assert count == 2
        assert len(manager.list_jobs()) == 0


# ============================================================================
# RoomRenderer Tests
# ============================================================================


class TestRoomRenderer:
    """Tests for RoomRenderer."""

    @pytest.mark.asyncio
    async def test_render_room_success(
        self, mock_openai_service, mock_library, sample_room, sample_assignments, render_config
    ):
        """Test successful room render."""
        renderer = RoomRenderer(mock_openai_service, mock_library)

        result = await renderer.render_room(sample_room, sample_assignments, render_config)

        assert result.room_id == "room1"
        assert result.room_name == "Living Room"
        assert result.image_url == "https://example.com/render.png"
        mock_openai_service.generate_concept_render.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_with_custom_prompt(
        self, mock_openai_service, mock_library, sample_room, render_config
    ):
        """Test rendering with custom prompt."""
        renderer = RoomRenderer(mock_openai_service, mock_library)

        result = await renderer.render_with_custom_prompt(
            sample_room, "A minimalist zen space", render_config
        )

        assert result.room_id == "room1"
        call_args = mock_openai_service.generate_concept_render.call_args
        assert "minimalist" in call_args[1]["prompt"].lower() or "minimalist" in call_args.kwargs.get("prompt", "").lower()

    @pytest.mark.asyncio
    async def test_render_content_policy_error(
        self, mock_openai_service, mock_library, sample_room, render_config
    ):
        """Test handling of content policy errors."""
        mock_openai_service.generate_concept_render.side_effect = Exception(
            "content_policy_violation detected"
        )
        renderer = RoomRenderer(mock_openai_service, mock_library, max_retries=0)

        with pytest.raises(ContentPolicyError):
            await renderer.render_room(sample_room, [], render_config)

    @pytest.mark.asyncio
    async def test_render_rate_limit_retry(
        self, mock_openai_service, mock_library, sample_room, render_config
    ):
        """Test retry on rate limit errors."""
        call_count = 0

        async def mock_render(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("rate limit exceeded 429")
            return {"url": "https://success.com/img.png", "revised_prompt": "test"}

        mock_openai_service.generate_concept_render = mock_render
        renderer = RoomRenderer(mock_openai_service, mock_library, max_retries=2)

        result = await renderer.render_room(sample_room, [], render_config)

        assert result.image_url == "https://success.com/img.png"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_render_room_safe(
        self, mock_openai_service, mock_library, sample_room, render_config
    ):
        """Test safe render method that doesn't raise."""
        renderer = RoomRenderer(mock_openai_service, mock_library)

        result, error = await renderer.render_room_safe(sample_room, [], render_config)

        assert result is not None
        assert error is None

    @pytest.mark.asyncio
    async def test_render_room_safe_with_error(
        self, mock_openai_service, mock_library, sample_room, render_config
    ):
        """Test safe render method with error."""
        mock_openai_service.generate_concept_render.side_effect = Exception("Test error")
        renderer = RoomRenderer(mock_openai_service, mock_library, max_retries=0)

        result, error = await renderer.render_room_safe(sample_room, [], render_config)

        assert result is None
        assert error is not None
        assert error.room_id == "room1"

    def test_create_error(self, mock_openai_service, mock_library, sample_room):
        """Test error creation from exception."""
        renderer = RoomRenderer(mock_openai_service, mock_library)

        # Test with RenderException
        exc = RateLimitError("Rate limit exceeded")
        error = renderer.create_error(sample_room, exc)
        assert error.error_type == "rate_limit"
        assert error.retryable

        # Test with generic exception
        exc = Exception("Unknown error")
        error = renderer.create_error(sample_room, exc)
        assert error.error_type == "unknown"
        assert not error.retryable


# ============================================================================
# BatchRenderer Tests
# ============================================================================


class TestBatchRenderer:
    """Tests for BatchRenderer."""

    @pytest.mark.asyncio
    async def test_start_batch(
        self, mock_openai_service, mock_library, sample_floor_plan, render_config
    ):
        """Test starting a batch render job."""
        batch = BatchRenderer(mock_openai_service, mock_library, max_concurrent=2)

        job_id = await batch.start(sample_floor_plan, [], render_config)

        assert job_id is not None
        job = batch.get_status(job_id)
        assert job is not None
        assert job.total_rooms == 3

    @pytest.mark.asyncio
    async def test_batch_render_completes(
        self, mock_openai_service, mock_library, sample_floor_plan, render_config
    ):
        """Test that batch render completes all rooms."""
        batch = BatchRenderer(mock_openai_service, mock_library, max_concurrent=2)

        job_id = await batch.start(sample_floor_plan, [], render_config)

        # Wait for completion
        for _ in range(50):  # Max 5 seconds
            await asyncio.sleep(0.1)
            job = batch.get_status(job_id)
            if job.is_complete:
                break

        job = batch.get_status(job_id)
        assert job.status == "completed"
        assert job.completed_rooms == 3
        assert len(job.results) == 3

    @pytest.mark.asyncio
    async def test_batch_render_with_specific_rooms(
        self, mock_openai_service, mock_library, sample_floor_plan, render_config
    ):
        """Test batch render with specific room IDs."""
        batch = BatchRenderer(mock_openai_service, mock_library)

        job_id = await batch.start(
            sample_floor_plan, [], render_config, room_ids=["room1", "room3"]
        )

        # Wait for completion
        for _ in range(50):
            await asyncio.sleep(0.1)
            job = batch.get_status(job_id)
            if job.is_complete:
                break

        job = batch.get_status(job_id)
        assert job.total_rooms == 2
        assert job.completed_rooms == 2

    @pytest.mark.asyncio
    async def test_batch_render_empty_floor_plan(
        self, mock_openai_service, mock_library, render_config
    ):
        """Test batch render with empty floor plan."""
        floor_plan = FloorPlan(
            metadata=FloorPlanMetadata(filename="empty.dxf"),
            rooms=[],
        )
        batch = BatchRenderer(mock_openai_service, mock_library)

        job_id = await batch.start(floor_plan, [], render_config)

        job = batch.get_status(job_id)
        assert job.status == "completed"
        assert job.total_rooms == 0

    @pytest.mark.asyncio
    async def test_cancel_batch_job(
        self, mock_openai_service, mock_library, render_config
    ):
        """Test cancelling a batch job."""
        # Create slow mock to allow cancellation
        async def slow_render(*args, **kwargs):
            await asyncio.sleep(0.5)
            return {"url": "https://test.com/img.png", "revised_prompt": "test"}

        mock_openai_service.generate_concept_render = slow_render

        # Create floor plan with many rooms
        rooms = [
            Room(id=f"room{i}", name=f"Room {i}", polygon=[(0, 0), (1, 0), (1, 1), (0, 1)])
            for i in range(10)
        ]
        floor_plan = FloorPlan(
            metadata=FloorPlanMetadata(filename="large.dxf"),
            rooms=rooms,
        )

        batch = BatchRenderer(mock_openai_service, mock_library, max_concurrent=1)
        job_id = await batch.start(floor_plan, [], render_config)

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Cancel the job
        result = batch.cancel(job_id)
        assert result is True

        job = batch.get_status(job_id)
        assert job.status == "cancelled"

    def test_list_jobs(self, mock_openai_service, mock_library):
        """Test listing jobs."""
        batch = BatchRenderer(mock_openai_service, mock_library)

        # Create some jobs directly via job manager
        batch.job_manager.create_job("plan1", 2)
        batch.job_manager.create_job("plan2", 3)

        jobs = batch.list_jobs()
        assert len(jobs) == 2

    def test_list_jobs_filtered(self, mock_openai_service, mock_library):
        """Test listing jobs with filter."""
        batch = BatchRenderer(mock_openai_service, mock_library)

        batch.job_manager.create_job("plan1", 2)
        batch.job_manager.create_job("plan2", 3)
        batch.job_manager.create_job("plan1", 1)

        jobs = batch.list_jobs(floor_plan_id="plan1")
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_render_single_convenience(
        self, mock_openai_service, mock_library, sample_room, render_config
    ):
        """Test single room convenience method."""
        batch = BatchRenderer(mock_openai_service, mock_library)

        result = await batch.render_single(sample_room, [], render_config)

        assert result.room_id == "room1"
        assert result.image_url == "https://example.com/render.png"


# ============================================================================
# Integration Tests
# ============================================================================


class TestRenderPipelineIntegration:
    """Integration tests for the render pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline(
        self, mock_openai_service, mock_library, sample_floor_plan, sample_assignments, render_config
    ):
        """Test full render pipeline from start to finish."""
        batch = BatchRenderer(mock_openai_service, mock_library)

        # Start batch job
        job_id = await batch.start(sample_floor_plan, sample_assignments, render_config)
        assert job_id is not None

        # Wait for completion
        for _ in range(100):
            await asyncio.sleep(0.05)
            job = batch.get_status(job_id)
            if job.is_complete:
                break

        # Verify completion
        job = batch.get_status(job_id)
        assert job.status == "completed"
        assert job.completed_rooms == 3
        assert len(job.results) == 3
        assert job.progress == 100.0

        # Verify results
        for result in job.results:
            assert result.image_url == "https://example.com/render.png"
            assert result.room_id in ["room1", "room2", "room3"]

    @pytest.mark.asyncio
    async def test_pipeline_with_failures(self, mock_library, sample_floor_plan, render_config):
        """Test pipeline handles failures gracefully."""
        call_count = 0

        async def flaky_render(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Random failure")
            return {"url": "https://test.com/img.png", "revised_prompt": "test"}

        mock_service = MagicMock()
        mock_service.generate_concept_render = flaky_render

        batch = BatchRenderer(mock_service, mock_library, max_concurrent=1)
        # Use renderer with no retries
        batch.room_renderer = RoomRenderer(mock_service, mock_library, max_retries=0)

        job_id = await batch.start(sample_floor_plan, [], render_config)

        # Wait for completion
        for _ in range(100):
            await asyncio.sleep(0.05)
            job = batch.get_status(job_id)
            if job.is_complete:
                break

        job = batch.get_status(job_id)
        assert job.status == "completed"
        assert job.completed_rooms == 3
        # Some should succeed, some should fail
        assert job.successful_renders + job.failed_renders == 3


# ============================================================================
# Module Import Test
# ============================================================================


class TestModuleImports:
    """Test that all module exports work correctly."""

    def test_import_all(self):
        """Test importing all exports from core.render."""
        from core.render import (
            BatchRenderer,
            ContentPolicyError,
            JobManager,
            PromptBuilder,
            RateLimitError,
            RenderConfig,
            RenderError,
            RenderException,
            RenderJob,
            RenderResult,
            RoomRenderer,
            TimeoutError,
        )

        # Just verify they imported correctly
        assert RenderConfig is not None
        assert RenderResult is not None
        assert RenderJob is not None
        assert RoomRenderer is not None
        assert BatchRenderer is not None
        assert JobManager is not None
        assert PromptBuilder is not None
        assert RenderException is not None
        assert ContentPolicyError is not None
        assert RateLimitError is not None
        assert TimeoutError is not None
        assert RenderError is not None
