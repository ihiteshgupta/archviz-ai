'use client';

import { Canvas, ThreeEvent } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment } from '@react-three/drei';
import { Suspense, useState } from 'react';

export interface Waypoint {
  id: string;
  position: [number, number, number];
  lookAt: [number, number, number];
  duration?: number;
}

interface RoomViewer3DProps {
  gltfUrl?: string;
  onWaypointAdd?: (position: [number, number, number]) => void;
  waypoints?: Waypoint[];
}

interface SceneContentProps {
  gltfUrl?: string;
  onWaypointAdd?: (position: [number, number, number]) => void;
  waypoints: Waypoint[];
}

function RoomModel({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

function WaypointMarkers({ waypoints }: { waypoints: Waypoint[] }) {
  return (
    <>
      {waypoints.map((wp, i) => (
        <mesh key={wp.id} position={wp.position}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshStandardMaterial color={i === 0 ? '#22c55e' : '#3b82f6'} />
        </mesh>
      ))}
    </>
  );
}

function LoadingFallback() {
  return (
    <mesh>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#666" wireframe />
    </mesh>
  );
}

function ClickableFloor({
  onWaypointAdd,
}: {
  onWaypointAdd?: (position: [number, number, number]) => void;
}) {
  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    if (!onWaypointAdd) return;
    event.stopPropagation();
    const pos = event.point;
    onWaypointAdd([pos.x, 1.6, pos.z]);
  };

  return (
    <mesh
      name="floor"
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0, 0]}
      onClick={handleClick}
      receiveShadow
    >
      <planeGeometry args={[20, 20]} />
      <meshStandardMaterial color="#f0f0f0" transparent opacity={0.5} />
    </mesh>
  );
}

function SceneContent({ gltfUrl, onWaypointAdd, waypoints }: SceneContentProps) {
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />

      <Suspense fallback={<LoadingFallback />}>
        {gltfUrl && <RoomModel url={gltfUrl} />}
        <WaypointMarkers waypoints={waypoints} />
        <Environment preset="apartment" />
      </Suspense>

      <ClickableFloor onWaypointAdd={onWaypointAdd} />

      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        maxPolarAngle={Math.PI / 2}
      />

      <gridHelper args={[20, 20, '#444', '#222']} />
    </>
  );
}

export function RoomViewer3D({
  gltfUrl,
  onWaypointAdd,
  waypoints = [],
}: RoomViewer3DProps) {
  const [viewMode, setViewMode] = useState<'orbit' | 'firstPerson'>('orbit');

  return (
    <div className="relative w-full h-full">
      <Canvas camera={{ position: [5, 5, 5], fov: 50 }}>
        <SceneContent
          gltfUrl={gltfUrl}
          onWaypointAdd={onWaypointAdd}
          waypoints={waypoints}
        />
      </Canvas>

      <div className="absolute top-4 right-4 flex gap-2">
        <button
          onClick={() => setViewMode('orbit')}
          className={`px-3 py-1 rounded ${
            viewMode === 'orbit' ? 'bg-blue-500 text-white' : 'bg-gray-200'
          }`}
        >
          Orbit
        </button>
        <button
          onClick={() => setViewMode('firstPerson')}
          className={`px-3 py-1 rounded ${
            viewMode === 'firstPerson' ? 'bg-blue-500 text-white' : 'bg-gray-200'
          }`}
        >
          First Person
        </button>
      </div>
    </div>
  );
}
