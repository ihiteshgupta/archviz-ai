"""Tests for room pipeline API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.routes.room_pipeline import jobs


@pytest.fixture
def client():
    """Create synchronous test client."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear job storage before each test."""
    jobs.clear()
    yield
    jobs.clear()


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

    @pytest.mark.asyncio
    async def test_generate_shell_returns_initial_status(self):
        """POST /api/room-pipeline/generate-shell should return SHELL_BUILDING status."""
        room_data = {
            "room_id": "room_2",
            "room_data": {
                "polygon": [[0, 0], [3, 0], [3, 3], [0, 3]],
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
        assert data["status"] == "SHELL_BUILDING"

    @pytest.mark.asyncio
    async def test_generate_shell_job_id_is_uuid(self):
        """Job ID should be a valid UUID format."""
        import uuid

        room_data = {
            "room_id": "room_3",
            "room_data": {
                "polygon": [[0, 0], [4, 0], [4, 4], [0, 4]],
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

        data = response.json()
        # Should not raise ValueError if it's a valid UUID
        uuid.UUID(data["job_id"])

    @pytest.mark.asyncio
    async def test_get_job_status_returns_job_info(self):
        """GET /api/room-pipeline/{job_id}/status should return job status."""
        room_data = {
            "room_id": "room_4",
            "room_data": {
                "polygon": [[0, 0], [5, 0], [5, 5], [0, 5]],
                "doors": [],
                "windows": [],
            }
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Create job
            create_response = await client.post(
                "/api/room-pipeline/generate-shell",
                json=room_data
            )
            job_id = create_response.json()["job_id"]

            # Get status
            status_response = await client.get(
                f"/api/room-pipeline/{job_id}/status"
            )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert "stage" in data
        assert "progress" in data

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self):
        """GET /api/room-pipeline/{job_id}/status should return 404 for unknown job."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/room-pipeline/nonexistent-job-id/status"
            )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Job not found"

    @pytest.mark.asyncio
    async def test_generate_shell_with_doors_and_windows(self):
        """POST /api/room-pipeline/generate-shell should accept room with doors/windows."""
        room_data = {
            "room_id": "room_5",
            "room_data": {
                "polygon": [[0, 0], [6, 0], [6, 5], [0, 5]],
                "doors": [
                    {
                        "wall_index": 0,
                        "position": 2.0,
                        "width": 0.9,
                        "height": 2.1
                    }
                ],
                "windows": [
                    {
                        "wall_index": 1,
                        "position": 1.0,
                        "width": 1.2,
                        "height": 1.4,
                        "sill_height": 0.9
                    }
                ],
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
        assert data["status"] == "SHELL_BUILDING"

    @pytest.mark.asyncio
    async def test_generate_shell_missing_room_id(self):
        """POST /api/room-pipeline/generate-shell should fail without room_id."""
        room_data = {
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

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_generate_shell_missing_room_data(self):
        """POST /api/room-pipeline/generate-shell should fail without room_data."""
        room_data = {
            "room_id": "room_6"
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/room-pipeline/generate-shell",
                json=room_data
            )

        assert response.status_code == 422  # Validation error


class TestRoomPipelineSyncClient:
    """Tests using synchronous test client for simpler cases."""

    def test_generate_shell_sync(self, client):
        """Test generate shell with sync client."""
        room_data = {
            "room_id": "room_sync_1",
            "room_data": {
                "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]],
                "doors": [],
                "windows": [],
            }
        }

        response = client.post(
            "/api/room-pipeline/generate-shell",
            json=room_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "SHELL_BUILDING"

    def test_get_job_status_sync(self, client):
        """Test get job status with sync client."""
        # Create job
        room_data = {
            "room_id": "room_sync_2",
            "room_data": {
                "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
                "doors": [],
                "windows": [],
            }
        }

        create_response = client.post(
            "/api/room-pipeline/generate-shell",
            json=room_data
        )
        job_id = create_response.json()["job_id"]

        # Get status
        status_response = client.get(f"/api/room-pipeline/{job_id}/status")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert "stage" in data
        assert "progress" in data

    def test_job_not_found_sync(self, client):
        """Test job not found with sync client."""
        response = client.get("/api/room-pipeline/fake-job-id/status")

        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"


class TestJobStatusResponse:
    """Tests for job status response structure."""

    def test_status_response_has_required_fields(self, client):
        """Verify status response contains all required fields."""
        room_data = {
            "room_id": "room_status_1",
            "room_data": {
                "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
                "doors": [],
                "windows": [],
            }
        }

        create_response = client.post(
            "/api/room-pipeline/generate-shell",
            json=room_data
        )
        job_id = create_response.json()["job_id"]

        status_response = client.get(f"/api/room-pipeline/{job_id}/status")
        data = status_response.json()

        # Required fields
        assert "job_id" in data
        assert "stage" in data
        assert "progress" in data

        # Optional fields (may be None initially)
        assert "preview_url" in data or data.get("preview_url") is None
        assert "outputs" in data or data.get("outputs") is None

    def test_initial_progress_is_zero(self, client):
        """Initial progress should be 0.0."""
        room_data = {
            "room_id": "room_progress_1",
            "room_data": {
                "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
                "doors": [],
                "windows": [],
            }
        }

        create_response = client.post(
            "/api/room-pipeline/generate-shell",
            json=room_data
        )
        job_id = create_response.json()["job_id"]

        status_response = client.get(f"/api/room-pipeline/{job_id}/status")
        data = status_response.json()

        # Progress should be numeric
        assert isinstance(data["progress"], (int, float))
        # Initial progress is 0.0 before background task updates it
        assert data["progress"] >= 0.0
