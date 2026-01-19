# tests/test_room_pipeline_api.py
"""Tests for room pipeline API endpoints."""

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

    @pytest.mark.asyncio
    async def test_generate_shell_returns_shell_building_status(self):
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
    async def test_get_job_status_returns_404_for_unknown_job(self):
        """GET /api/room-pipeline/{job_id}/status should return 404 for unknown job."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/room-pipeline/unknown-job-id/status"
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_job_status_returns_job_info(self):
        """GET /api/room-pipeline/{job_id}/status should return job information."""
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
            # First create a job
            create_response = await client.post(
                "/api/room-pipeline/generate-shell",
                json=room_data
            )
            job_id = create_response.json()["job_id"]

            # Then check its status
            status_response = await client.get(
                f"/api/room-pipeline/{job_id}/status"
            )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert "stage" in data
        assert "progress" in data

    @pytest.mark.asyncio
    async def test_generate_shell_validates_room_data(self):
        """POST /api/room-pipeline/generate-shell should validate required fields."""
        # Missing room_id
        invalid_data = {
            "room_data": {
                "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]],
            }
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/room-pipeline/generate-shell",
                json=invalid_data
            )

        assert response.status_code == 422  # Validation error
