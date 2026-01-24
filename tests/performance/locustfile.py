"""
Locust load testing script for ArchViz AI.

Usage:
    locust -f tests/performance/locustfile.py --host=http://localhost:8000

    # Headless mode:
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
           --headless -u 50 -r 10 --run-time 5m
"""

import json
import random
from locust import HttpUser, task, between, tag, events
from locust.runners import MasterRunner


class ArchVizUser(HttpUser):
    """Standard user performing typical operations."""

    wait_time = between(1, 5)

    def on_start(self):
        """Create a project on user start."""
        response = self.client.post(
            "/api/projects/",
            json={"name": f"Load Test {random.randint(1000, 9999)}"}
        )
        if response.status_code == 200:
            self.project_id = response.json()["id"]
        else:
            self.project_id = None

        # Track created projects for cleanup
        self.created_projects = []
        if self.project_id:
            self.created_projects.append(self.project_id)

    def on_stop(self):
        """Cleanup created projects."""
        for project_id in self.created_projects:
            try:
                self.client.delete(f"/api/projects/{project_id}")
            except Exception:
                pass

    @task(40)
    @tag("read", "projects")
    def list_projects(self):
        """List all projects - most common operation."""
        self.client.get("/api/projects/")

    @task(30)
    @tag("read", "projects")
    def get_project(self):
        """Get single project details."""
        if self.project_id:
            self.client.get(f"/api/projects/{self.project_id}")

    @task(10)
    @tag("write", "projects")
    def create_project(self):
        """Create new project."""
        response = self.client.post(
            "/api/projects/",
            json={"name": f"Perf Test {random.randint(1000, 9999)}"}
        )
        if response.status_code == 200:
            self.created_projects.append(response.json()["id"])

    @task(15)
    @tag("read", "materials")
    def get_materials(self):
        """Get material library."""
        self.client.get("/api/materials/library")

    @task(10)
    @tag("read", "materials")
    def get_categories(self):
        """Get material categories."""
        self.client.get("/api/materials/categories")

    @task(8)
    @tag("read", "materials")
    def get_presets(self):
        """Get style presets."""
        self.client.get("/api/materials/presets")

    @task(5)
    @tag("read", "render")
    def get_render_styles(self):
        """Get available render styles."""
        self.client.get("/api/render/styles")

    @task(3)
    @tag("write", "render")
    def create_render_job(self):
        """Create render job."""
        if self.project_id:
            styles = [
                "modern_minimalist", "scandinavian", "industrial",
                "traditional", "mediterranean", "japanese_zen", "art_deco"
            ]
            self.client.post(
                "/api/render/",
                json={
                    "project_id": self.project_id,
                    "style": random.choice(styles)
                }
            )

    @task(5)
    @tag("read", "render")
    def get_project_renders(self):
        """Get renders for a project."""
        if self.project_id:
            self.client.get(f"/api/render/project/{self.project_id}")

    @task(2)
    @tag("read", "health")
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/api/health")

    @task(3)
    @tag("read", "render")
    def get_pipeline_status(self):
        """Check render pipeline status."""
        self.client.get("/api/render/pipeline/status")

    @task(2)
    @tag("read", "chat")
    def get_chat_status(self):
        """Check chat service status."""
        self.client.get("/api/chat/status")


class AIHeavyUser(HttpUser):
    """User that heavily uses AI features (lower weight)."""

    wait_time = between(5, 15)
    weight = 1  # Lower weight than standard user

    @task(5)
    @tag("ai", "render")
    def quick_render(self):
        """Generate quick render (requires Azure)."""
        room_types = ["bedroom", "living room", "kitchen", "bathroom", "office"]
        styles = ["modern", "scandinavian", "industrial", "traditional"]

        self.client.post(
            "/api/render/quick",
            json={
                "room_type": random.choice(room_types),
                "style": random.choice(styles),
                "size": "1024x1024"
            }
        )

    @task(3)
    @tag("ai", "chat")
    def chat(self):
        """Chat with AI assistant."""
        prompts = [
            "Suggest materials for a modern kitchen",
            "What colors work well in a bedroom?",
            "How can I make a small room look bigger?",
            "Recommend flooring for a living room",
        ]

        self.client.post(
            "/api/chat/",
            json={
                "message": random.choice(prompts),
                "conversation_history": []
            }
        )

    @task(2)
    @tag("ai", "render")
    def quick_render_status(self):
        """Check quick render availability."""
        self.client.get("/api/render/quick/status")


class BatchRenderUser(HttpUser):
    """User performing batch render operations."""

    wait_time = between(10, 30)
    weight = 1  # Lower weight

    def on_start(self):
        """Setup for batch operations."""
        self.batch_job_ids = []

    @task(3)
    @tag("write", "batch")
    def start_batch_render(self):
        """Start a batch render job."""
        rooms = [
            {"id": f"room_{i}", "name": f"Room {i}"}
            for i in range(random.randint(2, 5))
        ]

        response = self.client.post(
            "/api/render/batch",
            json={
                "floor_plan_id": f"test-plan-{random.randint(1000, 9999)}",
                "rooms": rooms,
                "style_preset": random.choice(["modern", "scandinavian"])
            }
        )

        if response.status_code == 200:
            self.batch_job_ids.append(response.json()["id"])

    @task(5)
    @tag("read", "batch")
    def list_batch_jobs(self):
        """List batch render jobs."""
        self.client.get("/api/render/batch/jobs/list?limit=10")

    @task(4)
    @tag("read", "batch")
    def check_batch_status(self):
        """Check batch job status."""
        if self.batch_job_ids:
            job_id = random.choice(self.batch_job_ids)
            self.client.get(f"/api/render/batch/{job_id}")


class RoomPipelineUser(HttpUser):
    """User performing room pipeline operations."""

    wait_time = between(5, 15)
    weight = 1

    @task
    @tag("write", "pipeline")
    def generate_shell(self):
        """Generate room shell."""
        polygons = [
            # Square room
            [[0, 0], [5, 0], [5, 5], [0, 5]],
            # Rectangle
            [[0, 0], [8, 0], [8, 4], [0, 4]],
            # L-shape
            [[0, 0], [6, 0], [6, 3], [3, 3], [3, 6], [0, 6]],
        ]

        self.client.post(
            "/api/room-pipeline/generate-shell",
            json={
                "room_id": f"perf-room-{random.randint(1000, 9999)}",
                "room_data": {
                    "polygon": random.choice(polygons),
                    "height": random.uniform(2.4, 3.2)
                }
            }
        )


# Event handlers for custom metrics
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics."""
    if isinstance(environment.runner, MasterRunner):
        print("Running in distributed mode")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics per request."""
    if exception:
        print(f"Request failed: {name} - {exception}")


if __name__ == "__main__":
    import os
    print("Run with: locust -f locustfile.py --host=http://localhost:8000")
