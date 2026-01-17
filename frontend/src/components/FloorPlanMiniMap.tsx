'use client';

import { useEffect, useState, useMemo } from 'react';
import { getPreview } from '@/lib/api';
import { Map } from 'lucide-react';

interface FloorPlanMiniMapProps {
  projectId: string;
}

// Simple SVG sanitizer - only allow safe SVG elements and attributes
// This removes potentially dangerous elements like <script>, <foreignObject>, event handlers
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

  // Create a DOM parser to parse the SVG
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgString, 'image/svg+xml');

  // Check for parsing errors
  const parseError = doc.querySelector('parsererror');
  if (parseError) {
    console.error('SVG parse error');
    return '';
  }

  // Recursively sanitize elements
  function sanitizeElement(el: Element): boolean {
    const tagName = el.tagName.toLowerCase();

    // Remove disallowed tags
    if (!allowedTags.includes(tagName)) {
      return false;
    }

    // Remove disallowed attributes (including event handlers)
    const attrs = Array.from(el.attributes);
    for (const attr of attrs) {
      if (!allowedAttrs.includes(attr.name)) {
        el.removeAttribute(attr.name);
      }
    }

    // Sanitize children
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

export default function FloorPlanMiniMap({ projectId }: FloorPlanMiniMapProps) {
  const [svg, setSvg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPreview() {
      try {
        setLoading(true);
        const data = await getPreview(projectId);
        setSvg(data.svg);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load preview');
      } finally {
        setLoading(false);
      }
    }

    loadPreview();
  }, [projectId]);

  // Sanitize SVG before rendering - strips dangerous elements and attributes
  const sanitizedSvg = useMemo(() => {
    if (!svg) return null;
    return sanitizeSvg(svg);
  }, [svg]);

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
      {/* SVG is sanitized above - only safe elements/attributes allowed */}
      <div
        className="bg-gray-50 rounded-lg p-2 [&>svg]:w-full [&>svg]:h-auto [&>svg]:max-h-[200px]"
        dangerouslySetInnerHTML={{ __html: sanitizedSvg }}
      />
    </div>
  );
}
