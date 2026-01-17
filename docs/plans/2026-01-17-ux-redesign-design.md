# ArchViz AI - UX Redesign Design Document

**Date:** 2026-01-17
**Status:** Approved for Implementation

## Overview

A complete UX redesign to position ArchViz AI as the market leader for solo architects. Built around the promise: **"Upload your DWG, get stunning renders in 2 minutes."**

### Target Persona
- **Solo Architect** (1-3 person firm)
- Time-constrained, wearing many hats
- Needs fast client presentations
- Price-sensitive ($29/mo sweet spot)
- Values simplicity over features

### Jobs-to-be-Done
1. **Client Presentation** - Quick renders for tomorrow's meeting
2. **Design Exploration** - Try different styles/materials
3. **Marketing Assets** - Portfolio images for website
4. **Client Revisions** - Change materials, re-render specific rooms

### Visual Direction
- **Warm Architectural** - Earth tones, blueprint accents
- Makes architects feel "this was built for me"

---

## Design Philosophy

### Core Principle: "2-Minute Magic"
Every design decision supports the promise of upload-to-render in under 2 minutes.

### Three-Click Principle
Any task should complete in 3 clicks or less:
- Upload → Auto-detect rooms → Render (3 clicks for first render)
- Change material → Re-render room (2 clicks for revision)

---

## Information Architecture

```
Home (/)
├── Projects List (cards with preview thumbnails)
├── Quick Upload (drag-drop zone always visible)

Project (/project/[id])
├── Overview Tab (floor plan + stats)
├── Render Studio Tab ← Main workspace
├── Gallery Tab ← All renders organized

Render Studio (/project/[id]/studio)
├── Left Panel: Interactive Floor Plan (click rooms)
├── Center Panel: Room Configuration
├── Right Panel: Live Preview + Render Queue
```

---

## Color Palette

