'use client';

import { forwardRef } from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral';
  size?: 'sm' | 'md';
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant = 'neutral', size = 'md', children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center font-medium rounded-full';

    const variantStyles = {
      success: 'bg-emerald-50 text-emerald-700',
      warning: 'bg-amber-50 text-amber-700',
      error: 'bg-red-50 text-red-700',
      info: 'bg-blue-50 text-blue-700',
      neutral: 'bg-gray-100 text-gray-600',
    };

    const sizeStyles = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-xs',
    };

    return (
      <span
        ref={ref}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

interface StatusBadgeProps {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'parsed' | 'created';
}

const StatusBadge = ({ status }: StatusBadgeProps) => {
  const statusConfig = {
    pending: { variant: 'neutral' as const, label: 'Pending' },
    running: { variant: 'info' as const, label: 'Running' },
    completed: { variant: 'success' as const, label: 'Completed' },
    failed: { variant: 'error' as const, label: 'Failed' },
    parsed: { variant: 'success' as const, label: 'Ready' },
    created: { variant: 'neutral' as const, label: 'No File' },
  };

  const config = statusConfig[status] || statusConfig.pending;

  return <Badge variant={config.variant}>{config.label}</Badge>;
};

export { Badge, StatusBadge };
export type { BadgeProps, StatusBadgeProps };
