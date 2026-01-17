'use client';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

const Skeleton = ({
  className = '',
  variant = 'text',
  width,
  height,
}: SkeletonProps) => {
  const baseStyles = 'skeleton animate-shimmer';

  const variantStyles = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  };

  const style: React.CSSProperties = {
    width: width,
    height: height,
  };

  return (
    <div
      className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      style={style}
    />
  );
};

const SkeletonText = ({
  lines = 3,
  className = '',
}: {
  lines?: number;
  className?: string;
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          width={i === lines - 1 ? '70%' : '100%'}
        />
      ))}
    </div>
  );
};

const SkeletonCard = ({ className = '' }: { className?: string }) => {
  return (
    <div className={`card-static animate-fade-in ${className}`}>
      <Skeleton variant="rectangular" height={160} className="mb-4 -mx-6 -mt-6" />
      <Skeleton variant="text" width="60%" height={24} className="mb-2" />
      <Skeleton variant="text" width="40%" height={16} className="mb-4" />
      <div className="flex gap-2">
        <Skeleton variant="rectangular" width={80} height={32} />
        <Skeleton variant="rectangular" width={80} height={32} />
      </div>
    </div>
  );
};

const SkeletonProjectCard = ({ className = '' }: { className?: string }) => {
  return (
    <div className={`card-static ${className}`}>
      <div className="flex items-start gap-4">
        <Skeleton variant="rectangular" width={80} height={80} />
        <div className="flex-1">
          <Skeleton variant="text" width="70%" height={20} className="mb-2" />
          <Skeleton variant="text" width="50%" height={16} className="mb-3" />
          <div className="flex gap-2">
            <Skeleton variant="rectangular" width={60} height={24} />
            <Skeleton variant="rectangular" width={60} height={24} />
          </div>
        </div>
      </div>
    </div>
  );
};

const SkeletonFloorPlan = ({ className = '' }: { className?: string }) => {
  return (
    <div className={`card-static aspect-video ${className}`}>
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Skeleton variant="circular" width={48} height={48} className="mx-auto mb-3" />
          <Skeleton variant="text" width={120} className="mx-auto" />
        </div>
      </div>
    </div>
  );
};

const SkeletonRenderQueue = ({ items = 3 }: { items?: number }) => {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-surface-base">
          <Skeleton variant="rectangular" width={48} height={48} />
          <div className="flex-1">
            <Skeleton variant="text" width="60%" height={16} className="mb-2" />
            <Skeleton variant="rectangular" height={8} />
          </div>
        </div>
      ))}
    </div>
  );
};

const SkeletonMaterialSwatches = ({ count = 6 }: { count?: number }) => {
  return (
    <div className="flex flex-wrap gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} variant="rectangular" width={48} height={48} />
      ))}
    </div>
  );
};

const SkeletonGalleryGrid = ({ items = 6 }: { items?: number }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="card-static p-0 overflow-hidden">
          <Skeleton variant="rectangular" className="aspect-[4/3]" />
          <div className="p-3">
            <Skeleton variant="text" width="70%" height={16} className="mb-1" />
            <Skeleton variant="text" width="50%" height={14} />
          </div>
        </div>
      ))}
    </div>
  );
};

export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonProjectCard,
  SkeletonFloorPlan,
  SkeletonRenderQueue,
  SkeletonMaterialSwatches,
  SkeletonGalleryGrid,
};
export type { SkeletonProps };
