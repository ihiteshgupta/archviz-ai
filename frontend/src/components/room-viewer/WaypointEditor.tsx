'use client';

import type { Waypoint } from './RoomViewer3D';

interface WaypointEditorProps {
  waypoints: Waypoint[];
  onWaypointsChange: (waypoints: Waypoint[]) => void;
  onPreviewWalkthrough: () => void;
}

export function WaypointEditor({
  waypoints,
  onWaypointsChange,
  onPreviewWalkthrough,
}: WaypointEditorProps) {
  const removeWaypoint = (id: string) => {
    onWaypointsChange(waypoints.filter((w) => w.id !== id));
  };

  const updateDuration = (id: string, duration: number) => {
    onWaypointsChange(
      waypoints.map((w) => (w.id === id ? { ...w, duration } : w))
    );
  };

  const moveWaypoint = (id: string, direction: 'up' | 'down') => {
    const index = waypoints.findIndex((w) => w.id === id);
    if (
      (direction === 'up' && index === 0) ||
      (direction === 'down' && index === waypoints.length - 1)
    ) {
      return;
    }

    const newWaypoints = [...waypoints];
    const swapIndex = direction === 'up' ? index - 1 : index + 1;
    [newWaypoints[index], newWaypoints[swapIndex]] = [
      newWaypoints[swapIndex],
      newWaypoints[index],
    ];
    onWaypointsChange(newWaypoints);
  };

  const totalDuration = waypoints.reduce((sum, w) => sum + (w.duration || 3), 0);

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold text-lg mb-4">Walkthrough Waypoints</h3>

      {waypoints.length === 0 ? (
        <p className="text-gray-500 text-sm">
          Click on the floor in the 3D view to add waypoints
        </p>
      ) : (
        <div className="space-y-2">
          {waypoints.map((wp, index) => (
            <div
              key={wp.id}
              className="flex items-center gap-2 p-2 bg-gray-50 rounded"
            >
              <span className="w-6 h-6 flex items-center justify-center bg-blue-500 text-white rounded-full text-sm">
                {index + 1}
              </span>

              <div className="flex-1">
                <span className="text-sm text-gray-600">
                  ({wp.position[0].toFixed(1)}, {wp.position[2].toFixed(1)})
                </span>
              </div>

              <input
                type="number"
                value={wp.duration || 3}
                onChange={(e) => updateDuration(wp.id, Number(e.target.value))}
                className="w-16 px-2 py-1 border rounded text-sm"
                min={1}
                max={30}
              />
              <span className="text-xs text-gray-500">sec</span>

              <button
                onClick={() => moveWaypoint(wp.id, 'up')}
                disabled={index === 0}
                className="p-1 hover:bg-gray-200 rounded disabled:opacity-30"
              >
                ^
              </button>
              <button
                onClick={() => moveWaypoint(wp.id, 'down')}
                disabled={index === waypoints.length - 1}
                className="p-1 hover:bg-gray-200 rounded disabled:opacity-30"
              >
                v
              </button>
              <button
                onClick={() => removeWaypoint(wp.id)}
                className="p-1 hover:bg-red-100 text-red-500 rounded"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}

      {waypoints.length >= 2 && (
        <div className="mt-4 pt-4 border-t">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm text-gray-600">
              Total duration: {totalDuration}s
            </span>
            <span className="text-sm text-gray-600">
              {waypoints.length} waypoints
            </span>
          </div>

          <button
            onClick={onPreviewWalkthrough}
            className="w-full py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Preview Walkthrough
          </button>
        </div>
      )}
    </div>
  );
}
