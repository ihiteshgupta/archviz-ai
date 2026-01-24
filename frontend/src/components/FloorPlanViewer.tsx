'use client';

import { useEffect, useState, useMemo } from 'react';
import { getPreview } from '@/lib/api';

interface FloorPlanViewerProps {
  projectId: string;
}

// SVG sanitizer - allow safe SVG elements and attributes including ezdxf output
function sanitizeSvg(svgString: string): string {
  const allowedTags = ['svg', 'g', 'path', 'rect', 'polygon', 'circle', 'ellipse', 'line', 'polyline', 'text', 'tspan', 'defs', 'style', 'use', 'clipPath', 'mask', 'pattern', 'image'];
  const allowedAttrs = ['viewBox', 'xmlns', 'id', 'class', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-linecap', 'stroke-linejoin', 'stroke-dasharray', 'fill', 'fill-opacity', 'fill-rule', 'opacity', 'd', 'x', 'y', 'width', 'height', 'points', 'cx', 'cy', 'r', 'rx', 'ry', 'x1', 'y1', 'x2', 'y2', 'transform', 'clip-path', 'href', 'xlink:href', 'font-size', 'font-family', 'text-anchor', 'dominant-baseline'];

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

    // Remove disallowed attributes
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

export default function FloorPlanViewer({ projectId }: FloorPlanViewerProps) {
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

  // Sanitize SVG before rendering
  const sanitizedSvg = useMemo(() => {
    if (!svg) return null;
    return sanitizeSvg(svg);
  }, [svg]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 bg-red-50 rounded-lg">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!sanitizedSvg) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
        <p className="text-gray-500">No preview available</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 p-4">
      <div
        className="w-full h-auto [&>svg]:w-full [&>svg]:h-auto [&>svg]:max-h-[600px]"
        dangerouslySetInnerHTML={{ __html: sanitizedSvg }}
      />
    </div>
  );
}
