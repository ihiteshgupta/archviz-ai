'use client';

import { useRef, useEffect, useState, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Environment, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import type { FloorPlan, Wall, Door, Window as WindowType, Room } from '@/types';

interface FloorPlan3DViewerProps {
  floorPlan: FloorPlan;
}

// Wall component
function Wall3D({ wall, height = 3 }: { wall: Wall; height?: number }) {
  const geometry = useMemo(() => {
    if (wall.points.length < 2) return null;

    const shape = new THREE.Shape();
    const thickness = wall.thickness || 0.2;

    // Create wall as extruded shape along points
    const points = wall.points;
    const segments: THREE.BufferGeometry[] = [];

    for (let i = 0; i < points.length - 1; i++) {
      const start = new THREE.Vector2(points[i][0], points[i][1]);
      const end = new THREE.Vector2(points[i + 1][0], points[i + 1][1]);
      const dir = end.clone().sub(start).normalize();
      const perp = new THREE.Vector2(-dir.y, dir.x).multiplyScalar(thickness / 2);

      const boxGeom = new THREE.BoxGeometry(
        start.distanceTo(end),
        height,
        thickness
      );

      const midPoint = start.clone().add(end).multiplyScalar(0.5);
      const angle = Math.atan2(dir.y, dir.x);

      const matrix = new THREE.Matrix4()
        .makeTranslation(midPoint.x, height / 2, midPoint.y)
        .multiply(new THREE.Matrix4().makeRotationY(-angle));

      boxGeom.applyMatrix4(matrix);
      segments.push(boxGeom);
    }

    if (segments.length === 0) return null;

    // Merge all segments
    const mergedGeometry = segments.length === 1
      ? segments[0]
      : segments.reduce((acc, geom) => {
          const merged = new THREE.BufferGeometry();
          // Simple approach: just use first segment for now
          return acc;
        }, segments[0]);

    return segments[0];
  }, [wall, height]);

  if (!geometry) return null;

  return (
    <mesh geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial
        color={wall.is_exterior ? '#8B7355' : '#E8E4E0'}
        roughness={0.9}
      />
    </mesh>
  );
}

// Simple wall segment
function WallSegment({ start, end, height = 3, thickness = 0.2, isExterior = false }: {
  start: [number, number];
  end: [number, number];
  height?: number;
  thickness?: number;
  isExterior?: boolean;
}) {
  const length = Math.sqrt(
    Math.pow(end[0] - start[0], 2) + Math.pow(end[1] - start[1], 2)
  );

  const midX = (start[0] + end[0]) / 2;
  const midZ = (start[1] + end[1]) / 2;
  const angle = Math.atan2(end[1] - start[1], end[0] - start[0]);

  return (
    <mesh
      position={[midX, height / 2, midZ]}
      rotation={[0, -angle, 0]}
      castShadow
      receiveShadow
    >
      <boxGeometry args={[length, height, thickness]} />
      <meshStandardMaterial
        color={isExterior ? '#8B7355' : '#F5F5F0'}
        roughness={0.9}
      />
    </mesh>
  );
}

// Door component
function Door3D({ door }: { door: Door }) {
  const width = door.width || 0.9;
  const height = door.height || 2.1;

  return (
    <group position={[door.position[0], height / 2, door.position[1]]}>
      <mesh castShadow>
        <boxGeometry args={[width, height, 0.05]} />
        <meshStandardMaterial color="#8B4513" roughness={0.6} />
      </mesh>
      {/* Door frame */}
      <mesh position={[0, 0, -0.03]}>
        <boxGeometry args={[width + 0.1, height + 0.05, 0.02]} />
        <meshStandardMaterial color="#5C4033" roughness={0.7} />
      </mesh>
    </group>
  );
}

// Window component
function Window3D({ window: win }: { window: WindowType }) {
  const width = win.width || 1.2;
  const height = win.height || 1.2;
  const sillHeight = win.sill_height || 0.9;

  return (
    <group position={[win.position[0], sillHeight + height / 2, win.position[1]]}>
      {/* Glass */}
      <mesh>
        <boxGeometry args={[width, height, 0.02]} />
        <meshStandardMaterial
          color="#87CEEB"
          transparent
          opacity={0.4}
          roughness={0.1}
        />
      </mesh>
      {/* Frame */}
      <mesh position={[0, 0, -0.02]}>
        <boxGeometry args={[width + 0.1, height + 0.1, 0.02]} />
        <meshStandardMaterial color="#FFFFFF" roughness={0.5} />
      </mesh>
    </group>
  );
}

// Room floor component
function RoomFloor({ room }: { room: Room }) {
  const geometry = useMemo(() => {
    if (!room.polygon || room.polygon.length < 3) return null;

    const shape = new THREE.Shape();
    shape.moveTo(room.polygon[0][0], room.polygon[0][1]);

    for (let i = 1; i < room.polygon.length; i++) {
      shape.lineTo(room.polygon[i][0], room.polygon[i][1]);
    }
    shape.closePath();

    return new THREE.ShapeGeometry(shape);
  }, [room.polygon]);

  if (!geometry) return null;

  // Rotate to lie flat on XZ plane
  return (
    <mesh
      geometry={geometry}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0.01, 0]}
      receiveShadow
    >
      <meshStandardMaterial
        color={getRoomColor(room.room_type)}
        roughness={0.8}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function getRoomColor(roomType: string): string {
  const colors: Record<string, string> = {
    living: '#F5F5DC',
    bedroom: '#E6E6FA',
    kitchen: '#FAFAD2',
    bathroom: '#E0FFFF',
    dining: '#FFF8DC',
    office: '#F0F8FF',
    default: '#F5F5F5',
  };
  return colors[roomType.toLowerCase()] || colors.default;
}

// Camera controls
function CameraController() {
  const { camera } = useThree();

  useEffect(() => {
    camera.position.set(15, 15, 15);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  return null;
}

// Scene component
function Scene({ floorPlan }: { floorPlan: FloorPlan }) {
  const bounds = floorPlan.metadata?.bounds;
  const center = bounds
    ? [
        (bounds.min[0] + bounds.max[0]) / 2,
        0,
        (bounds.min[1] + bounds.max[1]) / 2,
      ]
    : [0, 0, 0];

  return (
    <group position={[-center[0], 0, -center[2]]}>
      {/* Render walls */}
      {floorPlan.walls?.map((wall) => {
        if (wall.points.length < 2) return null;

        return wall.points.slice(0, -1).map((point, i) => (
          <WallSegment
            key={`${wall.id}-${i}`}
            start={point}
            end={wall.points[i + 1]}
            height={wall.height || 3}
            thickness={wall.thickness || 0.2}
            isExterior={wall.is_exterior}
          />
        ));
      })}

      {/* Render rooms (floors) */}
      {floorPlan.rooms?.map((room) => (
        <RoomFloor key={room.id} room={room} />
      ))}

      {/* Render doors */}
      {floorPlan.doors?.map((door) => (
        <Door3D key={door.id} door={door} />
      ))}

      {/* Render windows */}
      {floorPlan.windows?.map((win) => (
        <Window3D key={win.id} window={win} />
      ))}

      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[center[0], -0.01, center[2]]} receiveShadow>
        <planeGeometry args={[100, 100]} />
        <meshStandardMaterial color="#E8E8E8" />
      </mesh>
    </group>
  );
}

export default function FloorPlan3DViewer({ floorPlan }: FloorPlan3DViewerProps) {
  const [viewMode, setViewMode] = useState<'perspective' | 'top'>('perspective');

  return (
    <div className="w-full h-[500px] bg-gray-100 rounded-lg overflow-hidden relative">
      {/* View mode toggle */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        <button
          onClick={() => setViewMode('perspective')}
          className={`px-3 py-1 rounded text-sm ${
            viewMode === 'perspective'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700'
          }`}
        >
          3D View
        </button>
        <button
          onClick={() => setViewMode('top')}
          className={`px-3 py-1 rounded text-sm ${
            viewMode === 'top'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-700'
          }`}
        >
          Top View
        </button>
      </div>

      <Canvas shadows>
        <PerspectiveCamera
          makeDefault
          position={viewMode === 'top' ? [0, 30, 0] : [15, 15, 15]}
          fov={50}
        />
        <OrbitControls
          enablePan
          enableZoom
          enableRotate={viewMode === 'perspective'}
          maxPolarAngle={viewMode === 'top' ? 0 : Math.PI / 2}
          minPolarAngle={viewMode === 'top' ? 0 : 0}
        />

        {/* Lighting */}
        <ambientLight intensity={0.5} />
        <directionalLight
          position={[10, 20, 10]}
          intensity={1}
          castShadow
          shadow-mapSize={[2048, 2048]}
        />

        {/* Grid helper */}
        <Grid
          infiniteGrid
          cellSize={1}
          sectionSize={5}
          fadeDistance={50}
          cellColor="#cccccc"
          sectionColor="#999999"
        />

        {/* Floor plan scene */}
        <Scene floorPlan={floorPlan} />
      </Canvas>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-white/90 rounded-lg p-3 text-xs">
        <div className="font-medium mb-2">Legend</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[#8B7355] rounded" />
            <span>Exterior Wall</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[#F5F5F0] rounded" />
            <span>Interior Wall</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[#8B4513] rounded" />
            <span>Door</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[#87CEEB] rounded" />
            <span>Window</span>
          </div>
        </div>
      </div>
    </div>
  );
}
