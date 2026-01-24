# ArchViz AI - User Flows & Testing Guide

> Complete reference document for all user interactions, flows, and test scenarios.

**Live URLs:**
- Frontend: https://ca-archvizaid-frontend.kindstone-cfc3d3d7.westeurope.azurecontainerapps.io
- API: https://ca-archvizaid-api.kindstone-cfc3d3d7.westeurope.azurecontainerapps.io

---

## Table of Contents

1. [Application Overview](#1-application-overview)
2. [Page Routes & Navigation](#2-page-routes--navigation)
3. [User Flow: Project Creation](#3-user-flow-project-creation)
4. [User Flow: File Upload & Parsing](#4-user-flow-file-upload--parsing)
5. [User Flow: Floor Plan Viewing](#5-user-flow-floor-plan-viewing)
6. [User Flow: Render Studio](#6-user-flow-render-studio)
7. [User Flow: Gallery & Downloads](#7-user-flow-gallery--downloads)
8. [User Flow: Material Library](#8-user-flow-material-library)
9. [API Endpoints Reference](#9-api-endpoints-reference)
10. [Test Scenarios](#10-test-scenarios)
11. [Error States & Edge Cases](#11-error-states--edge-cases)
12. [Mobile Responsive Behavior](#12-mobile-responsive-behavior)

---

## 1. Application Overview

### Purpose
ArchViz AI transforms architectural DWG/DXF floor plans into photorealistic room renders using AI (DALL-E 3).

### Core Workflow
```
Upload DWG → Parse Floor Plan → Select Rooms → Configure Materials → Generate Renders → Download
```

### Technology Stack
| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| 3D Visualization | React Three Fiber (Three.js) |
| State Management | React Query (TanStack Query) |
| API | FastAPI (Python) |
| AI Services | Azure OpenAI (GPT-4o, DALL-E 3) |
| DWG Conversion | LibreDWG |
| Deployment | Azure Container Apps |

---

## 2. Page Routes & Navigation

### Route Map

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | Project list, create/upload projects |
| `/materials` | Material Library | Browse materials by category |
| `/project/[id]` | Project Detail | View 2D/3D floor plan, project info |
| `/project/[id]/render` | Render Studio | Configure and execute batch renders |
| `/project/[id]/gallery` | Gallery | View, compare, download renders |
| `/settings` | Settings | App settings (placeholder) |

### Navigation Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      HEADER (All Pages)                      │
│  [Logo] ─────── [Projects] ─── [Materials] ─── [Settings]   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐         ┌───────────┐         ┌──────────┐
   │Dashboard│         │ Materials │         │ Settings │
   │   (/)   │         │/materials │         │/settings │
   └────┬────┘         └───────────┘         └──────────┘
        │
        │ Click Project Card
        ▼
   ┌─────────────────┐
   │  Project Detail │
   │  /project/[id]  │
   └────────┬────────┘
            │
     ┌──────┴──────┐
     ▼             ▼
┌─────────┐  ┌─────────┐
│ Render  │  │ Gallery │
│ Studio  │  │  View   │
│ /render │  │/gallery │
└────┬────┘  └────┬────┘
     │            │
     └─────┬──────┘
           ▼
    [Downloads/Results]
```

---

## 3. User Flow: Project Creation

### Flow Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Dashboard  │────▶│  New Project │────▶│ Upload File  │
│              │     │    Modal     │     │    Modal     │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       │                    │                    │
       ▼                    ▼                    ▼
  Click "New          Enter name &         Select DWG/DXF
   Project"           description              file
                           │                    │
                           ▼                    ▼
                    Click "Create"      Auto-upload starts
                           │                    │
                           ▼                    ▼
                    Project created      Floor plan parsed
                           │                    │
                           └────────┬───────────┘
                                    ▼
                           Project card appears
                              in dashboard
```

### Step-by-Step Actions

| Step | User Action | System Response | API Call |
|------|-------------|-----------------|----------|
| 1 | Click "New Project" button | Modal opens with form | - |
| 2 | Enter project name (required) | Enable "Create" button | - |
| 3 | Enter description (optional) | Update form state | - |
| 4 | Click "Create Project" | Create project, open upload modal | `POST /projects/` |
| 5 | Drag/drop or browse DWG file | Validate file type/size | - |
| 6 | File selected | Start upload with spinner | `POST /projects/{id}/upload` |
| 7 | Upload complete | Parse floor plan | Auto on upload |
| 8 | Parsing complete | Close modal, refresh list | `GET /projects/` |

### Alternative Flow: Quick Upload

| Step | User Action | System Response | API Call |
|------|-------------|-----------------|----------|
| 1 | Drag DWG file to Quick Upload zone | Highlight drop zone | - |
| 2 | Drop file | Auto-create project from filename | `POST /projects/` |
| 3 | - | Auto-upload file | `POST /projects/{id}/upload` |
| 4 | - | Refresh project list | `GET /projects/` |

### Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| Project Name | Required, non-empty | "Project name is required" |
| File Type | .dwg or .dxf only | "Invalid file type. Only .dwg and .dxf files are supported." |
| File Size | Max 50MB | "File too large. Maximum size is 50MB." |

---

## 4. User Flow: File Upload & Parsing

### Upload States

```
┌─────────┐     ┌───────────┐     ┌─────────┐     ┌─────────┐
│  Idle   │────▶│ Selected  │────▶│Uploading│────▶│ Success │
│         │     │           │     │         │     │         │
└─────────┘     └───────────┘     └─────────┘     └─────────┘
     │                │                │               │
     │                │                │               │
     │                ▼                ▼               │
     │          ┌─────────┐      ┌─────────┐          │
     │          │  Clear  │      │  Error  │          │
     │          │         │      │         │          │
     │          └─────────┘      └─────────┘          │
     │                │                │               │
     └────────────────┴────────────────┴───────────────┘
                        Reset to Idle
```

### File Processing Pipeline

```
DWG File
    │
    ▼
┌───────────────────┐
│ LibreDWG Convert  │  (DWG → DXF)
│   dwg2dxf tool    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   ezdxf Parser    │  (DXF → JSON)
│   Extract layers  │
└─────────┬─────────┘
          │
    ┌─────┴─────┬─────────┬──────────┐
    ▼           ▼         ▼          ▼
┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐
│ Walls │  │ Doors │  │Windows│  │ Rooms │
└───────┘  └───────┘  └───────┘  └───────┘
    │           │         │          │
    └───────────┴─────────┴──────────┘
                    │
                    ▼
            ┌───────────────┐
            │  Room Type    │
            │  Classifier   │
            │  (AI/Pattern) │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Floor Plan   │
            │    Object     │
            └───────────────┘
```

### Parsed Data Structure

```json
{
  "id": "project-uuid",
  "name": "My Floor Plan",
  "floor_plan": {
    "rooms": [
      {
        "id": "room-1",
        "name": "Living Room",
        "room_type": "living",
        "area": 25.5,
        "polygon": [[0,0], [5,0], [5,5], [0,5]],
        "centroid": [2.5, 2.5]
      }
    ],
    "walls": [
      {
        "id": "wall-1",
        "start": [0, 0],
        "end": [5, 0],
        "thickness": 0.2,
        "layer": "A-WALL"
      }
    ],
    "doors": [
      {
        "id": "door-1",
        "position": [2.5, 0],
        "width": 0.9,
        "swing": "left"
      }
    ],
    "windows": [
      {
        "id": "window-1",
        "position": [1.0, 5.0],
        "width": 1.2
      }
    ],
    "metadata": {
      "units": "meters",
      "total_area": 150.5,
      "bounds": {"min": [0,0], "max": [15,10]}
    }
  }
}
```

---

## 5. User Flow: Floor Plan Viewing

### Project Detail Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ← Back    Full Test Project    [Ready]    [Open Studio]     │
├─────────────────────────────────────────────────────────────┤
│                                           │                 │
│  [2D View] [3D View] [Details]            │  Project Info   │
│  ┌─────────────────────────────┐          │  ───────────    │
│  │                             │          │  Status: Ready  │
│  │                             │          │  File: plan.dwg │
│  │     Floor Plan Display      │          │  Created: ...   │
│  │     (SVG or Three.js)       │          │  Area: 150 m²   │
│  │                             │          │                 │
│  │                             │          │  Quick Actions  │
│  │                             │          │  ───────────    │
│  │                             │          │  [Replace File] │
│  └─────────────────────────────┘          │  [Open Studio]  │
│                                           │  [View Gallery] │
└─────────────────────────────────────────────────────────────┘
```

### Tab Views

#### 2D View
- SVG rendering of floor plan
- Color-coded elements:
  - **Black**: Walls
  - **Cyan/Blue**: Doors
  - **Green**: Windows
- Pan and zoom enabled

#### 3D View
- React Three Fiber visualization
- Extruded walls with depth
- Toggle views:
  - **3D View**: Perspective camera, orbit controls
  - **Top View**: Orthographic top-down
- Legend showing element types

#### Details Tab
- Room list with areas
- Wall/door/window counts
- Layer information
- Dimensions

### Interactions

| Element | Action | Result |
|---------|--------|--------|
| 2D Floor Plan | Pan (drag) | Move view |
| 2D Floor Plan | Zoom (scroll) | Scale view |
| 3D View | Orbit (drag) | Rotate camera |
| 3D View | Zoom (scroll) | Dolly camera |
| "3D View" toggle | Click | Perspective view |
| "Top View" toggle | Click | Top-down view |
| "Open Studio" button | Click | Navigate to render page |
| "Replace File" button | Click | Open upload modal |
| "View Gallery" button | Click | Navigate to gallery |

---

## 6. User Flow: Render Studio

### Three-Phase Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: CONFIGURE                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Left Panel  │  │ Center Panel │  │ Right Panel  │       │
│  │              │  │              │  │              │       │
│  │ Floor Plan   │  │   Room       │  │  Lighting    │       │
│  │ Mini Map     │  │ Configuration│  │  Settings    │       │
│  │              │  │              │  │              │       │
│  │ Room List    │  │  Materials   │  │ Render Queue │       │
│  │ (checkboxes) │  │  Dropdowns   │  │              │       │
│  │              │  │              │  │ [Start       │       │
│  │ 13/13        │  │ Design Style │  │  Rendering]  │       │
│  │ selected     │  │              │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Click "Start Rendering"
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 2: RENDERING                        │
│                                                              │
│                  ┌─────────────────────┐                     │
│                  │                     │                     │
│                  │   Generating...     │                     │
│                  │   ████████░░ 60%    │                     │
│                  │                     │                     │
│                  │   ✓ Living Room     │                     │
│                  │   ✓ Kitchen         │                     │
│                  │   ⟳ Bedroom        │                     │
│                  │   ○ Bathroom        │                     │
│                  │                     │                     │
│                  │   [Cancel Render]   │                     │
│                  │                     │                     │
│                  └─────────────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ All rooms complete
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 3: RESULTS                          │
│                                                              │
│  Render Complete!  12 successful • 1 failed                  │
│                                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Living  │  │ Kitchen │  │ Bedroom │  │  Bath   │        │
│  │  Room   │  │         │  │    1    │  │  room   │        │
│  │ [image] │  │ [image] │  │ [image] │  │ [image] │        │
│  │ ↓ Save  │  │ ↓ Save  │  │ ↓ Save  │  │ ↓ Save  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                              │
│  [View Gallery]                         [New Render]         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Room Selection

| Action | Result |
|--------|--------|
| Click room in mini map | Toggle room selection + set as active |
| Click room in list | Toggle selection + set as active |
| Click "All" button | Select all rooms |
| Click "None" button | Deselect all rooms |
| Click "Selected" badge | Toggle room selection only |

### Material Configuration

| Element | Options | Default |
|---------|---------|---------|
| Floor | White Oak (Light), White Oak (Medium), Walnut (Dark), Maple, Carrara Marble, Nero Marquina, Grey Slate, White Porcelain, Terracotta, Polished Concrete, Raw Concrete | White Oak (Light) |
| Walls | White (Matte), Warm Grey, Polished Concrete, Raw Concrete | White (Matte) |
| Ceiling | White (Matte), Warm Grey | White (Matte) |

### Design Styles

| Style | Description |
|-------|-------------|
| Modern | Clean lines, minimal decoration |
| Scandinavian | Light, cozy, natural materials |
| Industrial | Raw, urban, exposed elements |
| Rustic | Warm, natural, textured |
| Minimalist | Simple, essential, uncluttered |
| Traditional | Classic, elegant details |

### Lighting Settings

| Setting | Options |
|---------|---------|
| Style | Natural, Warm, Cool, Dramatic |
| Time of Day | Day, Evening, Night |

### Render Queue

- Shows all selected rooms
- Displays room name + type
- Status: Queued → Processing → Complete/Failed
- Estimated time: ~30 seconds per room

---

## 7. User Flow: Gallery & Downloads

### View Modes

#### Grid View (Default)
```
┌─────────────────────────────────────────────────────────────┐
│  [Grid] [Compare] [Timeline]     Filters ▾    [Download All]│
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ ☐  ♡   │  │ ☐  ♡   │  │ ☐  ♡   │  │ ☐  ♡   │        │
│  │ [image] │  │ [image] │  │ [image] │  │ [image] │        │
│  │ Living  │  │ Kitchen │  │ Bedroom │  │ Bath    │        │
│  │ Room    │  │         │  │         │  │         │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ ☐  ♡   │  │ ☐  ♡   │  │ ☐  ♡   │  │ ☐  ♡   │        │
│  │ [image] │  │ [image] │  │ [image] │  │ [image] │        │
│  │ Office  │  │ Dining  │  │ Entry   │  │ Laundry │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Compare View
```
┌─────────────────────────────────────────────────────────────┐
│  [Grid] [Compare] [Timeline]                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────┐  ┌───────────────────────┐       │
│  │                       │  │                       │       │
│  │         A             │  │         B             │       │
│  │                       │  │                       │       │
│  │     [Full image]      │  │     [Full image]      │       │
│  │                       │  │                       │       │
│  │   Living Room         │  │   Living Room         │       │
│  │   Modern • Day        │  │   Scandinavian • Day  │       │
│  └───────────────────────┘  └───────────────────────┘       │
│                                                              │
│  Thumbnails: [A] [B] [img] [img] [img] [img] [img]         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Timeline View
```
┌─────────────────────────────────────────────────────────────┐
│  [Grid] [Compare] [Timeline]                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Living Room                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ Latest  │  │   v2    │  │   v1    │  ───────────▶       │
│  │ [image] │  │ [image] │  │ [image] │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
│                                                              │
│  Kitchen                                                     │
│  ┌─────────┐  ┌─────────┐                                   │
│  │ Latest  │  │   v1    │  ───────────▶                    │
│  │ [image] │  │ [image] │                                   │
│  └─────────┘  └─────────┘                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Filter Options

| Filter | Options |
|--------|---------|
| Room | All rooms, or specific room name |
| Style | All styles, Modern, Scandinavian, etc. |
| Sort By | Newest first, Oldest first, By room |

### Download Options

| Option | Description |
|--------|-------------|
| Single download | Click download icon on any image |
| Batch download | Select multiple + "Download All" |
| Download format | PNG or JPG |
| Favorites only | Download only favorited images |

### Interactions

| Element | Action | Result |
|---------|--------|--------|
| Image card | Hover | Show overlay with zoom/download icons |
| Zoom icon | Click | Open lightbox modal |
| Download icon | Click | Download single image |
| Checkbox | Click | Add to selection for batch download |
| Heart icon | Click | Toggle favorite |
| "Download All" | Click | Open download modal |
| Lightbox | Click outside | Close lightbox |

---

## 8. User Flow: Material Library

### Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    Material Library                          │
│         Browse and select materials for your renders         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [All] [Wood] [Stone] [Metal] [Fabric] [Ceramic] [Concrete] │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ ████████████    │  │ ████████████    │  │ ████████    │  │
│  │ White Oak       │  │ White Oak       │  │ Walnut      │  │
│  │ (Light)         │  │ (Medium)        │  │ (Dark)      │  │
│  │                 │  │                 │  │             │  │
│  │ modern          │  │ traditional     │  │ traditional │  │
│  │ scandinavian    │  │ modern          │  │ luxury      │  │
│  │                 │  │                 │  │             │  │
│  │ Rough: 0.70     │  │ Rough: 0.65     │  │ Rough: 0.60 │  │
│  │ Metal: 0.00     │  │ Metal: 0.00     │  │ Metal: 0.00 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Material Categories

| Category | Materials |
|----------|-----------|
| Wood | White Oak (Light), White Oak (Medium), Walnut (Dark), Maple (Natural) |
| Stone | Carrara Marble, Nero Marquina Marble, Grey Slate |
| Metal | Brushed Brass, Black Steel, Brushed Nickel |
| Ceramic | White Porcelain, Terracotta |
| Concrete | Polished Concrete, Raw Concrete |
| Paint | White (Matte), Warm Grey |

### Material Properties

| Property | Description | Range |
|----------|-------------|-------|
| Roughness | Surface smoothness | 0.0 (smooth) - 1.0 (rough) |
| Metallic | Metal appearance | 0.0 (non-metal) - 1.0 (metal) |
| Color | Base color | Hex color code |
| Style Tags | Suitable design styles | Array of strings |

---

## 9. API Endpoints Reference

### Projects

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/projects/` | List all projects |
| POST | `/projects/` | Create new project |
| GET | `/projects/{id}` | Get project details |
| DELETE | `/projects/{id}` | Delete project |
| POST | `/projects/{id}/upload` | Upload DWG/DXF file |
| GET | `/projects/{id}/preview` | Get SVG preview |
| GET | `/projects/{id}/floor-plan` | Get parsed floor plan |

### Render

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/render/styles` | Get available design styles |
| GET | `/render/pipeline/status` | Check DALL-E availability |
| POST | `/render/batch` | Start batch render job |
| GET | `/render/batch/{id}` | Get job status |
| POST | `/render/batch/{id}/cancel` | Cancel running job |
| GET | `/render/batch/jobs/list` | List completed jobs |

### Materials

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/materials/library` | Get all materials |
| GET | `/materials/categories` | Get material categories |
| GET | `/materials/presets` | Get style presets |

### Chat

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/chat/` | Send chat message with context |

### Health

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | API health check |

---

## 10. Test Scenarios

### TC-001: Project Creation (Happy Path)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to dashboard (/) | Dashboard loads with project list |
| 2 | Click "New Project" button | Modal opens |
| 3 | Enter "Test Project" in name field | Name field populated |
| 4 | Enter "Test description" in description | Description field populated |
| 5 | Click "Create Project" | Project created, upload modal opens |
| 6 | Select valid DWG file | File selected, upload starts |
| 7 | Wait for upload complete | Modal closes, project appears in list |
| 8 | Verify project card shows "Ready" status | Status badge is green "Ready" |

### TC-002: Project Creation (Validation)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "New Project" button | Modal opens |
| 2 | Leave name empty, click "Create" | Button disabled or error shown |
| 3 | Enter name, select .txt file | Error: "Invalid file type" |
| 4 | Select file > 50MB | Error: "File too large" |

### TC-003: Quick Upload

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Drag DWG file to Quick Upload zone | Zone highlights |
| 2 | Drop file | Project auto-created from filename |
| 3 | Wait for processing | Project appears in list with "Ready" status |

### TC-004: Floor Plan Viewing

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click project card "View" button | Navigate to /project/[id] |
| 2 | Verify 2D view loads | SVG floor plan displayed |
| 3 | Click "3D View" tab | 3D visualization loads |
| 4 | Drag to rotate 3D view | Camera orbits around model |
| 5 | Click "Top View" button | Camera switches to top-down |
| 6 | Click "Details" tab | Room list and stats displayed |

### TC-005: Render Studio Configuration

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "Open Studio" button | Navigate to /project/[id]/render |
| 2 | Verify all rooms selected | "13/13 selected" (or actual count) |
| 3 | Click room in mini map | Room highlights, becomes active |
| 4 | Change floor material dropdown | Material updates for that room |
| 5 | Click "Apply to all rooms" | All rooms get same materials |
| 6 | Select "Scandinavian" style | Style card highlights |
| 7 | Click "Warm" lighting | Lighting option highlights |
| 8 | Click "Evening" time | Time option highlights |
| 9 | Click "None" to deselect all | All rooms deselected |
| 10 | Click specific room to select | Single room selected |

### TC-006: Batch Render Execution

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select 3 rooms | "3/13 selected" shown |
| 2 | Configure materials and style | Settings applied |
| 3 | Click "Start Rendering" | Phase changes to "rendering" |
| 4 | Observe progress | Progress bar updates, rooms complete |
| 5 | Wait for completion | Phase changes to "results" |
| 6 | Verify render images | 3 images displayed |
| 7 | Click "Save" on an image | Image downloads |

### TC-007: Gallery Viewing

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to /project/[id]/gallery | Gallery loads with renders |
| 2 | Click image zoom icon | Lightbox opens with full image |
| 3 | Click outside lightbox | Lightbox closes |
| 4 | Click "Compare" view | Compare layout shown |
| 5 | Click "A" on thumbnail | Image set as comparison A |
| 6 | Click "B" on different thumbnail | Image set as comparison B |
| 7 | Click "Timeline" view | Timeline grouped by room |
| 8 | Click heart icon on image | Image marked as favorite |

### TC-008: Batch Download

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "Download All" button | Download modal opens |
| 2 | Select "PNG" format | Format selected |
| 3 | Check "Favorites only" | Option checked |
| 4 | Click "Download ZIP" | ZIP file downloads |
| 5 | Extract ZIP | Contains selected images |

### TC-009: Material Library

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to /materials | Material library loads |
| 2 | Click "Wood" category | Only wood materials shown |
| 3 | Click "Stone" category | Only stone materials shown |
| 4 | Click "All" category | All materials shown |
| 5 | Verify material card info | Name, description, properties visible |

### TC-010: Error Handling

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Upload corrupt DWG file | Error message displayed |
| 2 | Navigate to non-existent project | Error page with "Back" button |
| 3 | Start render with no rooms selected | Button disabled |
| 4 | Cancel render mid-progress | Job cancelled, partial results shown |

---

## 11. Error States & Edge Cases

### Upload Errors

| Error | Trigger | User Feedback |
|-------|---------|---------------|
| Invalid file type | Select .pdf, .txt, etc. | "Invalid file type. Only .dwg and .dxf files are supported." |
| File too large | Select file > 50MB | "File too large. Maximum size is 50MB." |
| Upload failed | Network error | "Upload failed. Please try again." |
| Parse failed | Corrupt/unsupported DWG | "Failed to parse floor plan" + details |

### Render Errors

| Error | Trigger | User Feedback |
|-------|---------|---------------|
| No rooms selected | Click render with 0 selected | Button disabled |
| DALL-E unavailable | Azure OpenAI down | "DALL-E Unavailable" badge |
| Room render failed | AI generation error | Room shows "Failed" in results |
| Job cancelled | User cancels mid-render | Partial results displayed |

### Navigation Errors

| Error | Trigger | User Feedback |
|-------|---------|---------------|
| Project not found | Invalid project ID in URL | Error card with "Back to Projects" |
| 404 page | Invalid route | Next.js 404 page |

### Loading States

| State | Display |
|-------|---------|
| Projects loading | 3 skeleton cards |
| Project detail loading | Full skeleton layout |
| Render studio loading | 3-panel skeleton |
| Gallery loading | 8 skeleton cards |
| Materials loading | Centered spinner |
| File uploading | Spinner in dropzone |
| Batch rendering | Modal with progress bar |
| Image downloading | Overlay with progress |

---

## 12. Mobile Responsive Behavior

### Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 768px | Single column, tab navigation |
| Tablet | 768px - 1024px | Two columns where applicable |
| Desktop | > 1024px | Full three-panel layout |

### Render Studio Mobile

```
┌─────────────────────────┐
│  Render Studio          │
│  Full Test Project      │
├─────────────────────────┤
│                         │
│    [Current Panel       │
│     Content]            │
│                         │
│                         │
│                         │
├─────────────────────────┤
│ [Rooms] [Style] [Queue] │  ← Bottom tab bar
└─────────────────────────┘
```

### Touch Interactions

| Element | Desktop | Mobile |
|---------|---------|--------|
| Floor plan | Click to select | Tap to select |
| 3D view | Mouse drag to orbit | Touch drag to orbit |
| Dropdowns | Click to open | Tap to open |
| Buttons | Hover states | No hover states |

---

## Appendix: Status Badge Colors

| Status | Color | Tailwind Class |
|--------|-------|----------------|
| Ready | Green | `bg-emerald-100 text-emerald-800` |
| Processing | Yellow | `bg-amber-100 text-amber-800` |
| Error | Red | `bg-red-100 text-red-800` |
| Queued | Gray | `bg-gray-100 text-gray-800` |
| Completed | Green | `bg-emerald-100 text-emerald-800` |
| Failed | Red | `bg-red-100 text-red-800` |

---

*Document generated: January 2026*
*Version: MVP 1.0*
