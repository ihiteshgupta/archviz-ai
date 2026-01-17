'use client';

interface ProgressBarProps {
  value: number;
  max?: number;
  variant?: 'default' | 'success' | 'warning' | 'gradient';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  label?: string;
  className?: string;
}

const ProgressBar = ({
  value,
  max = 100,
  variant = 'default',
  size = 'md',
  showLabel = false,
  label,
  className = '',
}: ProgressBarProps) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const sizeStyles = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  };

  const variantStyles = {
    default: 'bg-primary-600',
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    gradient: 'bg-gradient-to-r from-primary-600 to-oak',
  };

  return (
    <div className={className}>
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-gray-600">{label}</span>
          {showLabel && (
            <span className="text-sm font-medium text-gray-700">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      <div className={`bg-gray-100 rounded-full overflow-hidden ${sizeStyles[size]}`}>
        <div
          className={`h-full rounded-full transition-all duration-300 ease-out ${variantStyles[variant]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

interface RenderProgressProps {
  current: number;
  total: number;
  status?: 'pending' | 'running' | 'completed' | 'failed';
  roomName?: string;
}

const RenderProgress = ({
  current,
  total,
  status = 'running',
  roomName,
}: RenderProgressProps) => {
  const statusColors = {
    pending: 'text-gray-500',
    running: 'text-primary-600',
    completed: 'text-emerald-600',
    failed: 'text-red-600',
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-sm">
        <span className={statusColors[status]}>
          {roomName || `${current} of ${total}`}
        </span>
        <span className="text-gray-500">{Math.round((current / total) * 100)}%</span>
      </div>
      <ProgressBar
        value={current}
        max={total}
        variant={status === 'completed' ? 'success' : status === 'failed' ? 'warning' : 'gradient'}
        size="md"
      />
    </div>
  );
};

export { ProgressBar, RenderProgress };
export type { ProgressBarProps, RenderProgressProps };
