'use client';

import { useState, useEffect } from 'react';
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
  Play,
  X,
  Layers,
  Clock,
} from 'lucide-react';
import {
  useProject,
  useRenderStyles,
  useStylePresets,
  useMaterials,
  usePipelineStatus,
  useBatchJob,
  useStartBatchRender,
  useCancelBatchJob,
} from '@/lib/hooks';
import { cleanRoomName, getShortRoomLabel, formatArea } from '@/lib/utils';
import {
  Button,
  Card,
  Badge,
  ProgressBar,
  Modal,
  ModalFooter,
  Skeleton,
  SkeletonRenderQueue,
} from '@/components';
import FloorPlanMiniMap from '@/components/FloorPlanMiniMap';
import type { MaterialAssignment, RoomMaterials, Material } from '@/types';

type RenderPhase = 'configure' | 'rendering' | 'results';

export default function RenderPage() {
  const params = useParams();
  const projectId = params.id as string;

  // React Query hooks
  const { data: project, isLoading: projectLoading, error: projectError } = useProject(projectId);
  const { data: stylesData } = useRenderStyles();
  const { data: presetsData } = useStylePresets();
  const { data: materialsData } = useMaterials();
  const { data: pipelineStatus } = usePipelineStatus();

  // UI states
  const [phase, setPhase] = useState<RenderPhase>('configure');
  const [error, setError] = useState<string | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);

  // Render settings
  const [selectedStyle, setSelectedStyle] = useState('modern');
  const [lighting, setLighting] = useState('natural');
  const [timeOfDay, setTimeOfDay] = useState('day');
  const [additionalPrompt, setAdditionalPrompt] = useState('');

  // Room material assignments
  const [roomMaterials, setRoomMaterials] = useState<Record<string, RoomMaterials>>({});

  // Room selection for rendering
  const [selectedRooms, setSelectedRooms] = useState<Set<string>>(new Set());

  // Batch job tracking
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const isJobRunning = phase === 'rendering';
  const { data: currentJob } = useBatchJob(currentJobId, { polling: isJobRunning });

  // Mutations
  const startBatchRenderMutation = useStartBatchRender();
  const cancelBatchJobMutation = useCancelBatchJob();

  // Extract data
  const styles = stylesData?.styles ?? [];
  const presets = presetsData?.presets ?? [];
  const materials = materialsData?.materials ?? [];
  const loading = projectLoading;

  // Initialize room materials when project loads
  useEffect(() => {
    if (project?.floor_plan?.rooms && Object.keys(roomMaterials).length === 0) {
      const initialMaterials: Record<string, RoomMaterials> = {};
      const allRoomIds = new Set<string>();
      project.floor_plan.rooms.forEach((room) => {
        initialMaterials[room.id] = {
          floor: 'white_oak_light',
          wall: 'white_matte',
          ceiling: 'white_matte',
        };
        allRoomIds.add(room.id);
      });
      setRoomMaterials(initialMaterials);
      setSelectedRooms(allRoomIds);
      // Select first room by default
      if (project.floor_plan.rooms.length > 0) {
        setSelectedRoomId(project.floor_plan.rooms[0].id);
      }
    }
  }, [project, roomMaterials]);

  // Transition to results when job completes
  useEffect(() => {
    if (currentJob && ['completed', 'failed', 'cancelled'].includes(currentJob.status)) {
      setPhase('results');
    }
  }, [currentJob]);

  const handleStartRender = async () => {
    if (!project?.floor_plan?.rooms || selectedRooms.size === 0) return;

    try {
      setError(null);
      setPhase('rendering');

      const roomsToRender = project.floor_plan.rooms.filter((room) =>
        selectedRooms.has(room.id)
      );

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

      const job = await startBatchRenderMutation.mutateAsync({
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

      setCurrentJobId(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start render');
      setPhase('configure');
    }
  };

  const handleCancelRender = async () => {
    if (!currentJobId) return;
    try {
      await cancelBatchJobMutation.mutateAsync(currentJobId);
      setPhase('configure');
      setCurrentJobId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel render');
    }
  };

  const handleNewRender = () => {
    setPhase('configure');
    setCurrentJobId(null);
  };

  const updateRoomMaterial = (roomId: string, surface: keyof RoomMaterials, materialId: string) => {
    setRoomMaterials((prev) => ({
      ...prev,
      [roomId]: { ...prev[roomId], [surface]: materialId },
    }));
  };

  const applyMaterialToAllRooms = (surface: keyof RoomMaterials, materialId: string) => {
    if (!project?.floor_plan?.rooms) return;
    setRoomMaterials((prev) => {
      const updated = { ...prev };
      project.floor_plan!.rooms.forEach((room) => {
        updated[room.id] = { ...updated[room.id], [surface]: materialId };
      });
      return updated;
    });
  };

  const toggleRoomSelection = (roomId: string) => {
    setSelectedRooms((prev) => {
      const next = new Set(prev);
      if (next.has(roomId)) {
        next.delete(roomId);
      } else {
        next.add(roomId);
      }
      return next;
    });
  };

  // Get materials by category
  const getMaterialsByCategory = (category: string) =>
    materials.filter((m) => m.category.toLowerCase() === category.toLowerCase());

  const floorMaterials = [
    ...getMaterialsByCategory('wood'),
    ...getMaterialsByCategory('stone'),
    ...getMaterialsByCategory('ceramic'),
    ...getMaterialsByCategory('concrete'),
  ];
  const wallMaterials = [...getMaterialsByCategory('paint'), ...getMaterialsByCategory('concrete')];
  const ceilingMaterials = getMaterialsByCategory('paint');

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="h-screen flex">
          <div className="w-80 border-r border-border p-4 space-y-4">
            <Skeleton variant="rectangular" height={200} />
            <Skeleton variant="text" width="60%" />
            <SkeletonRenderQueue items={4} />
          </div>
          <div className="flex-1 p-8">
            <Skeleton variant="rectangular" className="aspect-video" />
          </div>
          <div className="w-80 border-l border-border p-4">
            <Skeleton variant="rectangular" height={300} />
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if ((error || projectError) && !project) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <Card className="text-center py-12 max-w-md">
          <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">
            {error || (projectError instanceof Error ? projectError.message : 'Failed to load')}
          </p>
          <Button variant="primary" onClick={() => (window.location.href = '/')}>
            Back to Projects
          </Button>
        </Card>
      </div>
    );
  }

  // No rooms state
  if (!project?.floor_plan?.rooms?.length) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <Card className="text-center py-12 max-w-md">
          <Home className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">No Rooms Found</h2>
          <p className="text-gray-500 mb-4">
            This floor plan doesn't have any detected rooms to render.
          </p>
          <Button
            variant="primary"
            onClick={() => (window.location.href = `/project/${project?.id}`)}
          >
            Back to Project
          </Button>
        </Card>
      </div>
    );
  }

  const rooms = project.floor_plan.rooms;
  const selectedRoom = rooms.find((r) => r.id === selectedRoomId);

  // Style options
  const styleOptions = [
    { id: 'modern', name: 'Modern', desc: 'Clean lines, minimal' },
    { id: 'scandinavian', name: 'Scandinavian', desc: 'Light, cozy, natural' },
    { id: 'industrial', name: 'Industrial', desc: 'Raw, urban, exposed' },
    { id: 'rustic', name: 'Rustic', desc: 'Warm, natural, textured' },
    { id: 'minimalist', name: 'Minimalist', desc: 'Simple, essential' },
    { id: 'traditional', name: 'Traditional', desc: 'Classic, elegant' },
  ];

  // Rendering Phase
  if (phase === 'rendering' && currentJob) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <Card className="text-center py-12 max-w-lg w-full mx-4">
          <div className="w-20 h-20 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-6">
            <Loader2 className="w-10 h-10 text-primary-600 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Rendering in Progress</h2>
          <p className="text-gray-500 mb-6">
            Generating renders for {currentJob.total_rooms} rooms...
          </p>

          <ProgressBar
            value={currentJob.progress}
            variant="gradient"
            size="lg"
            showLabel
            className="mb-6"
          />

          <div className="text-sm text-gray-600 mb-6">
            {currentJob.completed_rooms} of {currentJob.total_rooms} completed
          </div>

          {currentJob.results.length > 0 && (
            <div className="text-left mb-6 max-h-40 overflow-y-auto">
              {currentJob.results.map((result) => (
                <div
                  key={result.room_id}
                  className="flex items-center gap-2 text-sm text-emerald-600 py-1"
                >
                  <CheckCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{result.room_name}</span>
                </div>
              ))}
            </div>
          )}

          <Button variant="secondary" onClick={handleCancelRender}>
            Cancel Render
          </Button>
        </Card>
      </div>
    );
  }

  // Results Phase
  if (phase === 'results' && currentJob) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Render Results</h1>
              <p className="text-gray-500">{project.name}</p>
            </div>
            <Button
              variant="primary"
              icon={<RefreshCw className="w-4 h-4" />}
              onClick={handleNewRender}
            >
              New Render
            </Button>
          </div>

          {/* Status Summary */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            <Card variant="static" className="text-center">
              <div className="text-3xl font-bold text-emerald-600">
                {currentJob.successful_renders}
              </div>
              <div className="text-sm text-gray-500">Successful</div>
            </Card>
            <Card variant="static" className="text-center">
              <div className="text-3xl font-bold text-red-600">{currentJob.failed_renders}</div>
              <div className="text-sm text-gray-500">Failed</div>
            </Card>
            <Card variant="static" className="text-center">
              <div className="text-3xl font-bold text-gray-900">{currentJob.total_rooms}</div>
              <div className="text-sm text-gray-500">Total</div>
            </Card>
          </div>

          {/* Render Results Grid */}
          {currentJob.results.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Rendered Images</h2>
                <Badge variant="success">{currentJob.results.length} renders</Badge>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {currentJob.results.map((result) => (
                  <Card
                    key={result.room_id}
                    variant="interactive"
                    padding="none"
                    className="overflow-hidden group"
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
                      <div className="absolute top-2 right-2">
                        <Badge variant="success">
                          <CheckCircle className="w-3 h-3" />
                        </Badge>
                      </div>
                      <a
                        href={result.image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center"
                      >
                        <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity text-sm font-medium">
                          View Full Size
                        </span>
                      </a>
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-gray-900">{result.room_name}</h3>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {result.revised_prompt}
                      </p>
                      <div className="flex gap-2 mt-3">
                        <a
                          href={result.image_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1"
                        >
                          <Button variant="secondary" size="sm" className="w-full">
                            <Image className="w-4 h-4" />
                            View
                          </Button>
                        </a>
                        <a
                          href={result.image_url}
                          download={`${result.room_name}.png`}
                          className="flex-1"
                        >
                          <Button variant="secondary" size="sm" className="w-full">
                            <Download className="w-4 h-4" />
                            Save
                          </Button>
                        </a>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Errors */}
          {currentJob.errors.length > 0 && (
            <div className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Failed Renders</h2>
              <div className="space-y-2">
                {currentJob.errors.map((err) => (
                  <div
                    key={err.room_id}
                    className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                    <div>
                      <div className="font-medium text-red-800">{err.room_name}</div>
                      <div className="text-sm text-red-600">{err.message}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-center">
            <Button
              variant="secondary"
              onClick={() => (window.location.href = `/project/${project.id}`)}
            >
              Back to Project
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Configuration Phase - Three Panel Layout
  return (
    <div className="min-h-screen bg-surface-base">
      {/* Top Header */}
      <div className="bg-white border-b border-border px-4 py-3">
        <div className="max-w-[1800px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <a
              href={`/project/${project.id}`}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </a>
            <div>
              <h1 className="font-semibold text-gray-900">Render Studio</h1>
              <p className="text-sm text-gray-500">{project.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {pipelineStatus && (
              <Badge variant={pipelineStatus.available ? 'success' : 'error'}>
                {pipelineStatus.available ? 'DALL-E Ready' : 'DALL-E Unavailable'}
              </Badge>
            )}
            <Button
              variant="primary"
              icon={<Zap className="w-4 h-4" />}
              onClick={handleStartRender}
              disabled={!pipelineStatus?.available || selectedRooms.size === 0}
            >
              Render {selectedRooms.size} Room{selectedRooms.size !== 1 ? 's' : ''}
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3">
          <div className="max-w-[1800px] mx-auto flex items-center justify-between">
            <p className="text-red-700">{error}</p>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Three Panel Layout */}
      <div className="flex h-[calc(100vh-65px)]">
        {/* Left Panel - Floor Plan & Room List */}
        <div className="w-80 border-r border-border flex flex-col bg-white">
          {/* Floor Plan Preview */}
          <div className="p-4 border-b border-border">
            <FloorPlanMiniMap projectId={projectId} />
          </div>

          {/* Room List */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-3 border-b border-border flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                {selectedRooms.size}/{rooms.length} selected
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedRooms(new Set(rooms.map((r) => r.id)))}
                  className="text-xs text-primary-600 hover:text-primary-700"
                >
                  All
                </button>
                <button
                  onClick={() => setSelectedRooms(new Set())}
                  className="text-xs text-gray-500 hover:text-gray-700"
                >
                  None
                </button>
              </div>
            </div>

            <div className="p-2 space-y-1">
              {rooms.map((room) => {
                const isSelected = selectedRooms.has(room.id);
                const isActive = room.id === selectedRoomId;
                const displayName =
                  cleanRoomName(room.name) !== 'Unnamed Room'
                    ? cleanRoomName(room.name)
                    : getShortRoomLabel(room.name, room.room_type, room.id);

                return (
                  <div
                    key={room.id}
                    className={`
                      p-3 rounded-lg cursor-pointer transition-all
                      ${isActive ? 'bg-primary-50 border border-primary-200' : 'hover:bg-gray-50'}
                      ${!isSelected && 'opacity-50'}
                    `}
                    onClick={() => setSelectedRoomId(room.id)}
                  >
                    <div className="flex items-center gap-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleRoomSelection(room.id);
                        }}
                        className="text-primary-600"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-5 h-5" />
                        ) : (
                          <Square className="w-5 h-5" />
                        )}
                      </button>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 truncate">{displayName}</div>
                        <div className="text-xs text-gray-500">
                          {formatArea(room.area)} • {room.room_type}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Center Panel - Room Configurator */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedRoom ? (
            <div className="max-w-2xl mx-auto space-y-6">
              {/* Room Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {cleanRoomName(selectedRoom.name) !== 'Unnamed Room'
                      ? cleanRoomName(selectedRoom.name)
                      : getShortRoomLabel(selectedRoom.name, selectedRoom.room_type, selectedRoom.id)}
                  </h2>
                  <p className="text-gray-500">
                    {formatArea(selectedRoom.area)} • {selectedRoom.room_type}
                  </p>
                </div>
                <Button
                  variant={selectedRooms.has(selectedRoom.id) ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => toggleRoomSelection(selectedRoom.id)}
                >
                  {selectedRooms.has(selectedRoom.id) ? 'Selected' : 'Select'}
                </Button>
              </div>

              {/* Materials */}
              <Card variant="static">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-primary-600" />
                  Materials
                </h3>

                <div className="space-y-4">
                  {/* Floor */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Floor</label>
                    <select
                      value={roomMaterials[selectedRoom.id]?.floor || ''}
                      onChange={(e) => updateRoomMaterial(selectedRoom.id, 'floor', e.target.value)}
                      className="select"
                    >
                      {floorMaterials.map((mat) => (
                        <option key={mat.id} value={mat.id}>
                          {mat.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Walls */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Walls</label>
                    <select
                      value={roomMaterials[selectedRoom.id]?.wall || ''}
                      onChange={(e) => updateRoomMaterial(selectedRoom.id, 'wall', e.target.value)}
                      className="select"
                    >
                      {wallMaterials.map((mat) => (
                        <option key={mat.id} value={mat.id}>
                          {mat.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Ceiling */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Ceiling</label>
                    <select
                      value={roomMaterials[selectedRoom.id]?.ceiling || ''}
                      onChange={(e) =>
                        updateRoomMaterial(selectedRoom.id, 'ceiling', e.target.value)
                      }
                      className="select"
                    >
                      {ceilingMaterials.map((mat) => (
                        <option key={mat.id} value={mat.id}>
                          {mat.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-border">
                  <button
                    onClick={() => {
                      const mats = roomMaterials[selectedRoom.id];
                      if (mats?.floor) applyMaterialToAllRooms('floor', mats.floor);
                      if (mats?.wall) applyMaterialToAllRooms('wall', mats.wall);
                      if (mats?.ceiling) applyMaterialToAllRooms('ceiling', mats.ceiling);
                    }}
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Apply to all rooms
                  </button>
                </div>
              </Card>

              {/* Style Selection */}
              <Card variant="static">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Palette className="w-5 h-5 text-primary-600" />
                  Design Style
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {styleOptions.map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setSelectedStyle(style.id)}
                      className={`
                        p-4 rounded-lg border-2 text-left transition-all
                        ${
                          selectedStyle === style.id
                            ? 'border-primary bg-primary-50'
                            : 'border-border hover:border-border-hover'
                        }
                      `}
                    >
                      <div className="font-medium text-gray-900">{style.name}</div>
                      <div className="text-xs text-gray-500">{style.desc}</div>
                    </button>
                  ))}
                </div>
              </Card>

              {/* Additional Prompt */}
              <Card variant="static">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Additional Details (Optional)
                </label>
                <textarea
                  value={additionalPrompt}
                  onChange={(e) => setAdditionalPrompt(e.target.value)}
                  placeholder="Add furniture, plants, specific decor..."
                  className="input resize-none"
                  rows={3}
                />
              </Card>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Home className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">Select a room to configure</p>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Settings & Queue */}
        <div className="w-80 border-l border-border bg-white overflow-y-auto">
          <div className="p-4 space-y-6">
            {/* Lighting Settings */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Settings2 className="w-5 h-5 text-primary-600" />
                Lighting
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Style</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['natural', 'warm', 'cool', 'dramatic'].map((light) => (
                      <button
                        key={light}
                        onClick={() => setLighting(light)}
                        className={`
                          p-2 rounded-lg border text-sm capitalize transition-all
                          ${
                            lighting === light
                              ? 'border-primary bg-primary-50 text-primary-700'
                              : 'border-border hover:border-border-hover'
                          }
                        `}
                      >
                        {light}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Time of Day</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'day', icon: Sun, label: 'Day' },
                      { id: 'evening', icon: Sunset, label: 'Evening' },
                      { id: 'night', icon: Moon, label: 'Night' },
                    ].map((time) => (
                      <button
                        key={time.id}
                        onClick={() => setTimeOfDay(time.id)}
                        className={`
                          p-2 rounded-lg border text-sm flex flex-col items-center gap-1 transition-all
                          ${
                            timeOfDay === time.id
                              ? 'border-primary bg-primary-50 text-primary-700'
                              : 'border-border hover:border-border-hover'
                          }
                        `}
                      >
                        <time.icon className="w-4 h-4" />
                        {time.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Render Queue Summary */}
            <div className="border-t border-border pt-4">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-primary-600" />
                Render Queue
              </h3>

              <div className="space-y-3">
                {rooms
                  .filter((r) => selectedRooms.has(r.id))
                  .map((room) => {
                    const displayName =
                      cleanRoomName(room.name) !== 'Unnamed Room'
                        ? cleanRoomName(room.name)
                        : getShortRoomLabel(room.name, room.room_type, room.id);
                    return (
                      <div
                        key={room.id}
                        className="flex items-center gap-3 p-2 bg-surface-base rounded-lg"
                      >
                        <div className="w-8 h-8 rounded bg-primary-100 flex items-center justify-center">
                          <Home className="w-4 h-4 text-primary-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            {displayName}
                          </div>
                          <div className="text-xs text-gray-500">{room.room_type}</div>
                        </div>
                        <Badge variant="neutral" size="sm">
                          Queued
                        </Badge>
                      </div>
                    );
                  })}

                {selectedRooms.size === 0 && (
                  <div className="text-center py-4 text-gray-500 text-sm">
                    No rooms selected
                  </div>
                )}
              </div>

              {selectedRooms.size > 0 && (
                <div className="mt-4 p-3 bg-surface-base rounded-lg">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Estimated time</span>
                    <span className="font-medium text-gray-900">
                      ~{Math.ceil(selectedRooms.size * 0.5)} min
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Render Button */}
            <Button
              variant="primary"
              size="lg"
              icon={<Play className="w-5 h-5" />}
              onClick={handleStartRender}
              disabled={!pipelineStatus?.available || selectedRooms.size === 0}
              className="w-full"
            >
              Start Rendering
            </Button>

            {!pipelineStatus?.available && (
              <p className="text-xs text-red-500 text-center">
                DALL-E API not configured
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
