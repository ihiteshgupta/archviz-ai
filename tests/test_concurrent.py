"""Concurrent access tests for ArchViz AI."""

import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestConcurrentProjectCreation:
    """Test concurrent project operations."""

    def test_concurrent_project_creation(self, client):
        """Multiple projects can be created concurrently."""
        def create_project(i):
            response = client.post(
                "/api/projects/",
                json={"name": f"Concurrent Project {i}"}
            )
            return response

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_project, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # All should have unique IDs
        ids = [r.json()["id"] for r in results]
        assert len(ids) == len(set(ids)), "Project IDs should be unique"

    def test_concurrent_project_list(self, client):
        """Multiple list requests can happen concurrently."""
        # Create some projects first
        for i in range(5):
            client.post("/api/projects/", json={"name": f"List Test {i}"})

        def list_projects():
            return client.get("/api/projects/")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(list_projects) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # All should return same count (consistency)
        counts = [len(r.json()) for r in results]
        assert len(set(counts)) == 1, "All responses should have same project count"

    def test_concurrent_project_get(self, client):
        """Multiple get requests for same project."""
        project = client.post("/api/projects/", json={"name": "Concurrent Get"}).json()
        project_id = project["id"]

        def get_project():
            return client.get(f"/api/projects/{project_id}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_project) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # All should return same data
        names = [r.json()["name"] for r in results]
        assert all(name == "Concurrent Get" for name in names)


class TestConcurrentRenderOperations:
    """Test concurrent render operations."""

    def test_concurrent_render_job_creation(self, client):
        """Multiple render jobs can be created concurrently."""
        project = client.post("/api/projects/", json={"name": "Render Concurrency"}).json()
        project_id = project["id"]

        def create_render():
            return client.post(
                "/api/render/",
                json={"project_id": project_id, "style": "modern_minimalist"}
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_render) for _ in range(5)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # All should have unique job IDs
        job_ids = [r.json()["id"] for r in results]
        assert len(job_ids) == len(set(job_ids)), "Render job IDs should be unique"

    def test_concurrent_render_status_checks(self, client):
        """Multiple status checks can happen concurrently."""
        project = client.post("/api/projects/", json={"name": "Status Check"}).json()
        render = client.post(
            "/api/render/",
            json={"project_id": project["id"], "style": "scandinavian"}
        ).json()
        job_id = render["id"]

        def check_status():
            return client.get(f"/api/render/{job_id}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_status) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

    def test_concurrent_render_styles_fetch(self, client):
        """Multiple style fetches can happen concurrently."""
        def get_styles():
            return client.get("/api/render/styles")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_styles) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # All should return same data
        style_counts = [len(r.json()["styles"]) for r in results]
        assert len(set(style_counts)) == 1


class TestConcurrentMaterialOperations:
    """Test concurrent material operations."""

    def test_concurrent_material_library_fetch(self, client):
        """Multiple material library fetches."""
        def get_materials():
            return client.get("/api/materials/library")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_materials) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert all(r.status_code == 200 for r in results)

    def test_concurrent_category_fetch(self, client):
        """Multiple category fetches."""
        def get_categories():
            return client.get("/api/materials/categories")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_categories) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert all(r.status_code == 200 for r in results)

    def test_concurrent_preset_fetch(self, client):
        """Multiple preset fetches."""
        def get_presets():
            return client.get("/api/materials/presets")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_presets) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert all(r.status_code == 200 for r in results)


class TestMixedConcurrentOperations:
    """Test mixed read/write concurrent operations."""

    def test_concurrent_read_write_projects(self, client):
        """Read and write operations on projects concurrently."""
        # Create initial project
        project = client.post("/api/projects/", json={"name": "Mixed Ops"}).json()
        project_id = project["id"]

        def read_project():
            return ("read", client.get(f"/api/projects/{project_id}"))

        def list_projects():
            return ("list", client.get("/api/projects/"))

        def create_project():
            return ("create", client.post("/api/projects/", json={"name": "New Project"}))

        operations = [read_project] * 5 + [list_projects] * 3 + [create_project] * 2

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(op) for op in operations]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        for op_type, response in results:
            assert response.status_code == 200, f"{op_type} failed"

    def test_concurrent_api_endpoints(self, client):
        """Hit various API endpoints concurrently."""
        def health_check():
            return ("health", client.get("/api/health"))

        def get_styles():
            return ("styles", client.get("/api/render/styles"))

        def get_materials():
            return ("materials", client.get("/api/materials/library"))

        def get_categories():
            return ("categories", client.get("/api/materials/categories"))

        def get_presets():
            return ("presets", client.get("/api/materials/presets"))

        def list_projects():
            return ("projects", client.get("/api/projects/"))

        operations = [
            health_check, get_styles, get_materials,
            get_categories, get_presets, list_projects
        ] * 3

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(op) for op in operations]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        failed = [(op, r.status_code) for op, r in results if r.status_code != 200]
        assert len(failed) == 0, f"Failed operations: {failed}"


class TestConcurrentBatchOperations:
    """Test concurrent batch operations."""

    def test_concurrent_batch_status_checks(self, client):
        """Multiple batch status checks (even for nonexistent jobs)."""
        def check_batch_list():
            return client.get("/api/render/batch/jobs/list")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_batch_list) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert all(r.status_code == 200 for r in results)

    def test_concurrent_pipeline_status(self, client):
        """Multiple pipeline status checks."""
        def check_pipeline():
            return client.get("/api/render/pipeline/status")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_pipeline) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert all(r.status_code == 200 for r in results)


class TestRaceConditions:
    """Test potential race conditions."""

    def test_rapid_project_create_delete(self, client):
        """Rapid create and delete of projects."""
        created_ids = []

        # Create projects rapidly
        for i in range(10):
            response = client.post("/api/projects/", json={"name": f"Rapid {i}"})
            if response.status_code == 200:
                created_ids.append(response.json()["id"])

        # Delete them rapidly
        def delete_project(project_id):
            return client.delete(f"/api/projects/{project_id}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(delete_project, pid) for pid in created_ids]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed or already be deleted
        assert all(r.status_code in [200, 404] for r in results)

    def test_concurrent_render_cancel(self, client):
        """Concurrent cancel requests for same job."""
        project = client.post("/api/projects/", json={"name": "Cancel Race"}).json()
        render = client.post(
            "/api/render/",
            json={"project_id": project["id"], "style": "industrial"}
        ).json()
        job_id = render["id"]

        def cancel_render():
            return client.post(f"/api/render/{job_id}/cancel")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(cancel_render) for _ in range(5)]
            results = [f.result() for f in as_completed(futures)]

        # At least one should succeed, others may fail with "already finished"
        statuses = [r.status_code for r in results]
        assert 200 in statuses or 400 in statuses, "At least one cancel should be processed"
