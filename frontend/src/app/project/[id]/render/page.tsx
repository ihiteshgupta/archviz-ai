'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Zap,
  Palette,
  Settings2,
  Image,
  CheckCircle,
  XCircle,
  Loader2,
  Home,
  RefreshCw,
  Download,
  Sun,
  Moon,
  Sunset,
  Square,
  CheckSquare,
} from 'lucide-react';
import {
  getProject,
  getRenderStyles,
  getStylePresets,
  getMaterialLibrary,
  getPipelineStatus,
  startBatchRender,
  getBatchJob,
  cancelBatchJob,
} from '@/lib/api';
import { cleanRoomName, getShortRoomLabel } from '@/lib/utils';
import FloorPlanMiniMap from '@/components/FloorPlanMiniMap';
import type {
  Project,
  RenderStyle,
  StylePreset,
  Material,
  BatchRenderJob,
  MaterialAssignment,
  RoomMaterials,
  PipelineStatus,
} from '@/types';

type RenderPhase = 'configure' | 'rendering' | 'results';

export default function RenderPage() {
  const params = useParams();
  const projectId = params.id as string;

  // Data states
  const [project, setProject] = useState<Project | null>(null);
  const [styles, setStyles] = useState<RenderStyle[]>([]);
  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);

  // UI states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<RenderPhase>('configure');

  // Render settings
  const [selectedStyle, setSelectedStyle] = useState('modern');
  const [lighting, setLighting] = useState('natural');
  const [timeOfDay, setTimeOfDay] = useState('day');
  const [additionalPrompt, setAdditionalPrompt] = useState('');

  // Room material assignments: { roomId: { floor: materialId, wall: materialId, ceiling: materialId } }
  const [roomMaterials, setRoomMaterials] = useState<Record<string, RoomMaterials>>({});

  // Room selection for rendering
  const [selectedRooms, setSelectedRooms] = useState<Set<string>>(new Set());

  // Batch job tracking
  const [currentJob, setCurrentJob] = useState<BatchRenderJob | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Load initial data
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [projectData, stylesData, presetsData, materialsData, statusData] =
          await Promise.all([
            getProject(projectId),
            getRenderStyles(),
            getStylePresets(),
            getMaterialLibrary(),
            getPipelineStatus().catch(() => null),
          ]);

        setProject(projectData);
        setStyles(stylesData.styles);
        setPresets(presetsData.presets);
        setMaterials(materialsData.materials);
        setPipelineStatus(statusData);

        // Initialize room materials with defaults and select all rooms
        if (projectData.floor_plan?.rooms) {
          const initialMaterials: Record<string, RoomMaterials> = {};
          const allRoomIds = new Set<string>();
          projectData.floor_plan.rooms.forEach((room) => {
            initialMaterials[room.id] = {
              floor: 'white_oak_light',
              wall: 'white_matte',
              ceiling: 'white_matte',
            };
            allRoomIds.add(room.id);
          });
          setRoomMaterials(initialMaterials);
          setSelectedRooms(allRoomIds);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [projectId]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // Poll for job status
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const job = await getBatchJob(jobId);
      setCurrentJob(job);

      if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        setPhase('results');
      }
    } catch (err) {
      console.error('Failed to poll job status:', err);
    }
  }, [pollingInterval]);

  const handleStartRender = async () => {
    if (!project?.floor_plan?.rooms || selectedRooms.size === 0) return;

    try {
      setError(null);
      setPhase('rendering');

      // Filter rooms to only selected ones
      const roomsToRender = project.floor_plan.rooms.filter((room) =>
        selectedRooms.has(room.id)
      );

      // Build material assignments only for selected rooms
      const materialAssignments: MaterialAssignment[] = [];
      Object.entries(roomMaterials).forEach(([roomId, mats]) => {
        if (!selectedRooms.has(roomId)) return;
        if (mats.floor) {
          materialAssignments.push({
            surface_id: `${roomId}_floor`,
            material_id: mats.floor,
            room_id: roomId,
            surface_type: 'floor',
          });
        }
        if (mats.wall) {
          materialAssignments.push({
            surface_id: `${roomId}_wall`,
            material_id: mats.wall,
            room_id: roomId,
            surface_type: 'wall',
          });
        }
        if (mats.ceiling) {
          materialAssignments.push({
            surface_id: `${roomId}_ceiling`,
            material_id: mats.ceiling,
            room_id: roomId,
            surface_type: 'ceiling',
          });
        }
      });

      // Start batch render with only selected rooms
      const job = await startBatchRender({
        floor_plan_id: project.id,
        rooms: roomsToRender.map((room) => ({
          id: room.id,
          name: cleanRoomName(room.name) !== 'Unnamed Room'
            ? cleanRoomName(room.name)
            : getShortRoomLabel(room.name, room.room_type, room.id),
          room_type: room.room_type,
          polygon: room.polygon,
        })),
        material_assignments: materialAssignments,
        style_preset: selectedStyle,
        lighting,
        time_of_day: timeOfDay,
        additional_prompt: additionalPrompt,
      });

      setCurrentJob(job);

      // Start polling
      const interval = setInterval(() => pollJobStatus(job.id), 2000);
      setPollingInterval(interval);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start render');
      setPhase('configure');
    }
  };

  const handleCancelRender = async () => {
    if (!currentJob) return;

    try {
      await cancelBatchJob(currentJob.id);
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
      setPhase('configure');
      setCurrentJob(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel render');
    }
  };

  const handleNewRender = () => {
    setPhase('configure');
    setCurrentJob(null);
  };

  const updateRoomMaterial = (roomId: string, surface: keyof RoomMaterials, materialId: string) => {
    setRoomMaterials((prev) => ({
      ...prev,
      [roomId]: {
        ...prev[roomId],
        [surface]: materialId,
      },
    }));
  };

  // Get materials by category for dropdowns
  const getMaterialsByCategory = (category: string) => {
    return materials.filter((m) => m.category.toLowerCase() === category.toLowerCase());
  };

  const floorMaterials = getMaterialsByCategory('wood').concat(
    getMaterialsByCategory('stone'),
    getMaterialsByCategory('ceramic'),
    getMaterialsByCategory('concrete')
  );
  const wallMaterials = getMaterialsByCategory('paint').concat(
    getMaterialsByCategory('concrete')
  );
  const ceilingMaterials = getMaterialsByCategory('paint');

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        </div>
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="card text-center py-12">
          <p className="text-red-600 mb-4">{error}</p>
          <a href="/" className="btn-primary">
            Back to Projects
          </a>
        </div>
      </div>
    );
  }

  if (!project?.floor_plan?.rooms?.length) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="card text-center py-12">
          <Home className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">No Rooms Found</h2>
          <p className="text-gray-500 mb-4">
            This floor plan doesn't have any detected rooms to render.
          </p>
          <a href={`/project/${project?.id}`} className="btn-primary">
            Back to Project
          </a>
        </div>
      </div>
    );
  }

  const rooms = project.floor_plan.rooms;

  // Rendering Phase
  if (phase === 'rendering' && currentJob) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="card text-center py-12">
          <Loader2 className="w-16 h-16 text-primary-600 animate-spin mx-auto mb-6" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Rendering in Progress</h2>
          <p className="text-gray-500 mb-6">
            Generating photorealistic renders for {currentJob.total_rooms} rooms...
          </p>

          {/* Progress Bar */}
          <div className="w-full max-w-md mx-auto mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>{currentJob.completed_rooms} of {currentJob.total_rooms} rooms</span>
              <span>{Math.round(currentJob.progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-primary-600 h-3 rounded-full transition-all duration-500"
                style={{ width: `${currentJob.progress}%` }}
              />
            </div>
          </div>

          {/* Completed rooms list */}
          {currentJob.results.length > 0 && (
            <div className="text-left max-w-md mx-auto mb-6">
              <p className="text-sm font-medium text-gray-700 mb-2">Completed:</p>
              <div className="space-y-1">
                {currentJob.results.map((result) => (
                  <div key={result.room_id} className="flex items-center gap-2 text-sm text-green-600">
                    <CheckCircle className="w-4 h-4" />
                    <span>{result.room_name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button onClick={handleCancelRender} className="btn-secondary">
            Cancel Render
          </button>
        </div>
      </div>
    );
  }

  // Results Phase
  if (phase === 'results' && currentJob) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Render Results</h1>
            <p className="text-gray-500">{project.name}</p>
          </div>
          <button onClick={handleNewRender} className="btn-primary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            New Render
          </button>
        </div>

        {/* Status Summary */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="card text-center">
            <div className="text-3xl font-bold text-green-600">{currentJob.successful_renders}</div>
            <div className="text-sm text-gray-500">Successful</div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-red-600">{currentJob.failed_renders}</div>
            <div className="text-sm text-gray-500">Failed</div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-gray-900">{currentJob.total_rooms}</div>
            <div className="text-sm text-gray-500">Total Rooms</div>
          </div>
        </div>

        {/* Render Results Grid */}
        {currentJob.results.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Rendered Images</h2>
              <span className="text-sm text-gray-500">
                {currentJob.results.length} render{currentJob.results.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {currentJob.results.map((result) => (
                <div
                  key={result.room_id}
                  className="card overflow-hidden group hover:shadow-lg transition-shadow"
                >
                  <div className="aspect-square bg-gray-100 relative overflow-hidden">
                    <img
                      src={result.image_url}
                      alt={result.room_name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = '/placeholder-render.png';
                      }}
                    />
                    {/* Success badge */}
                    <div className="absolute top-2 right-2 bg-green-500 text-white p-1 rounded-full">
                      <CheckCircle className="w-4 h-4" />
                    </div>
                    {/* Quick view overlay */}
                    <a
                      href={result.image_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center"
                    >
                      <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity text-sm font-medium">
                        Click to view full size
                      </span>
                    </a>
                  </div>
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-gray-900">{result.room_name}</h3>
                    </div>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                      {result.revised_prompt}
                    </p>
                    <div className="flex gap-2 mt-3">
                      <a
                        href={result.image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary text-sm flex-1 flex items-center justify-center gap-1"
                      >
                        <Image className="w-4 h-4" />
                        View
                      </a>
                      <a
                        href={result.image_url}
                        download={`${result.room_name}.png`}
                        className="btn-secondary text-sm flex-1 flex items-center justify-center gap-1"
                      >
                        <Download className="w-4 h-4" />
                        Download
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Errors */}
        {currentJob.errors.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Failed Renders</h2>
            <div className="space-y-2">
              {currentJob.errors.map((error) => (
                <div
                  key={error.room_id}
                  className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg"
                >
                  <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-red-800">{error.room_name}</div>
                    <div className="text-sm text-red-600">{error.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-center">
          <a href={`/project/${project.id}`} className="btn-secondary">
            Back to Project
          </a>
        </div>
      </div>
    );
  }

  // Configuration Phase (default)
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <a
          href={`/project/${project.id}`}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </a>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">Create Render</h1>
          <p className="text-gray-500">{project.name}</p>
        </div>
        {pipelineStatus && (
          <div className={`px-3 py-1 rounded-full text-sm ${
            pipelineStatus.available
              ? 'bg-green-100 text-green-700'
              : 'bg-red-100 text-red-700'
          }`}>
            {pipelineStatus.available ? 'DALL-E Ready' : 'DALL-E Unavailable'}
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Room Material Assignment */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Home className="w-5 h-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-gray-900">Room Materials</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Assign materials to each room. These will be used to generate photorealistic renders.
            </p>

            {/* Room Selection Controls */}
            <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700">
                  {selectedRooms.size} of {rooms.length} rooms selected
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedRooms(new Set(rooms.map((r) => r.id)))}
                  className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                >
                  Select All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={() => setSelectedRooms(new Set())}
                  className="text-sm text-gray-500 hover:text-gray-700 font-medium"
                >
                  Deselect All
                </button>
              </div>
            </div>

            {/* Apply to All Rooms */}
            <div className="p-4 bg-primary-50 border border-primary-200 rounded-lg mb-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-primary-800">Apply to All Rooms</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-primary-700 mb-1">
                    Floor
                  </label>
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        setRoomMaterials((prev) => {
                          const updated = { ...prev };
                          rooms.forEach((room) => {
                            updated[room.id] = { ...updated[room.id], floor: e.target.value };
                          });
                          return updated;
                        });
                      }
                    }}
                    className="w-full px-2 py-1.5 text-sm border border-primary-300 rounded focus:ring-1 focus:ring-primary-500 bg-white"
                    defaultValue=""
                  >
                    <option value="" disabled>Select...</option>
                    {floorMaterials.map((mat) => (
                      <option key={mat.id} value={mat.id}>
                        {mat.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-primary-700 mb-1">
                    Walls
                  </label>
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        setRoomMaterials((prev) => {
                          const updated = { ...prev };
                          rooms.forEach((room) => {
                            updated[room.id] = { ...updated[room.id], wall: e.target.value };
                          });
                          return updated;
                        });
                      }
                    }}
                    className="w-full px-2 py-1.5 text-sm border border-primary-300 rounded focus:ring-1 focus:ring-primary-500 bg-white"
                    defaultValue=""
                  >
                    <option value="" disabled>Select...</option>
                    {wallMaterials.map((mat) => (
                      <option key={mat.id} value={mat.id}>
                        {mat.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-primary-700 mb-1">
                    Ceiling
                  </label>
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        setRoomMaterials((prev) => {
                          const updated = { ...prev };
                          rooms.forEach((room) => {
                            updated[room.id] = { ...updated[room.id], ceiling: e.target.value };
                          });
                          return updated;
                        });
                      }
                    }}
                    className="w-full px-2 py-1.5 text-sm border border-primary-300 rounded focus:ring-1 focus:ring-primary-500 bg-white"
                    defaultValue=""
                  >
                    <option value="" disabled>Select...</option>
                    {ceilingMaterials.map((mat) => (
                      <option key={mat.id} value={mat.id}>
                        {mat.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {rooms.map((room) => {
                const isSelected = selectedRooms.has(room.id);
                return (
                <div
                  key={room.id}
                  className={`p-4 rounded-lg border-2 transition-colors ${
                    isSelected
                      ? 'bg-gray-50 border-gray-200'
                      : 'bg-gray-50/50 border-gray-100 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => {
                          setSelectedRooms((prev) => {
                            const next = new Set(prev);
                            if (next.has(room.id)) {
                              next.delete(room.id);
                            } else {
                              next.add(room.id);
                            }
                            return next;
                          });
                        }}
                        className="text-primary-600 hover:text-primary-700"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-5 h-5" />
                        ) : (
                          <Square className="w-5 h-5" />
                        )}
                      </button>
                      <div>
                        <div className="font-medium text-gray-900">
                          {cleanRoomName(room.name) !== 'Unnamed Room'
                            ? cleanRoomName(room.name)
                            : getShortRoomLabel(room.name, room.room_type, room.id)}
                        </div>
                        <div className="text-sm text-gray-500">
                          {room.area?.toFixed(1)} m² • {room.room_type}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    {/* Floor Material */}
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Floor
                      </label>
                      <select
                        value={roomMaterials[room.id]?.floor || ''}
                        onChange={(e) => updateRoomMaterial(room.id, 'floor', e.target.value)}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-primary-500"
                      >
                        {floorMaterials.map((mat) => (
                          <option key={mat.id} value={mat.id}>
                            {mat.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Wall Material */}
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Walls
                      </label>
                      <select
                        value={roomMaterials[room.id]?.wall || ''}
                        onChange={(e) => updateRoomMaterial(room.id, 'wall', e.target.value)}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-primary-500"
                      >
                        {wallMaterials.map((mat) => (
                          <option key={mat.id} value={mat.id}>
                            {mat.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Ceiling Material */}
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Ceiling
                      </label>
                      <select
                        value={roomMaterials[room.id]?.ceiling || ''}
                        onChange={(e) => updateRoomMaterial(room.id, 'ceiling', e.target.value)}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-primary-500"
                      >
                        {ceilingMaterials.map((mat) => (
                          <option key={mat.id} value={mat.id}>
                            {mat.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              );
              })}
            </div>
          </div>

          {/* Style Selection */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Palette className="w-5 h-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-gray-900">Design Style</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {['modern', 'rustic', 'industrial', 'scandinavian', 'traditional', 'minimalist'].map(
                (style) => (
                  <button
                    key={style}
                    onClick={() => setSelectedStyle(style)}
                    className={`p-3 rounded-lg border-2 text-left transition-colors ${
                      selectedStyle === style
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium text-gray-900 capitalize">{style}</div>
                  </button>
                )
              )}
            </div>
          </div>
        </div>

        {/* Settings Sidebar */}
        <div className="space-y-6">
          {/* Floor Plan Preview */}
          <FloorPlanMiniMap projectId={projectId} />

          {/* Lighting Settings */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 className="w-5 h-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-gray-900">Lighting</h2>
            </div>

            <div className="space-y-4">
              {/* Lighting Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Lighting Style
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {['natural', 'warm', 'cool', 'dramatic'].map((light) => (
                    <button
                      key={light}
                      onClick={() => setLighting(light)}
                      className={`p-2 rounded border text-sm capitalize ${
                        lighting === light
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {light}
                    </button>
                  ))}
                </div>
              </div>

              {/* Time of Day */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time of Day
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={() => setTimeOfDay('day')}
                    className={`p-2 rounded border text-sm flex flex-col items-center gap-1 ${
                      timeOfDay === 'day'
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Sun className="w-4 h-4" />
                    Day
                  </button>
                  <button
                    onClick={() => setTimeOfDay('evening')}
                    className={`p-2 rounded border text-sm flex flex-col items-center gap-1 ${
                      timeOfDay === 'evening'
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Sunset className="w-4 h-4" />
                    Evening
                  </button>
                  <button
                    onClick={() => setTimeOfDay('night')}
                    className={`p-2 rounded border text-sm flex flex-col items-center gap-1 ${
                      timeOfDay === 'night'
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Moon className="w-4 h-4" />
                    Night
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Additional Prompt */}
          <div className="card">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Details (Optional)
            </label>
            <textarea
              value={additionalPrompt}
              onChange={(e) => setAdditionalPrompt(e.target.value)}
              placeholder="Add furniture, plants, specific decor..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm"
              rows={3}
            />
          </div>

          {/* Start Render Button */}
          <div className="card">
            <button
              onClick={handleStartRender}
              disabled={!pipelineStatus?.available || selectedRooms.size === 0}
              className="w-full btn-primary flex items-center justify-center gap-2 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Zap className="w-5 h-5" />
              Render {selectedRooms.size} Room{selectedRooms.size !== 1 ? 's' : ''}
            </button>
            {!pipelineStatus?.available && (
              <p className="text-xs text-red-500 text-center mt-2">
                DALL-E API not configured. Check Azure OpenAI settings.
              </p>
            )}
            {selectedRooms.size === 0 && (
              <p className="text-xs text-amber-600 text-center mt-2">
                Select at least one room to render
              </p>
            )}
            {selectedRooms.size > 0 && pipelineStatus?.available && (
              <p className="text-xs text-gray-500 text-center mt-2">
                ~30 seconds per room
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
