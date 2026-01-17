import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatArea(area: number): string {
  return `${area.toFixed(2)} m²`;
}

/**
 * Clean room name by stripping DWG formatting codes
 *
 * DWG files often contain formatting codes like:
 * - \A1; - alignment codes
 * - \P - paragraph breaks (often followed by dimensions)
 * - {\H0.7x;\S1/2;} - height and stacking codes
 * - \fArial|b0|i0|c0|p34; - font specifications
 *
 * Examples:
 * - "\A1;ELECTRICAL ROOM\P8'-0\"X5'-0\"" -> "Electrical Room (8' × 5')"
 * - "\A1;LIVING ROOM" -> "Living Room"
 * - "MASTER BEDROOM\P12'-0\"X14'-0\"" -> "Master Bedroom (12' × 14')"
 */
export function cleanRoomName(rawName: string | undefined | null): string {
  if (!rawName) return 'Unnamed Room';

  let name = rawName;

  // Remove alignment codes like \A1; \A0; etc
  name = name.replace(/\\A\d+;/g, '');

  // Remove font specifications like \fArial|b0|i0|c0|p34;
  name = name.replace(/\\f[^;]+;/g, '');

  // Remove height/stacking codes like {\H0.7x;\S1/2;}
  name = name.replace(/\{[^}]*\}/g, '');

  // Extract dimensions after \P (paragraph break)
  const dimensionMatch = name.match(
    /\\P\s*(\d+)['-]?\s*-?\s*(\d*)"?\s*[xX×]\s*(\d+)['-]?\s*-?\s*(\d*)"?/
  );
  let dimensions = '';
  if (dimensionMatch) {
    const [, feet1, inches1, feet2, inches2] = dimensionMatch;
    const dim1 = inches1 ? `${feet1}'${inches1}"` : `${feet1}'`;
    const dim2 = inches2 ? `${feet2}'${inches2}"` : `${feet2}'`;
    dimensions = ` (${dim1} × ${dim2})`;
  }

  // Remove \P and everything after it (dimensions part)
  name = name.replace(/\\P.*$/, '');

  // Remove any remaining backslash codes
  name = name.replace(/\\[a-zA-Z]\d*;?/g, '');
  name = name.replace(/\\/g, '');

  // Clean up extra whitespace
  name = name.replace(/\s+/g, ' ').trim();

  // Convert to title case
  name = name
    .toLowerCase()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  // Handle empty result
  if (!name || name.length === 0) {
    return 'Unnamed Room';
  }

  return name + dimensions;
}

/**
 * Get a short room label for display in compact spaces
 */
export function getShortRoomLabel(
  rawName: string | undefined | null,
  roomType?: string,
  roomId?: string
): string {
  const cleaned = cleanRoomName(rawName);
  if (cleaned !== 'Unnamed Room') {
    // Remove dimensions for short label
    return cleaned.replace(/\s*\([^)]+\)$/, '');
  }
  if (roomType) {
    return roomType.charAt(0).toUpperCase() + roomType.slice(1).toLowerCase();
  }
  if (roomId) {
    return `Room ${roomId.slice(0, 4)}`;
  }
  return 'Unnamed Room';
}
