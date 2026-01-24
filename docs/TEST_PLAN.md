# ArchViz AI - Comprehensive Test Plan

> Version 1.0 | Created: 2026-01-22

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Test Strategy](#2-test-strategy)
3. [Test Scope](#3-test-scope)
4. [Gap Analysis](#4-gap-analysis)
5. [New Test Cases](#5-new-test-cases)
6. [Manual Testing Checklist](#6-manual-testing-checklist)
7. [Performance & Load Testing Plan](#7-performance--load-testing-plan)
8. [Risk Assessment](#8-risk-assessment)
9. [Entry/Exit Criteria](#9-entryexit-criteria)
10. [Test Environment](#10-test-environment)

---

## 1. Executive Summary

### Application Overview
ArchViz AI transforms DWG/DXF CAD files into photorealistic renders and interactive walkthroughs using Azure OpenAI (GPT-4o + DALL-E 3).

### Test Objectives
- Validate end-to-end user workflows from file upload to render download
- Ensure API reliability and correct error handling
- Verify 3D visualization accuracy and performance
- Validate AI integration (Azure OpenAI) with proper fallback behavior
- Confirm cross-browser and responsive design compliance

### Key Metrics
| Metric | Target |
|--------|--------|
| Unit Test Coverage | > 80% |
| API Response Time (p95) | < 500ms (non-AI endpoints) |
| AI Render Success Rate | > 95% |
| Critical Bug Count | 0 at release |
| UI Accessibility Score | WCAG 2.1 AA |

---

## 2. Test Strategy

### Testing Pyramid

```
                    ┌─────────────┐
                    │   E2E/UI    │  ~10% - Playwright
                    │   Tests     │
                    ├─────────────┤
                    │ Integration │  ~20% - pytest + TestClient
                    │   Tests     │
                    ├─────────────┤
                    │    Unit     │  ~70% - pytest, Jest
                    │   Tests     │
                    └─────────────┘
```

### Test Categories

| Category | Framework | Markers/Tags | Run Frequency |
|----------|-----------|--------------|---------------|
| Unit Tests | pytest, Jest | default | Every commit |
| Integration Tests | pytest | `@pytest.mark.integration` | PR merge |
| E2E Tests | Playwright | - | Nightly/Release |
| Performance Tests | Locust, k6 | - | Weekly/Release |
| Manual Tests | - | - | Release |

### Test Data Strategy
- **Fixtures**: DWG/DXF sample files in `tests/fixtures/`
- **Mocking**: Azure OpenAI responses mocked for unit tests
- **Test Isolation**: In-memory storage reset between tests

---

## 3. Test Scope

### In Scope

#### Backend (FastAPI)
| Module | Priority | Coverage Target |
|--------|----------|-----------------|
| `api/routes/projects.py` | P0 | 90% |
| `api/routes/render.py` | P0 | 85% |
| `api/routes/materials.py` | P1 | 80% |
| `api/routes/chat.py` | P1 | 75% |
| `core/dwg_parser/` | P0 | 90% |
| `core/model_gen/` | P1 | 80% |
| `core/render/` | P0 | 85% |
| `core/materials/` | P1 | 80% |
| `core/walkthrough/` | P2 | 70% |

#### Frontend (Next.js)
| Component | Priority | Test Type |
|-----------|----------|-----------|
| Dashboard/Home | P0 | E2E + Manual |
| FileUpload | P0 | E2E + Unit |
| FloorPlan3DViewer | P1 | Manual + Visual |
| Render Studio | P0 | E2E + Manual |
| Gallery | P1 | E2E + Manual |
| Material Library | P2 | E2E |

### Out of Scope
- Electron desktop app (separate test plan)
- Third-party service internals (Azure OpenAI, LibreDWG)
- Infrastructure/DevOps (covered by CI/CD)

---

## 4. Gap Analysis

### Current Test Coverage Analysis

| Test File | Lines | Focus Area | Gap Assessment |
|-----------|-------|------------|----------------|
| `test_api.py` | 70 | Basic health checks | Missing: auth, rate limiting |
| `test_projects.py` | 100 | Project CRUD | Missing: concurrent access, large files |
| `test_render.py` | 330 | Render jobs | Missing: timeout handling, retry logic |
| `test_render_pipeline.py` | 850 | Batch rendering | Good coverage |
| `test_materials.py` | 115 | Material routes | Missing: invalid IDs, edge categories |
| `test_materials_core.py` | 530 | Material library | Good coverage |
| `test_chat.py` | 165 | LLM chat | Missing: rate limits, token limits |
| `test_dwg_parser.py` | - | DWG parsing | Need: corrupted files, edge formats |
| `test_model_gen.py` | 520 | 3D generation | Missing: memory limits |
| `test_e2e_workflow.py` | 285 | User workflows | Good coverage |
| `test_room_classifier.py` | 540 | Room detection | Good coverage |
| `test_room_detection.py` | 370 | Room boundaries | Good coverage |
| `test_wall_graph.py` | 180 | Wall topology | Missing: complex geometries |
| `test_spatial_utils.py` | 85 | Geometry utils | Good coverage |
| `test_furniture_placer.py` | 200 | Furniture AI | Missing: API failures |
| `test_furniture_library.py` | 130 | Furniture assets | Good coverage |
| `test_shell_builder.py` | 170 | 3D mesh gen | Missing: degenerate polygons |
| `test_texture_generator.py` | 190 | DALL-E textures | Missing: content policy errors |
| `test_blender_renderer.py` | 25 | Blender render | Very thin - needs expansion |
| `test_video_generator.py` | 45 | Video export | Minimal - needs expansion |
| `test_camera_path.py` | 30 | Camera paths | Minimal - needs expansion |
| `test_room_pipeline_api.py` | 280 | Room pipeline API | Good coverage |
| `test_room_pipeline_integration.py` | 215 | Pipeline E2E | Good coverage |

### Identified Gaps

#### Critical Gaps (P0)
1. **No frontend unit tests** - React components untested
2. **No E2E browser tests** - Playwright not configured
3. **Limited error scenario coverage** - Need Azure API failures, timeouts
4. **No security tests** - File upload validation, injection attacks
5. **Blender renderer barely tested** - Only 1 basic test

#### High Priority Gaps (P1)
6. **No concurrent access tests** - Multiple users, race conditions
7. **Missing boundary tests** - Max file size, max rooms, max renders
8. **No retry/resilience tests** - Network failures, partial failures
9. **Video generator thin coverage** - Missing format tests, duration limits
10. **No accessibility tests** - WCAG compliance

#### Medium Priority Gaps (P2)
11. **No visual regression tests** - 3D viewer screenshots
12. **Limited notification tests** - Firebase push notifications
13. **No mobile responsiveness tests** - Automated viewport tests

---

## 5. New Test Cases

### 5.1 Security Tests

```python
# tests/test_security.py

class TestFileUploadSecurity:
    """Security tests for file upload functionality."""

    def test_reject_executable_file(self, client):
        """Reject files with executable extensions."""
        # Create project first
        project = client.post("/api/projects/", json={"name": "Security Test"}).json()

        # Attempt to upload .exe disguised as .dwg
        files = {"file": ("malicious.dwg.exe", b"MZ...", "application/octet-stream")}
        response = client.post(f"/api/projects/{project['id']}/upload", files=files)
        assert response.status_code == 400

    def test_reject_oversized_file(self, client):
        """Reject files exceeding size limit (50MB)."""
        project = client.post("/api/projects/", json={"name": "Size Test"}).json()

        # 51MB file
        large_content = b"0" * (51 * 1024 * 1024)
        files = {"file": ("large.dxf", large_content, "application/octet-stream")}
        response = client.post(f"/api/projects/{project['id']}/upload", files=files)
        assert response.status_code == 413

    def test_path_traversal_prevention(self, client):
        """Prevent path traversal in filenames."""
        project = client.post("/api/projects/", json={"name": "Path Test"}).json()

        # Malicious filename
        files = {"file": ("../../../etc/passwd.dxf", b"content", "application/octet-stream")}
        response = client.post(f"/api/projects/{project['id']}/upload", files=files)
        # Should sanitize filename or reject
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            assert ".." not in response.json().get("file_name", "")

    def test_xss_in_project_name(self, client):
        """Prevent XSS in project name."""
        response = client.post(
            "/api/projects/",
            json={"name": "<script>alert('xss')</script>"}
        )
        assert response.status_code == 200
        # Name should be escaped or sanitized
        assert "<script>" not in response.json()["name"] or response.json()["name"].startswith("&lt;")


class TestAPISecurityHeaders:
    """Test security headers in API responses."""

    def test_cors_restricted(self, client):
        """CORS should only allow configured origins."""
        response = client.get(
            "/api/health",
            headers={"Origin": "https://malicious-site.com"}
        )
        assert "access-control-allow-origin" not in response.headers or \
               response.headers.get("access-control-allow-origin") != "https://malicious-site.com"

    def test_content_type_enforced(self, client):
        """API should enforce content-type for POST requests."""
        response = client.post(
            "/api/projects/",
            content="name=test",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422
```

### 5.2 Resilience Tests

```python
# tests/test_resilience.py

import pytest
from unittest.mock import patch, AsyncMock

class TestAzureOpenAIFailures:
    """Test handling of Azure OpenAI service failures."""

    @pytest.mark.integration
    async def test_dalle_timeout_handling(self, client):
        """Handle DALL-E timeout gracefully."""
        with patch("core.azure.openai_service.AzureOpenAIService.generate_concept_render") as mock:
            mock.side_effect = TimeoutError("Request timed out")

            response = client.post(
                "/api/render/quick",
                json={"room_type": "bedroom", "style": "modern"}
            )
            assert response.status_code == 504
            assert "timeout" in response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_dalle_rate_limit_handling(self, client):
        """Handle DALL-E rate limits with retry info."""
        with patch("core.azure.openai_service.AzureOpenAIService.generate_concept_render") as mock:
            mock.side_effect = Exception("Rate limit exceeded. Retry after 60 seconds.")

            response = client.post(
                "/api/render/quick",
                json={"room_type": "kitchen", "style": "scandinavian"}
            )
            assert response.status_code == 429
            assert "retry" in response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_dalle_content_policy_violation(self, client):
        """Handle content policy violations gracefully."""
        with patch("core.azure.openai_service.AzureOpenAIService.generate_concept_render") as mock:
            mock.side_effect = Exception("Content policy violation")

            response = client.post(
                "/api/render/quick",
                json={"room_type": "bathroom", "style": "modern", "additional_details": "explicit content"}
            )
            assert response.status_code == 400
            assert "content policy" in response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_chat_token_limit_exceeded(self, client):
        """Handle chat token limit gracefully."""
        # Very long conversation history
        long_history = [{"role": "user", "content": "x" * 1000}] * 100

        response = client.post(
            "/api/chat/",
            json={"message": "Help me", "conversation_history": long_history}
        )
        # Should either truncate or return error
        assert response.status_code in [200, 400]


class TestBatchRenderResilience:
    """Test batch render resilience to partial failures."""

    @pytest.mark.integration
    async def test_batch_continues_after_single_failure(self, client):
        """Batch job should continue even if one room fails."""
        # Start batch with 3 rooms
        response = client.post(
            "/api/render/batch",
            json={
                "floor_plan_id": "test-plan",
                "rooms": [
                    {"id": "room1", "name": "Living Room"},
                    {"id": "room2", "name": "Kitchen"},
                    {"id": "room3", "name": "Bedroom"}
                ]
            }
        )
        assert response.status_code in [200, 503]  # 503 if Azure not configured

        if response.status_code == 200:
            job = response.json()
            # Job should track individual failures
            assert "failed_renders" in job

    @pytest.mark.integration
    async def test_batch_cancellation_cleanup(self, client):
        """Cancelled batch jobs should cleanup properly."""
        # Start batch
        start_response = client.post(
            "/api/render/batch",
            json={
                "floor_plan_id": "cancel-test",
                "rooms": [{"id": "r1", "name": "Room"}]
            }
        )

        if start_response.status_code == 200:
            job_id = start_response.json()["id"]

            # Cancel it
            cancel_response = client.post(f"/api/render/batch/{job_id}/cancel")
            assert cancel_response.status_code in [200, 400]  # 400 if already completed
```

### 5.3 Boundary Tests

```python
# tests/test_boundaries.py

import pytest

class TestProjectBoundaries:
    """Test project boundary conditions."""

    def test_max_project_name_length(self, client):
        """Project name should have reasonable max length."""
        long_name = "x" * 500
        response = client.post("/api/projects/", json={"name": long_name})
        # Should either truncate or reject
        assert response.status_code in [200, 400, 422]
        if response.status_code == 200:
            assert len(response.json()["name"]) <= 255

    def test_empty_project_name(self, client):
        """Empty project name should be rejected."""
        response = client.post("/api/projects/", json={"name": ""})
        assert response.status_code == 422

    def test_whitespace_only_project_name(self, client):
        """Whitespace-only project name should be rejected."""
        response = client.post("/api/projects/", json={"name": "   "})
        assert response.status_code == 422

    def test_unicode_project_name(self, client):
        """Unicode characters in project name should work."""
        response = client.post("/api/projects/", json={"name": "Проект 建築 🏠"})
        assert response.status_code == 200
        assert response.json()["name"] == "Проект 建築 🏠"


class TestRenderBoundaries:
    """Test render boundary conditions."""

    def test_invalid_resolution(self, client):
        """Invalid resolution should be rejected."""
        project = client.post("/api/projects/", json={"name": "Res Test"}).json()

        response = client.post(
            "/api/render/",
            json={"project_id": project["id"], "resolution": 99999}
        )
        assert response.status_code in [400, 422]

    def test_invalid_render_style(self, client):
        """Invalid render style should be rejected."""
        project = client.post("/api/projects/", json={"name": "Style Test"}).json()

        response = client.post(
            "/api/render/",
            json={"project_id": project["id"], "style": "nonexistent_style"}
        )
        assert response.status_code == 422

    def test_max_rooms_in_batch(self, client):
        """Batch render should handle max room limit."""
        rooms = [{"id": f"room{i}", "name": f"Room {i}"} for i in range(100)]

        response = client.post(
            "/api/render/batch",
            json={"floor_plan_id": "many-rooms", "rooms": rooms}
        )
        # Should either accept or return specific limit error
        assert response.status_code in [200, 400, 503]


class TestFloorPlanBoundaries:
    """Test floor plan parsing boundaries."""

    def test_floor_plan_max_walls(self, client, tmp_path):
        """Parser should handle floor plans with many walls."""
        # This would need a fixture DXF with many walls
        pass  # Implement with fixture

    def test_floor_plan_zero_area_room(self, client):
        """Parser should handle degenerate rooms."""
        # Room with zero area (line or point)
        pass  # Implement with fixture

    def test_floor_plan_self_intersecting_walls(self, client):
        """Parser should handle self-intersecting walls."""
        pass  # Implement with fixture
```

### 5.4 Concurrent Access Tests

```python
# tests/test_concurrent.py

import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor

class TestConcurrentAccess:
    """Test concurrent access scenarios."""

    def test_concurrent_project_creation(self, client):
        """Multiple projects can be created concurrently."""
        def create_project(i):
            return client.post(
                "/api/projects/",
                json={"name": f"Concurrent Project {i}"}
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_project, i) for i in range(10)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # All should have unique IDs
        ids = [r.json()["id"] for r in results]
        assert len(ids) == len(set(ids))

    def test_concurrent_render_jobs(self, client):
        """Multiple render jobs can be queued concurrently."""
        # Create project first
        project = client.post("/api/projects/", json={"name": "Concurrent Render"}).json()

        def create_render(i):
            return client.post(
                "/api/render/",
                json={"project_id": project["id"], "style": "modern_minimalist"}
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_render, i) for i in range(5)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

    def test_concurrent_read_write(self, client):
        """Read and write operations can happen concurrently."""
        project = client.post("/api/projects/", json={"name": "RW Test"}).json()
        project_id = project["id"]

        def read_project():
            return client.get(f"/api/projects/{project_id}")

        def list_projects():
            return client.get("/api/projects/")

        with ThreadPoolExecutor(max_workers=10) as executor:
            read_futures = [executor.submit(read_project) for _ in range(5)]
            list_futures = [executor.submit(list_projects) for _ in range(5)]

            all_results = [f.result() for f in read_futures + list_futures]

        assert all(r.status_code == 200 for r in all_results)
```

### 5.5 Frontend Unit Tests (New)

```typescript
// frontend/src/components/__tests__/FileUpload.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileUpload } from '../FileUpload';

describe('FileUpload', () => {
  const mockOnUpload = jest.fn();

  beforeEach(() => {
    mockOnUpload.mockClear();
  });

  it('renders upload area', () => {
    render(<FileUpload onUpload={mockOnUpload} />);
    expect(screen.getByText(/drag.*drop/i)).toBeInTheDocument();
  });

  it('accepts .dwg files', async () => {
    render(<FileUpload onUpload={mockOnUpload} />);

    const file = new File(['content'], 'test.dwg', { type: 'application/octet-stream' });
    const input = screen.getByTestId('file-input');

    await userEvent.upload(input, file);

    expect(mockOnUpload).toHaveBeenCalledWith(file);
  });

  it('accepts .dxf files', async () => {
    render(<FileUpload onUpload={mockOnUpload} />);

    const file = new File(['content'], 'test.dxf', { type: 'application/octet-stream' });
    const input = screen.getByTestId('file-input');

    await userEvent.upload(input, file);

    expect(mockOnUpload).toHaveBeenCalledWith(file);
  });

  it('rejects non-CAD files', async () => {
    render(<FileUpload onUpload={mockOnUpload} />);

    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('file-input');

    await userEvent.upload(input, file);

    expect(mockOnUpload).not.toHaveBeenCalled();
    expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();
  });

  it('shows upload progress', async () => {
    render(<FileUpload onUpload={mockOnUpload} uploading={true} progress={50} />);

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
  });

  it('handles drag and drop', async () => {
    render(<FileUpload onUpload={mockOnUpload} />);

    const dropZone = screen.getByTestId('drop-zone');
    const file = new File(['content'], 'test.dwg', { type: 'application/octet-stream' });

    fireEvent.dragEnter(dropZone);
    expect(dropZone).toHaveClass('drag-active');

    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] }
    });

    expect(mockOnUpload).toHaveBeenCalledWith(file);
  });
});
```

```typescript
// frontend/src/lib/__tests__/api.test.ts

import { createProject, uploadFile, getProject } from '../api';

// Mock fetch
global.fetch = jest.fn();

describe('API Client', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  describe('createProject', () => {
    it('creates project successfully', async () => {
      const mockProject = { id: '123', name: 'Test', status: 'created' };
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockProject,
      });

      const result = await createProject('Test', 'Description');

      expect(fetch).toHaveBeenCalledWith('/api/projects/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Test', description: 'Description' }),
      });
      expect(result).toEqual(mockProject);
    });

    it('throws on API error', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Server error' }),
      });

      await expect(createProject('Test')).rejects.toThrow('Server error');
    });
  });

  describe('uploadFile', () => {
    it('uploads file with FormData', async () => {
      const mockResponse = { status: 'success', project_id: '123' };
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const file = new File(['content'], 'test.dwg');
      const result = await uploadFile('123', file);

      expect(fetch).toHaveBeenCalledWith('/api/projects/123/upload', {
        method: 'POST',
        body: expect.any(FormData),
      });
      expect(result).toEqual(mockResponse);
    });
  });
});
```

---

## 6. Manual Testing Checklist

### 6.1 Dashboard / Home Page

| ID | Test Case | Steps | Expected Result | Pass/Fail |
|----|-----------|-------|-----------------|-----------|
| D-01 | Load empty dashboard | Navigate to `/` with no projects | "No projects" message displayed | |
| D-02 | Create new project | Click "New Project" → Enter name → Create | Project card appears in list | |
| D-03 | Project card displays info | View project card | Shows name, status, timestamp | |
| D-04 | Quick upload via drag-drop | Drag DWG to upload zone | Auto-creates project, uploads file | |
| D-05 | Delete project | Click delete on project card → Confirm | Project removed from list | |
| D-06 | Navigate to project | Click project card | Navigates to `/project/[id]` | |
| D-07 | Search/filter projects | Type in search box | Projects filtered by name | |
| D-08 | Pagination | Have 20+ projects → Navigate pages | Pagination works correctly | |
| D-09 | Loading state | Slow connection / Loading | Skeleton loaders displayed | |
| D-10 | Error state | API unavailable | Error message with retry | |

### 6.2 Project Detail Page

| ID | Test Case | Steps | Expected Result | Pass/Fail |
|----|-----------|-------|-----------------|-----------|
| P-01 | View project info | Navigate to `/project/[id]` | Name, description, status shown | |
| P-02 | Upload DWG file | Click upload → Select .dwg | File uploaded, parsing starts | |
| P-03 | Upload DXF file | Click upload → Select .dxf | File uploaded, parsing starts | |
| P-04 | Reject invalid file | Try upload .pdf | Error: "Invalid file type" | |
| P-05 | View 2D floor plan | After parsing | 2D SVG preview displayed | |
| P-06 | Toggle 2D/3D view | Click view toggle | Switches between views | |
| P-07 | 3D viewer loads | Switch to 3D view | Three.js canvas renders | |
| P-08 | 3D orbit controls | Mouse drag on 3D view | Camera orbits scene | |
| P-09 | 3D zoom | Scroll wheel on 3D | Zoom in/out works | |
| P-10 | Room selection | Click room in 3D | Room highlights, info panel shows | |
| P-11 | Room list panel | View rooms panel | All detected rooms listed | |
| P-12 | Navigate to Render Studio | Click "Render" button | Navigates to render page | |
| P-13 | Navigate to Gallery | Click "Gallery" button | Navigates to gallery page | |
| P-14 | Handle parse error | Upload corrupt file | Error message, retry option | |

### 6.3 Render Studio

| ID | Test Case | Steps | Expected Result | Pass/Fail |
|----|-----------|-------|-----------------|-----------|
| R-01 | Room list displays | Open Render Studio | All rooms from floor plan shown | |
| R-02 | Select single room | Click room checkbox | Room selected for render | |
| R-03 | Select all rooms | Click "Select All" | All rooms selected | |
| R-04 | Deselect all rooms | Click "Deselect All" | No rooms selected | |
| R-05 | Style preset selector | Open style dropdown | All 7 styles shown | |
| R-06 | Apply style preset | Select "Scandinavian" | Preview updates, materials change | |
| R-07 | Material assignment | Click room → Assign floor material | Material assigned to room | |
| R-08 | Lighting options | Change lighting dropdown | Option saved for render | |
| R-09 | Time of day options | Change time dropdown | Option saved for render | |
| R-10 | Resolution options | Change resolution | Option saved | |
| R-11 | Start single render | Select 1 room → Render | Render job starts | |
| R-12 | Start batch render | Select 3+ rooms → Render | Batch job starts | |
| R-13 | Render progress | During render | Progress bar updates | |
| R-14 | Render completion | Render finishes | Success message, preview shown | |
| R-15 | Render failure | Trigger failure | Error message, retry option | |
| R-16 | Cancel render | Click cancel during render | Job cancelled | |
| R-17 | Azure unavailable | No Azure config | Clear error message | |

### 6.4 Gallery

| ID | Test Case | Steps | Expected Result | Pass/Fail |
|----|-----------|-------|-----------------|-----------|
| G-01 | View all renders | Open Gallery | Grid of all renders shown | |
| G-02 | Empty gallery | No renders yet | "No renders" message | |
| G-03 | Render thumbnail | View thumbnail | Correct image displayed | |
| G-04 | Open fullscreen | Click render | Fullscreen lightbox opens | |
| G-05 | Close fullscreen | Click X or Escape | Lightbox closes | |
| G-06 | Download render | Click download button | Image downloads | |
| G-07 | Download all | Click "Download All" | ZIP file downloads | |
| G-08 | Filter by room | Select room filter | Only that room's renders shown | |
| G-09 | Filter by style | Select style filter | Only that style's renders shown | |
| G-10 | Sort by date | Toggle sort | Newest/oldest first | |
| G-11 | Compare mode | Select 2 renders | Side-by-side comparison | |
| G-12 | Delete render | Click delete → Confirm | Render removed | |
| G-13 | Render metadata | View render details | Shows prompt, timestamp, settings | |

### 6.5 Material Library

| ID | Test Case | Steps | Expected Result | Pass/Fail |
|----|-----------|-------|-----------------|-----------|
| M-01 | View all materials | Open `/materials` | Grid of materials displayed | |
| M-02 | Category tabs | Click category tab | Materials filtered by category | |
| M-03 | Material swatch | View material | Color/texture preview shown | |
| M-04 | Material details | Click material | Detail panel with PBR props | |
| M-05 | Search materials | Type in search | Materials filtered by name | |
| M-06 | Apply to room | Select material → Apply | Material assigned to room | |
| M-07 | Style presets | View presets tab | All presets listed | |
| M-08 | Apply preset | Click preset | All materials auto-assigned | |

### 6.6 Cross-Browser Testing

| ID | Browser | Version | Platform | Result |
|----|---------|---------|----------|--------|
| B-01 | Chrome | Latest | Windows | |
| B-02 | Chrome | Latest | macOS | |
| B-03 | Firefox | Latest | Windows | |
| B-04 | Firefox | Latest | macOS | |
| B-05 | Safari | Latest | macOS | |
| B-06 | Edge | Latest | Windows | |
| B-07 | Chrome | Mobile | Android | |
| B-08 | Safari | Mobile | iOS | |

### 6.7 Responsive Design

| ID | Viewport | Test Case | Expected Result | Pass/Fail |
|----|----------|-----------|-----------------|-----------|
| RD-01 | Desktop (1920px) | Full layout | All panels visible | |
| RD-02 | Laptop (1366px) | Reduced layout | Panels stack appropriately | |
| RD-03 | Tablet (768px) | Touch-friendly | Touch targets 44px+, scrollable | |
| RD-04 | Mobile (375px) | Stacked layout | Single column, hamburger menu | |
| RD-05 | 3D Viewer Mobile | Touch gestures | Pinch zoom, drag rotate works | |

### 6.8 Accessibility Testing

| ID | Test Case | Tool | Expected Result | Pass/Fail |
|----|-----------|------|-----------------|-----------|
| A-01 | Keyboard navigation | Manual | All interactive elements focusable | |
| A-02 | Screen reader | NVDA/VoiceOver | All content announced correctly | |
| A-03 | Color contrast | axe DevTools | WCAG AA (4.5:1) ratio | |
| A-04 | Focus indicators | Manual | Visible focus rings | |
| A-05 | Alt text | Manual | All images have alt text | |
| A-06 | Form labels | axe DevTools | All inputs labeled | |
| A-07 | Error messages | Screen reader | Errors announced to AT users | |

---

## 7. Performance & Load Testing Plan

### 7.1 Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| API Response (p50) | < 100ms | < 200ms |
| API Response (p95) | < 300ms | < 500ms |
| API Response (p99) | < 500ms | < 1000ms |
| Page Load (LCP) | < 2.5s | < 4s |
| Time to Interactive | < 3s | < 5s |
| 3D Viewer FPS | > 30fps | > 15fps |
| File Upload (10MB) | < 5s | < 10s |
| DWG Parse Time | < 10s | < 30s |
| AI Render Time | < 60s | < 120s |

### 7.2 Load Test Scenarios

#### Scenario 1: Normal Load
```yaml
name: Normal Load
duration: 30m
users:
  - ramp_up: 5m to 50 users
  - steady: 20m at 50 users
  - ramp_down: 5m to 0 users
requests:
  - GET /api/projects/ (40%)
  - GET /api/projects/{id} (30%)
  - POST /api/projects/ (10%)
  - GET /api/materials/library (15%)
  - POST /api/render/ (5%)
```

#### Scenario 2: Peak Load
```yaml
name: Peak Load
duration: 15m
users:
  - ramp_up: 2m to 200 users
  - steady: 10m at 200 users
  - ramp_down: 3m to 0 users
requests:
  - Same distribution as Normal Load
```

#### Scenario 3: Stress Test
```yaml
name: Stress Test
duration: 20m
users:
  - continuous_ramp: 0 to 500 users
objective: Find breaking point
monitor:
  - Error rate
  - Response time degradation
  - Memory usage
  - CPU usage
```

#### Scenario 4: Soak Test
```yaml
name: Soak Test
duration: 4h
users:
  - steady: 100 users
objective: Find memory leaks, connection exhaustion
monitor:
  - Memory growth over time
  - Database connections
  - File handles
```

### 7.3 Locust Test Script

```python
# tests/performance/locustfile.py

from locust import HttpUser, task, between, tag

class ArchVizUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        """Create a project on user start."""
        response = self.client.post(
            "/api/projects/",
            json={"name": f"Load Test {self.environment.runner.user_count}"}
        )
        if response.status_code == 200:
            self.project_id = response.json()["id"]
        else:
            self.project_id = None

    @task(40)
    @tag("read")
    def list_projects(self):
        """List all projects."""
        self.client.get("/api/projects/")

    @task(30)
    @tag("read")
    def get_project(self):
        """Get single project."""
        if self.project_id:
            self.client.get(f"/api/projects/{self.project_id}")

    @task(10)
    @tag("write")
    def create_project(self):
        """Create new project."""
        self.client.post(
            "/api/projects/",
            json={"name": "Load Test Project"}
        )

    @task(15)
    @tag("read")
    def get_materials(self):
        """Get material library."""
        self.client.get("/api/materials/library")

    @task(5)
    @tag("write", "ai")
    def create_render(self):
        """Create render job."""
        if self.project_id:
            self.client.post(
                "/api/render/",
                json={
                    "project_id": self.project_id,
                    "style": "modern_minimalist"
                }
            )


class AIHeavyUser(HttpUser):
    """User that heavily uses AI features."""
    wait_time = between(5, 15)

    @task
    @tag("ai")
    def quick_render(self):
        """Generate quick render."""
        self.client.post(
            "/api/render/quick",
            json={
                "room_type": "bedroom",
                "style": "scandinavian",
                "size": "1024x1024"
            }
        )

    @task
    @tag("ai")
    def chat(self):
        """Chat with AI assistant."""
        self.client.post(
            "/api/chat/",
            json={
                "message": "Suggest materials for a modern kitchen",
                "conversation_history": []
            }
        )
```

### 7.4 k6 Load Test Script

```javascript
// tests/performance/k6-load-test.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const projectListTrend = new Trend('project_list_duration');
const renderCreateTrend = new Trend('render_create_duration');

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '5m', target: 50 },   // Stay at 50
    { duration: '2m', target: 100 },  // Ramp to 100
    { duration: '5m', target: 100 },  // Stay at 100
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    errors: ['rate<0.1'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

export default function () {
  // List projects
  let listRes = http.get(`${BASE_URL}/api/projects/`);
  projectListTrend.add(listRes.timings.duration);
  check(listRes, {
    'list status 200': (r) => r.status === 200,
    'list response time OK': (r) => r.timings.duration < 500,
  }) || errorRate.add(1);

  sleep(1);

  // Create project
  let createRes = http.post(
    `${BASE_URL}/api/projects/`,
    JSON.stringify({ name: `k6-test-${Date.now()}` }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(createRes, {
    'create status 200': (r) => r.status === 200,
  }) || errorRate.add(1);

  if (createRes.status === 200) {
    let projectId = createRes.json().id;

    // Create render job
    let renderRes = http.post(
      `${BASE_URL}/api/render/`,
      JSON.stringify({
        project_id: projectId,
        style: 'modern_minimalist',
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    renderCreateTrend.add(renderRes.timings.duration);
    check(renderRes, {
      'render status 200': (r) => r.status === 200,
    }) || errorRate.add(1);
  }

  sleep(2);
}
```

### 7.5 Performance Monitoring

```yaml
# Grafana Dashboard Metrics to Monitor

API Metrics:
  - request_duration_seconds (histogram)
  - request_count_total (counter)
  - error_count_total (counter)
  - active_connections (gauge)

System Metrics:
  - container_cpu_usage_seconds_total
  - container_memory_usage_bytes
  - container_network_receive_bytes_total

Azure OpenAI Metrics:
  - openai_request_duration_seconds
  - openai_token_usage_total
  - openai_error_count_total
  - openai_rate_limit_hits_total

Business Metrics:
  - projects_created_total
  - renders_completed_total
  - renders_failed_total
  - batch_job_duration_seconds
```

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Azure OpenAI rate limits | High | High | Implement retry with backoff, queue system |
| Large DWG files crash parser | Medium | High | Add file size limits, streaming parser |
| Memory exhaustion in batch renders | Medium | High | Limit concurrent renders, add memory checks |
| 3D viewer crashes on complex plans | Medium | Medium | Progressive loading, LOD system |
| CORS issues in production | Low | High | Test with production URLs before release |
| File upload timeout | Medium | Medium | Chunked uploads, progress feedback |
| Content policy blocks renders | Medium | Medium | Prompt sanitization, clear error messages |

---

## 9. Entry/Exit Criteria

### Entry Criteria
- [ ] Code complete and merged to main branch
- [ ] All unit tests passing (> 80% coverage)
- [ ] Development environment stable
- [ ] Test data prepared (DWG fixtures)
- [ ] Azure OpenAI credentials configured (integration tests)

### Exit Criteria
- [ ] All P0 test cases executed
- [ ] No Critical/Blocker bugs open
- [ ] Performance targets met (see 7.1)
- [ ] Security tests passed
- [ ] Accessibility audit passed (WCAG AA)
- [ ] Sign-off from QA lead

### Bug Severity Definitions

| Severity | Definition | Release Blocker |
|----------|------------|-----------------|
| Critical | System crash, data loss, security vulnerability | Yes |
| High | Major feature broken, no workaround | Yes |
| Medium | Feature partially broken, workaround exists | No |
| Low | Minor issue, cosmetic | No |

---

## 10. Test Environment

### Local Development
```bash
# Start services
npm run dev                 # API + Frontend

# Run tests
pytest tests/ -m "not integration"  # Unit tests only
pytest tests/ -v                     # All tests
npm run test --prefix frontend       # Frontend tests
```

### CI/CD (GitHub Actions)
- Triggered on: Push to main, PR to main
- Runs: lint-python, lint-frontend, test-api, build-docker

### Staging Environment
- URL: https://archviz-staging.azurecontainerapps.io
- Azure OpenAI: Separate staging deployment
- Data: Synthetic test projects

### Production
- Frontend: https://ca-archvizaid-frontend.kindstone-cfc3d3d7.westeurope.azurecontainerapps.io
- API: https://ca-archvizaid-api.kindstone-cfc3d3d7.westeurope.azurecontainerapps.io

---

## Appendix A: Test Data Requirements

### DWG/DXF Fixtures Needed
| File | Description | Use Case |
|------|-------------|----------|
| `simple_room.dxf` | Single rectangular room | Basic parsing |
| `multi_room.dxf` | 5-room apartment | Room detection |
| `complex_plan.dxf` | 20+ rooms, curved walls | Stress test |
| `with_furniture.dxf` | Rooms + furniture blocks | Block parsing |
| `minimal.dxf` | Nearly empty file | Edge case |
| `corrupted.dxf` | Invalid DXF | Error handling |
| `large_plan.dwg` | 40MB commercial building | Size limits |

### Mock Data
- Azure OpenAI responses (JSON fixtures)
- Sample render images (placeholder PNGs)
- Material library subset

---

## Appendix B: Test Automation Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov=core --cov-report=html

# Run specific category
pytest tests/ -m "integration"
pytest tests/ -m "not slow"

# Run single test file
pytest tests/test_projects.py -v

# Run single test
pytest tests/test_projects.py::TestProjectCRUD::test_create_project -v

# Frontend tests
cd frontend && npm test

# E2E tests (when Playwright configured)
cd frontend && npx playwright test

# Performance tests
locust -f tests/performance/locustfile.py --host=http://localhost:8000
k6 run tests/performance/k6-load-test.js

# Lint
ruff check api core
cd frontend && npm run lint
```

---

*Document maintained by QA Team. Last updated: 2026-01-22*