### Foundations
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-base` | #FAFAF8 | Page background (warm white) |
| `--bg-surface` | #FFFFFF | Cards, panels |
| `--border-default` | #E8E4DE | Borders (warm gray) |

### Blueprint Blues (Primary)
| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | #1E40AF | Buttons, links |
| `--primary-hover` | #1E3A8A | Hover states |
| `--primary-light` | #DBEAFE | Selection highlights |

### Warm Accents
| Token | Value | Usage |
|-------|-------|-------|
| `--accent-oak` | #B8860B | Success, rendered rooms |
| `--accent-oak-light` | #FEF3C7 | Subtle highlights |
| `--accent-terracotta` | #C2410C | Errors, warnings |

### Text Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | #1F2937 | Headings, body |
| `--text-secondary` | #6B7280 | Descriptions |
| `--text-muted` | #9CA3AF | Captions, hints |

---

## Typography

| Element | Font | Size/Weight |
|---------|------|-------------|
| H1 | Inter | 28px / 700 |
| H2 | Inter | 20px / 600 |
| H3 | Inter | 16px / 600 |
| Body | Inter | 14px / 400 |
| Caption | Inter | 12px / 400 |
| Dimensions | JetBrains Mono | 12px / 400 |
| Room Labels | Inter | 11px / 500 UPPERCASE |

---

## Component Specifications

### Cards
```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(139, 115, 85, 0.08);
}
.card:hover {
  border-color: #D4CFC7;
  box-shadow: 0 4px 12px rgba(139, 115, 85, 0.12);
}
```

### Buttons
```css
.btn-primary {
  background: linear-gradient(180deg, #1E40AF 0%, #1E3A8A 100%);
  color: white;
  border-radius: 8px;
  font-weight: 500;
  padding: 10px 20px;
}
.btn-secondary {
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  border-radius: 8px;
}
```

### Material Swatches
- Visual grid of swatches (not dropdowns)
- 48x48px with texture preview
- Checkmark overlay for selected
- "+N more" link for overflow

---

## Screen Designs

### 1. Home Page (Logged In)

**Header:**
- Greeting: "Good morning, {name}"
- Stats: "3 projects • 47 renders this month"
- CTA: [+ New Project] button

**Quick Upload Zone:**
- Always visible drag-drop area
- Text: "Drop a DWG to create a new project instantly"

**Project Cards Grid:**
- Thumbnail: Best render or floor plan preview
- Title, room count, render count
- "Updated X ago" timestamp
- Actions: [Studio] [Gallery]

**Empty State:**
- Large drop zone
- "Your workspace is ready"
- [Load Demo Project] for first-timers

### 2. Render Studio (Three-Panel Layout)

**Left Panel - Interactive Floor Plan:**
- SVG floor plan with clickable rooms
- Click to select, Shift+click for multi-select
- Color coding:
  - Gray fill = not configured
  - Blue outline = selected
  - Green fill = rendered
  - Orange fill = in queue
- Controls: [Select All] [Clear]

**Center Panel - Room Configurator:**
- Room header: Name, dimensions, area
- Style presets: Visual buttons (Modern, Scandinavian, etc.)
- Live preview: Last render or placeholder
- Material pickers: Visual swatches for Floor/Walls/Ceiling
- Quick action: "Apply to similar rooms"

**Right Panel - Render Queue:**
- Persistent visibility
- Progress bars per room
- Completed items with checkmarks
- Global settings: Style, Lighting, Time of Day
- Actions: [Render All Rooms] [Download ZIP]

### 3. Gallery

**Layout:**
- Filter bar: Room, Style, Date
- View toggles: Grid / Compare / Timeline
- Masonry grid of render cards

**Render Card:**
- Image thumbnail
- Room name + style
- Quick actions: Favorite, Download, Edit, Delete

**Compare Mode:**
- Side-by-side view
- Slider overlay option
- [Download Both] [Pick A] [Pick B]

**Timeline View:**
- Horizontal scroll per room
- Version history with restore option

**Batch Download:**
- Format: PNG / JPG / Both
- Resolution: Original / 4K Upscaled
- Include: Favorites only / All
- Custom naming pattern

**Share Modal:**
- Select rooms to include
- Options: Allow downloads, Show pricing, Expiry
- Generate shareable link

---

## User Flows

### Flow 1: First Upload → First Render
1. Drop DWG on home page (5s)
2. Processing animation with progress (15s)
3. Smart defaults applied based on room types
4. [Looks good, Render All] or [Let me adjust]
5. Batch render with queue visibility

### Flow 2: Design Exploration
1. In Studio, select room
2. Toggle "Comparison Mode"
3. Set Style A and Style B
4. Render both
5. Side-by-side comparison
6. [Pick A] or [Pick B]

### Flow 3: Quick Revision
1. In Gallery, click any render
2. Quick Edit panel appears
3. Change material (visual swatches)
4. [Re-render This Room]
5. New version appears, old preserved in timeline

### Flow 4: Batch Operations
1. In Studio, Shift+click multiple rooms
2. "4 rooms selected" banner
3. Apply style/materials to all
4. [Apply & Render All]

---

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (1280px+) | Three-panel studio |
| Tablet (768-1279px) | Two-panel + bottom bar |
| Mobile (<768px) | Tab navigation, stacked views |

### Mobile Specifics
- Floor plan: Tap to select, pinch to zoom
- Bottom tab bar: Rooms / Style / Queue
- Room edit: Bottom sheet modal
- Gallery: 2-column grid, tap for fullscreen

### Touch Interactions
| Gesture | Action |
|---------|--------|
| Tap room | Select/deselect |
| Long press | Quick preview popup |
| Pinch | Zoom floor plan or render |
| Swipe | Navigate gallery |
| Swipe down | Dismiss modal |

---

## Loading & Error States

### Loading States
- **File upload**: Progress bar with percentage
- **DWG parsing**: Animated blueprint + checklist
- **Render progress**: Percentage in preview area
- **Page load**: Skeleton screens with shimmer

### Error States
- **Upload failed**: Clear reason + troubleshooting steps
- **No rooms found**: Preview of what was found + manual edit option
- **Render failed**: Retry button + alternative suggestions
- **Connection lost**: Reassurance that server continues + background option

### Success States
- **Single render**: Subtle checkmark, preview update
- **Batch complete**: Celebration moment with confetti, stats summary

### Toast Notifications
- Position: Bottom-right
- Auto-dismiss: 4 seconds
- Types: Success (green), Info (blue), Warning (amber), Error (red)

---

## Implementation Plan

### Phase 1: Design System & Core Components
1. Create CSS variables for colors
2. Update Tailwind config with warm architectural theme
3. Build base components: Card, Button, MaterialSwatch
4. Create skeleton loading components

### Phase 2: Home Page Redesign
1. New hero section with quick upload
2. Project cards with thumbnails
3. Empty state design
4. Stats dashboard

### Phase 3: Render Studio
1. Three-panel layout structure
2. Interactive floor plan component
3. Room configurator with material swatches
4. Render queue sidebar

### Phase 4: Gallery
1. Grid view with filters
2. Compare mode
3. Timeline view
4. Share functionality

### Phase 5: Mobile & Polish
1. Responsive layouts
2. Touch interactions
3. Loading states
4. Error handling
5. PWA support

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to first render | ~5 min | <2 min |
| Clicks to render | 8+ | 3 |
| Mobile usability | Poor | Excellent |
| User retention (7-day) | TBD | 40%+ |

---

## Appendix: Competitive Differentiation

| Feature | ArchViz AI | Competitors |
|---------|------------|-------------|
| Native DWG support | ✅ Direct upload | ❌ Image export required |
| Room intelligence | ✅ Auto-detect types | ❌ Manual labeling |
| Bulk workflows | ✅ Apply to all rooms | ❌ One-by-one |
| Batch rendering | ✅ Parallel processing | ❌ Sequential |
| Visual material picker | ✅ Swatches | ❌ Dropdowns |
