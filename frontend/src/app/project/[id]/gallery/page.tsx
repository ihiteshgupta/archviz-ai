'use client';

import { useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Grid,
  Columns,
  Clock,
  Filter,
  Download,
  Heart,
  Trash2,
  ChevronDown,
  X,
  Check,
  Share2,
  ZoomIn,
  Layers,
  Image as ImageIcon,
} from 'lucide-react';
import { useProject, useBatchJobs } from '@/lib/hooks';
import { cleanRoomName, formatArea } from '@/lib/utils';
import {
  Button,
  Card,
  CardHeader,
  CardContent,
  Badge,
  Modal,
  ModalFooter,
  Skeleton,
} from '@/components';
import type { BatchRenderResult, BatchRenderJob } from '@/types';

type ViewMode = 'grid' | 'compare' | 'timeline';
type FilterState = {
  room: string | null;
  style: string | null;
  sortBy: 'newest' | 'oldest' | 'room';
};

interface RenderItem extends BatchRenderResult {
  jobId: string;
  jobCreatedAt: string;
  favorite?: boolean;
}

export default function GalleryPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  // Data fetching
  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: batchJobs, isLoading: jobsLoading } = useBatchJobs({
    floor_plan_id: projectId,
    status: 'completed',
    limit: 50,
  });

  // UI State
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filters, setFilters] = useState<FilterState>({
    room: null,
    style: null,
    sortBy: 'newest',
  });
  const [showFilters, setShowFilters] = useState(false);
  const [selectedRenders, setSelectedRenders] = useState<Set<string>>(new Set());
  const [compareItems, setCompareItems] = useState<[RenderItem | null, RenderItem | null]>([null, null]);
  const [lightboxItem, setLightboxItem] = useState<RenderItem | null>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [showShareModal, setShowShareModal] = useState(false);
  const [showDownloadModal, setShowDownloadModal] = useState(false);

  // Flatten all renders from batch jobs
  const allRenders = useMemo(() => {
    if (!batchJobs?.jobs) return [];
    const renders: RenderItem[] = [];
    batchJobs.jobs.forEach((job: BatchRenderJob) => {
      job.results.forEach((result) => {
        renders.push({
          ...result,
          jobId: job.id,
          jobCreatedAt: job.created_at,
          favorite: favorites.has(`${job.id}-${result.room_id}`),
        });
      });
    });
    return renders;
  }, [batchJobs, favorites]);

  // Get unique room names and styles for filters
  const uniqueRooms = useMemo(() => {
    const rooms = new Set(allRenders.map((r) => r.room_name));
    return Array.from(rooms).sort();
  }, [allRenders]);

  const uniqueStyles = useMemo(() => {
    const styles = new Set(allRenders.map((r) => r.config.style_preset));
    return Array.from(styles).sort();
  }, [allRenders]);

  // Apply filters and sorting
  const filteredRenders = useMemo(() => {
    let result = [...allRenders];

    if (filters.room) {
      result = result.filter((r) => r.room_name === filters.room);
    }
    if (filters.style) {
      result = result.filter((r) => r.config.style_preset === filters.style);
    }

    // Sort
    switch (filters.sortBy) {
      case 'newest':
        result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        break;
      case 'oldest':
        result.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
        break;
      case 'room':
        result.sort((a, b) => a.room_name.localeCompare(b.room_name));
        break;
    }

    return result;
  }, [allRenders, filters]);

  // Group by room for timeline view
  const rendersByRoom = useMemo(() => {
    const grouped: Record<string, RenderItem[]> = {};
    filteredRenders.forEach((render) => {
      if (!grouped[render.room_name]) {
        grouped[render.room_name] = [];
      }
      grouped[render.room_name].push(render);
    });
    // Sort each room's renders by date (newest first)
    Object.values(grouped).forEach((renders) => {
      renders.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    });
    return grouped;
  }, [filteredRenders]);

  const toggleFavorite = (renderId: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(renderId)) {
        next.delete(renderId);
      } else {
        next.add(renderId);
      }
      return next;
    });
  };

  const toggleSelect = (renderId: string) => {
    setSelectedRenders((prev) => {
      const next = new Set(prev);
      if (next.has(renderId)) {
        next.delete(renderId);
      } else {
        next.add(renderId);
      }
      return next;
    });
  };

  const selectForCompare = (render: RenderItem, slot: 0 | 1) => {
    setCompareItems((prev) => {
      const next: [RenderItem | null, RenderItem | null] = [...prev];
      next[slot] = render;
      return next;
    });
  };

  const downloadRender = async (url: string, filename: string) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const loading = projectLoading || jobsLoading;

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <GalleryHeader projectName="Loading..." />
        <div className="max-w-7xl mx-auto px-6 py-8">
          <GallerySkeleton />
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <Card className="p-8 text-center">
          <p className="text-gray-500">Project not found</p>
          <Link href="/">
            <Button variant="primary" className="mt-4">
              Go Home
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-base">
      <GalleryHeader projectName={project.name} />

      {/* Toolbar */}
      <div className="sticky top-0 z-20 bg-white border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex items-center justify-between">
            {/* Left: Filters */}
            <div className="flex items-center gap-3">
              <Button
                variant={showFilters ? 'primary' : 'secondary'}
                size="sm"
                icon={<Filter size={16} />}
                onClick={() => setShowFilters(!showFilters)}
              >
                Filters
              </Button>

              {(filters.room || filters.style) && (
                <div className="flex items-center gap-2">
                  {filters.room && (
                    <Badge variant="info" className="flex items-center gap-1">
                      {cleanRoomName(filters.room)}
                      <button onClick={() => setFilters((f) => ({ ...f, room: null }))}>
                        <X size={12} />
                      </button>
                    </Badge>
                  )}
                  {filters.style && (
                    <Badge variant="info" className="flex items-center gap-1">
                      {filters.style}
                      <button onClick={() => setFilters((f) => ({ ...f, style: null }))}>
                        <X size={12} />
                      </button>
                    </Badge>
                  )}
                </div>
              )}

              <span className="text-sm text-gray-500">
                {filteredRenders.length} render{filteredRenders.length !== 1 ? 's' : ''}
              </span>
            </div>

            {/* Right: View Toggles & Actions */}
            <div className="flex items-center gap-3">
              {/* View Mode Toggles */}
              <div className="flex items-center border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 ${viewMode === 'grid' ? 'bg-primary-50 text-primary-600' : 'text-gray-500 hover:bg-gray-50'}`}
                  title="Grid view"
                >
                  <Grid size={18} />
                </button>
                <button
                  onClick={() => setViewMode('compare')}
                  className={`p-2 ${viewMode === 'compare' ? 'bg-primary-50 text-primary-600' : 'text-gray-500 hover:bg-gray-50'}`}
                  title="Compare view"
                >
                  <Columns size={18} />
                </button>
                <button
                  onClick={() => setViewMode('timeline')}
                  className={`p-2 ${viewMode === 'timeline' ? 'bg-primary-50 text-primary-600' : 'text-gray-500 hover:bg-gray-50'}`}
                  title="Timeline view"
                >
                  <Clock size={18} />
                </button>
              </div>

              {/* Batch Actions */}
              {selectedRenders.size > 0 && (
                <div className="flex items-center gap-2 pl-3 border-l border-border">
                  <span className="text-sm text-gray-600">{selectedRenders.size} selected</span>
                  <Button variant="secondary" size="sm" icon={<Download size={16} />} onClick={() => setShowDownloadModal(true)}>
                    Download
                  </Button>
                  <Button variant="secondary" size="sm" icon={<Share2 size={16} />} onClick={() => setShowShareModal(true)}>
                    Share
                  </Button>
                </div>
              )}

              {selectedRenders.size === 0 && (
                <>
                  <Button variant="secondary" size="sm" icon={<Download size={16} />} onClick={() => setShowDownloadModal(true)}>
                    Download All
                  </Button>
                  <Button variant="secondary" size="sm" icon={<Share2 size={16} />} onClick={() => setShowShareModal(true)}>
                    Share
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="flex items-center gap-4 pt-3 mt-3 border-t border-border">
              {/* Room Filter */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">Room:</label>
                <select
                  value={filters.room || ''}
                  onChange={(e) => setFilters((f) => ({ ...f, room: e.target.value || null }))}
                  className="select text-sm"
                >
                  <option value="">All Rooms</option>
                  {uniqueRooms.map((room) => (
                    <option key={room} value={room}>
                      {cleanRoomName(room)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Style Filter */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">Style:</label>
                <select
                  value={filters.style || ''}
                  onChange={(e) => setFilters((f) => ({ ...f, style: e.target.value || null }))}
                  className="select text-sm"
                >
                  <option value="">All Styles</option>
                  {uniqueStyles.map((style) => (
                    <option key={style} value={style}>
                      {style}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sort */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">Sort:</label>
                <select
                  value={filters.sortBy}
                  onChange={(e) => setFilters((f) => ({ ...f, sortBy: e.target.value as FilterState['sortBy'] }))}
                  className="select text-sm"
                >
                  <option value="newest">Newest First</option>
                  <option value="oldest">Oldest First</option>
                  <option value="room">By Room</option>
                </select>
              </div>

              <button
                onClick={() => setFilters({ room: null, style: null, sortBy: 'newest' })}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {filteredRenders.length === 0 ? (
          <EmptyGallery projectId={projectId} />
        ) : viewMode === 'grid' ? (
          <GridView
            renders={filteredRenders}
            selectedRenders={selectedRenders}
            favorites={favorites}
            onSelect={toggleSelect}
            onFavorite={toggleFavorite}
            onDownload={downloadRender}
            onView={setLightboxItem}
          />
        ) : viewMode === 'compare' ? (
          <CompareView
            renders={filteredRenders}
            compareItems={compareItems}
            onSelectA={(r) => selectForCompare(r, 0)}
            onSelectB={(r) => selectForCompare(r, 1)}
            onDownload={downloadRender}
          />
        ) : (
          <TimelineView
            rendersByRoom={rendersByRoom}
            favorites={favorites}
            onFavorite={toggleFavorite}
            onDownload={downloadRender}
            onView={setLightboxItem}
          />
        )}
      </div>

      {/* Lightbox Modal */}
      {lightboxItem && (
        <LightboxModal
          render={lightboxItem}
          onClose={() => setLightboxItem(null)}
          onDownload={() => downloadRender(lightboxItem.image_url, `${cleanRoomName(lightboxItem.room_name)}.png`)}
          isFavorite={favorites.has(`${lightboxItem.jobId}-${lightboxItem.room_id}`)}
          onToggleFavorite={() => toggleFavorite(`${lightboxItem.jobId}-${lightboxItem.room_id}`)}
        />
      )}

      {/* Share Modal */}
      <Modal open={showShareModal} onClose={() => setShowShareModal(false)} title="Share Gallery">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Create a shareable link to your renders. Clients can view and download without an account.
          </p>
          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm">Allow downloads</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Show pricing</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Expires in:</span>
              <select className="select text-sm">
                <option value="7">7 days</option>
                <option value="30">30 days</option>
                <option value="never">Never</option>
              </select>
            </div>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowShareModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" icon={<Share2 size={16} />}>
            Generate Link
          </Button>
        </ModalFooter>
      </Modal>

      {/* Download Modal */}
      <Modal open={showDownloadModal} onClose={() => setShowDownloadModal(false)} title="Download Renders">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            {selectedRenders.size > 0
              ? `Download ${selectedRenders.size} selected render${selectedRenders.size !== 1 ? 's' : ''}`
              : `Download all ${filteredRenders.length} renders`}
          </p>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Format:</span>
              <select className="select text-sm">
                <option value="png">PNG</option>
                <option value="jpg">JPG (smaller file)</option>
                <option value="both">Both PNG & JPG</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Resolution:</span>
              <select className="select text-sm">
                <option value="original">Original</option>
                <option value="4k">4K Upscaled</option>
              </select>
            </div>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Include only favorites</span>
            </label>
          </div>
        </div>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowDownloadModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" icon={<Download size={16} />}>
            Download ZIP
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}

// Header Component
function GalleryHeader({ projectName }: { projectName: string }) {
  return (
    <header className="bg-white border-b border-border">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href={`/project/${useParams().id}`}>
            <Button variant="ghost" size="sm" icon={<ArrowLeft size={18} />}>
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{projectName}</h1>
            <p className="text-sm text-gray-500">Gallery</p>
          </div>
        </div>
      </div>
    </header>
  );
}

// Grid View
function GridView({
  renders,
  selectedRenders,
  favorites,
  onSelect,
  onFavorite,
  onDownload,
  onView,
}: {
  renders: RenderItem[];
  selectedRenders: Set<string>;
  favorites: Set<string>;
  onSelect: (id: string) => void;
  onFavorite: (id: string) => void;
  onDownload: (url: string, filename: string) => void;
  onView: (render: RenderItem) => void;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {renders.map((render) => {
        const renderId = `${render.jobId}-${render.room_id}`;
        const isSelected = selectedRenders.has(renderId);
        const isFavorite = favorites.has(renderId);

        return (
          <Card
            key={renderId}
            variant="interactive"
            className={`group overflow-hidden ${isSelected ? 'ring-2 ring-primary-500' : ''}`}
          >
            {/* Image */}
            <div className="relative aspect-[4/3] bg-gray-100">
              <img src={render.image_url} alt={render.room_name} className="w-full h-full object-cover" />

              {/* Overlay on hover */}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all">
                <div className="absolute inset-0 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => onView(render)}
                    className="p-2 bg-white rounded-full shadow-lg hover:bg-gray-50"
                    title="View"
                  >
                    <ZoomIn size={18} />
                  </button>
                  <button
                    onClick={() => onDownload(render.image_url, `${cleanRoomName(render.room_name)}.png`)}
                    className="p-2 bg-white rounded-full shadow-lg hover:bg-gray-50"
                    title="Download"
                  >
                    <Download size={18} />
                  </button>
                </div>
              </div>

              {/* Selection checkbox */}
              <button
                onClick={() => onSelect(renderId)}
                className={`absolute top-2 left-2 w-6 h-6 rounded border-2 flex items-center justify-center transition-all ${
                  isSelected
                    ? 'bg-primary-500 border-primary-500 text-white'
                    : 'bg-white/80 border-gray-300 opacity-0 group-hover:opacity-100'
                }`}
              >
                {isSelected && <Check size={14} />}
              </button>

              {/* Favorite button */}
              <button
                onClick={() => onFavorite(renderId)}
                className={`absolute top-2 right-2 p-1.5 rounded-full transition-all ${
                  isFavorite
                    ? 'bg-red-500 text-white'
                    : 'bg-white/80 text-gray-500 opacity-0 group-hover:opacity-100 hover:text-red-500'
                }`}
              >
                <Heart size={16} fill={isFavorite ? 'currentColor' : 'none'} />
              </button>
            </div>

            {/* Info */}
            <CardContent className="p-3">
              <h3 className="font-medium text-gray-900 truncate">{cleanRoomName(render.room_name)}</h3>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-500 capitalize">{render.config.style_preset}</span>
                <span className="text-xs text-gray-400">
                  {new Date(render.created_at).toLocaleDateString()}
                </span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

// Compare View
function CompareView({
  renders,
  compareItems,
  onSelectA,
  onSelectB,
  onDownload,
}: {
  renders: RenderItem[];
  compareItems: [RenderItem | null, RenderItem | null];
  onSelectA: (render: RenderItem) => void;
  onSelectB: (render: RenderItem) => void;
  onDownload: (url: string, filename: string) => void;
}) {
  const [sliderPosition, setSliderPosition] = useState(50);

  return (
    <div className="space-y-6">
      {/* Comparison Area */}
      <div className="grid grid-cols-2 gap-6">
        {/* Side A */}
        <Card className="overflow-hidden">
          <CardHeader>
            <h3 className="font-medium text-gray-900">Option A</h3>
          </CardHeader>
          {compareItems[0] ? (
            <div className="relative aspect-[4/3] bg-gray-100">
              <img src={compareItems[0].image_url} alt="Option A" className="w-full h-full object-cover" />
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4">
                <p className="text-white font-medium">{cleanRoomName(compareItems[0].room_name)}</p>
                <p className="text-white/80 text-sm capitalize">{compareItems[0].config.style_preset}</p>
              </div>
            </div>
          ) : (
            <div className="aspect-[4/3] bg-gray-100 flex items-center justify-center">
              <p className="text-gray-400">Select a render below</p>
            </div>
          )}
          <CardContent className="p-3 flex gap-2">
            {compareItems[0] && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  className="flex-1"
                  onClick={() => onDownload(compareItems[0]!.image_url, 'option-a.png')}
                >
                  Pick A
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Download size={14} />}
                  onClick={() => onDownload(compareItems[0]!.image_url, 'option-a.png')}
                />
              </>
            )}
          </CardContent>
        </Card>

        {/* Side B */}
        <Card className="overflow-hidden">
          <CardHeader>
            <h3 className="font-medium text-gray-900">Option B</h3>
          </CardHeader>
          {compareItems[1] ? (
            <div className="relative aspect-[4/3] bg-gray-100">
              <img src={compareItems[1].image_url} alt="Option B" className="w-full h-full object-cover" />
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4">
                <p className="text-white font-medium">{cleanRoomName(compareItems[1].room_name)}</p>
                <p className="text-white/80 text-sm capitalize">{compareItems[1].config.style_preset}</p>
              </div>
            </div>
          ) : (
            <div className="aspect-[4/3] bg-gray-100 flex items-center justify-center">
              <p className="text-gray-400">Select a render below</p>
            </div>
          )}
          <CardContent className="p-3 flex gap-2">
            {compareItems[1] && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  className="flex-1"
                  onClick={() => onDownload(compareItems[1]!.image_url, 'option-b.png')}
                >
                  Pick B
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Download size={14} />}
                  onClick={() => onDownload(compareItems[1]!.image_url, 'option-b.png')}
                />
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Download Both */}
      {compareItems[0] && compareItems[1] && (
        <div className="flex justify-center">
          <Button
            variant="secondary"
            icon={<Download size={16} />}
            onClick={() => {
              onDownload(compareItems[0]!.image_url, 'option-a.png');
              onDownload(compareItems[1]!.image_url, 'option-b.png');
            }}
          >
            Download Both
          </Button>
        </div>
      )}

      {/* Render Selection */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">Select renders to compare:</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
          {renders.map((render) => {
            const renderId = `${render.jobId}-${render.room_id}`;
            const isA = compareItems[0]?.room_id === render.room_id && compareItems[0]?.jobId === render.jobId;
            const isB = compareItems[1]?.room_id === render.room_id && compareItems[1]?.jobId === render.jobId;

            return (
              <div key={renderId} className="relative">
                <img
                  src={render.image_url}
                  alt={render.room_name}
                  className={`w-full aspect-[4/3] object-cover rounded-lg cursor-pointer border-2 transition-all ${
                    isA ? 'border-blue-500' : isB ? 'border-green-500' : 'border-transparent hover:border-gray-300'
                  }`}
                  onClick={() => (!isA && !isB ? (compareItems[0] ? onSelectB(render) : onSelectA(render)) : null)}
                />
                <div className="absolute bottom-1 left-1 right-1 flex gap-1">
                  <button
                    onClick={() => onSelectA(render)}
                    className={`flex-1 text-xs py-1 rounded ${
                      isA ? 'bg-blue-500 text-white' : 'bg-white/90 text-gray-700 hover:bg-blue-100'
                    }`}
                  >
                    A
                  </button>
                  <button
                    onClick={() => onSelectB(render)}
                    className={`flex-1 text-xs py-1 rounded ${
                      isB ? 'bg-green-500 text-white' : 'bg-white/90 text-gray-700 hover:bg-green-100'
                    }`}
                  >
                    B
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Timeline View
function TimelineView({
  rendersByRoom,
  favorites,
  onFavorite,
  onDownload,
  onView,
}: {
  rendersByRoom: Record<string, RenderItem[]>;
  favorites: Set<string>;
  onFavorite: (id: string) => void;
  onDownload: (url: string, filename: string) => void;
  onView: (render: RenderItem) => void;
}) {
  return (
    <div className="space-y-8">
      {Object.entries(rendersByRoom).map(([roomName, renders]) => (
        <div key={roomName}>
          <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
            <Layers size={18} className="text-gray-400" />
            {cleanRoomName(roomName)}
            <Badge variant="neutral" size="sm">
              {renders.length} version{renders.length !== 1 ? 's' : ''}
            </Badge>
          </h3>

          {/* Horizontal scroll container */}
          <div className="overflow-x-auto pb-4">
            <div className="flex gap-4" style={{ minWidth: 'max-content' }}>
              {renders.map((render, index) => {
                const renderId = `${render.jobId}-${render.room_id}`;
                const isFavorite = favorites.has(renderId);

                return (
                  <Card key={renderId} className="w-64 flex-shrink-0 overflow-hidden group">
                    <div className="relative aspect-[4/3] bg-gray-100">
                      <img src={render.image_url} alt={render.room_name} className="w-full h-full object-cover" />

                      {/* Version badge */}
                      {index === 0 && (
                        <Badge variant="success" size="sm" className="absolute top-2 left-2">
                          Latest
                        </Badge>
                      )}

                      {/* Favorite */}
                      <button
                        onClick={() => onFavorite(renderId)}
                        className={`absolute top-2 right-2 p-1.5 rounded-full transition-all ${
                          isFavorite
                            ? 'bg-red-500 text-white'
                            : 'bg-white/80 text-gray-500 opacity-0 group-hover:opacity-100 hover:text-red-500'
                        }`}
                      >
                        <Heart size={14} fill={isFavorite ? 'currentColor' : 'none'} />
                      </button>

                      {/* Actions */}
                      <div className="absolute bottom-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => onView(render)}
                          className="p-1.5 bg-white rounded-full shadow hover:bg-gray-50"
                        >
                          <ZoomIn size={14} />
                        </button>
                        <button
                          onClick={() => onDownload(render.image_url, `${cleanRoomName(render.room_name)}-v${renders.length - index}.png`)}
                          className="p-1.5 bg-white rounded-full shadow hover:bg-gray-50"
                        >
                          <Download size={14} />
                        </button>
                      </div>
                    </div>

                    <CardContent className="p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500 capitalize">{render.config.style_preset}</span>
                        <span className="text-xs text-gray-400">
                          {new Date(render.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Empty State
function EmptyGallery({ projectId }: { projectId: string }) {
  return (
    <Card className="py-16 text-center">
      <ImageIcon size={48} className="mx-auto text-gray-300 mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">No renders yet</h3>
      <p className="text-gray-500 mb-6">Head to the Render Studio to create your first visualization.</p>
      <Link href={`/project/${projectId}/render`}>
        <Button variant="primary">Open Render Studio</Button>
      </Link>
    </Card>
  );
}

// Lightbox Modal
function LightboxModal({
  render,
  onClose,
  onDownload,
  isFavorite,
  onToggleFavorite,
}: {
  render: RenderItem;
  onClose: () => void;
  onDownload: () => void;
  isFavorite: boolean;
  onToggleFavorite: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center" onClick={onClose}>
      <button className="absolute top-4 right-4 p-2 text-white/70 hover:text-white" onClick={onClose}>
        <X size={24} />
      </button>

      <div className="max-w-5xl max-h-[90vh] relative" onClick={(e) => e.stopPropagation()}>
        <img src={render.image_url} alt={render.room_name} className="max-w-full max-h-[85vh] object-contain" />

        {/* Info bar */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-6">
          <div className="flex items-end justify-between">
            <div>
              <h3 className="text-white text-xl font-medium">{cleanRoomName(render.room_name)}</h3>
              <p className="text-white/70 capitalize">{render.config.style_preset} • {render.config.time_of_day}</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                icon={<Heart size={16} fill={isFavorite ? 'currentColor' : 'none'} />}
                onClick={onToggleFavorite}
                className={isFavorite ? 'text-red-500' : ''}
              >
                {isFavorite ? 'Favorited' : 'Favorite'}
              </Button>
              <Button variant="primary" size="sm" icon={<Download size={16} />} onClick={onDownload}>
                Download
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Skeleton
function GallerySkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {Array.from({ length: 8 }).map((_, i) => (
        <Card key={i} className="overflow-hidden">
          <Skeleton className="aspect-[4/3]" />
          <CardContent className="p-3 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <div className="flex justify-between">
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
