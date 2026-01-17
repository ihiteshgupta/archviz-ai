'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { getPreview, getFloorPlan } from '@/lib/api';
import { Map } from 'lucide-react';
import { cleanRoomName
 } from '@/lib/utils';
import type { FloorPlan, Room } from '@/types';

interface FloorPlanMiniMapProps {
  projectId: string;
  selectedRooms?: Set<string>;
  onRoomClick?: (roomId: string) => void;
  interactive?: boolean;
}

// Simple SVG sanitizer - only allow safe SVG elements and attributes
function sanitizeSvg(svgString: string): string {
  const allowedTags = [
    'svg',
    'g',
    'path',
    'rect',
    'polygon',
    'circle',
    'ellipse',
    'line',
    'polyline',
    'text',
    'tspan',
  ];
  const allowedAttrs = [
    'viewBox',
    'xmlns',
    'id',
    'class',
    'stroke',
    'stroke-width',
    'fill',
    'fill-opacity',
    'd',
    'x',
    'y',
    'width',
    'height',
    'points',
    'cx',
    'cy',
    'r',
    'rx',
    'ry',
    'x1',
    'y1',
    'x2',
    'y2',
    'transform',
  ];

  const parser = new DOMParser();
  const doc = parser.parseFromString(svgString, 'image/svg+xml');

  const parseError = doc.querySelector('parsererror');
  if (parseError) {
    console.error('SVG parse error');
    return '';
  }

  function sanitizeElement(el: Element): boolean {
    const tagName = el.tagName.toLowerCase();

    if (!allowedTags.includes(tagName)) {
      return false;
    }

    const attrs = Array.from(el.attributes);
    for (const attr of attrs) {
      if (!allowedAttrs.includes(attr.name)) {
        el.removeAttribute(attr.name);
      }
    }

    const children = Array.from(el.children);
    for (const child of children) {
      if (!sanitizeElement(child)) {
        el.removeChild(child);
      }
    }

    return true;
  }

  const svgElement = doc.querySelector('svg');
  if (!svgElement) {
    return '';
  }

  sanitizeElement(svgElement);

  return svgElement.outerHTML;
}

// Convert polygon points to SVG path
function polygonToPath(polygon: [number, number][]): string {
  if (polygon.length === 0) return '';
  const [first, ...rest] = polygon;
  return `M ${first[0]} ${first[1]} ` + rest.map(([x, y]) => `L ${x} ${y}`).join(' ') + ' Z';
}

// Calculate bounding box for all rooms
function calculateBounds(rooms: Room[]): { minX: number; minY: number; maxX: number; maxY: number } {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

  rooms.forEach(room => {
    room.polygon.forEach(([x, y]) => {
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    });
  });

  return { minX, minY, maxX, maxY };
}

// Calculate centroid of polygon for label placement
function getCentroid(polygon: [number, number][]): [number, number] {
  let sumX = 0, sumY = 0;
  polygon.forEach(([x, y]) => {
    sumX += x;
    sumY += y;
  });
  return [sumX / polygon.length, sumY / polygon.length];
}

export default function FloorPlanMiniMap({
  projectId,
  selectedRooms,
  onRoomClick,
  interactive = true
}: FloorPlanMiniMapProps) {
  const [svg, setSvg] = useState<string | null>(null);
  const [floorPlan, setFloorPlan] = useState<FloorPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredRoom, setHoveredRoom] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [previewData, floorPlanData] = await Promise.all([
          getPreview(projectId).catch(() => null),
          getFloorPlan(projectId).catch(() => null),
        ]);

        if (previewData?.svg) {
          setSvg(previewData.svg);
        }
        if (floorPlanData) {
          setFloorPlan(floorPlanData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load preview');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [projectId]);

  const sanitizedSvg = useMemo(() => {
    if (!svg) return null;
    return sanitizeSvg(svg);
  }, [svg]);

  const handleRoomClick = useCallback((roomId: string) => {
    if (onRoomClick && interactive) {
      onRoomClick(roomId);
    }
  }, [onRoomClick, interactive]);

  // Calculate SVG viewBox from room bounds
  const viewBox = useMemo(() => {
    if (!floorPlan?.rooms || floorPlan.rooms.length === 0) return null;
    const bounds = calculateBounds(floorPlan.rooms);
    const padding = 50;
    const width = bounds.maxX - bounds.minX + padding * 2;
    const height = bounds.maxY - bounds.minY + padding * 2;
    return {
      x: bounds.minX - padding,
      y: bounds.minY - padding,
      width,
      height,
    };
  }, [floorPlan]);

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Map className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Floor Plan</h2>
        </div>
        <div className="flex items-center justify-center h-32 bg-gray-50 rounded-lg">
          <div className="w-6 h-6 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  // If we have floor plan data with rooms, render interactive SVG
  if (floorPlan?.rooms && floorPlan.rooms.length > 0 && viewBox) {
    return (
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Map className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Floor Plan</h2>
        </div>
        <div className="bg-gray-50 rounded-lg p-2">
          <svg
            viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
            className="w-full h-auto max-h-[200px]"
            style={{ transform: 'scaleY(-1)' }} // Flip Y axis for CAD coordinates
          >
            {/* Render room polygons */}
            {floorPlan.rooms.map((room) => {
              const isSelected = selectedRooms?.has(room.id);
              const isHovered = hoveredRoom === room.id;
              const centroid = getCentroid(room.polygon);

              return (
                <g key={room.id}>
                  <path
                    d={polygonToPath(room.polygon)}
                    fill={isSelected ? '#DBEAFE' : isHovered ? '#F3F4F6' : '#FFFFFF'}
                    stroke={isSelected ? '#1E40AF' : '#9CA3AF'}
                    strokeWidth={isSelected ? 2 : 1}
                    className={interactive ? 'cursor-pointer transition-colors' : ''}
                    onClick={() => handleRoomClick(room.id)}
                    onMouseEnter={() => interactive && setHoveredRoom(room.id)}
                    onMouseLeave={() => setHoveredRoom(null)}
                  />
                  {/* Room label - flip text back */}
                  <text
                    x={centroid[0]}
                    y={centroid[1]}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="12"
                    fill={isSelected ? '#1E40AF' : '#6B7280'}
                    fontWeight={isSelected ? '600' : '400'}
                    style={{ transform: `scaleY(-1)`, transformOrigin: `${centroid[0]}px ${centroid[1]}px` }}
                    className="pointer-events-none select-none"
                  >
                    {cleanRoomName(room.name).substring(0, 10)}
                  </text>
                </g>
              );
            })}

            {/* Render walls on top */}
            {floorPlan.walls.map((wall) => (
              <path
                key={wall.id}
                d={polygonToPath(wall.points)}
                fill="none"
                stroke="#374151"
                strokeWidth={wall.thickness || 2}
              />
            ))}
          </svg>
        </div>
        {interactive && (
          <p className="text-xs text-gray-500 mt-2 text-center">
            Click rooms to select
          </p>
        )}
      </div>
    );
  }

  // Fallback to static SVG preview
  if (error || !sanitizedSvg) {
    return (
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Map className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Floor Plan</h2>
        </div>
        <div className="flex items-center justify-center h-32 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-500">Preview unavailable</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <Map className="w-5 h-5 text-primary-600" />
        <h2 className="text-lg font-semibold text-gray-900">Floor Plan</h2>
      </div>
      <div
        className="bg-gray-50 rounded-lg p-2 [&>svg]:w-full [&>svg]:h-auto [&>svg]:max-h-[200px]"
        dangerouslySetInnerHTML={{ __html: sanitizedSvg }}
      />
    </div>
  );
}
