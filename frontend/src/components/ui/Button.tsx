'use client';

import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = '',
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'left',
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-all rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2';

    const variantStyles = {
      primary:
        'bg-gradient-to-b from-primary-600 to-primary-700 text-white hover:from-primary-700 hover:to-primary-800 hover:shadow-md focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed',
      secondary:
        'bg-surface-base border border-border text-gray-900 hover:border-border-hover hover:bg-gray-50 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed',
      ghost:
        'bg-transparent text-gray-600 hover:bg-surface-base hover:text-gray-900 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed',
      danger:
        'bg-gradient-to-b from-red-600 to-red-700 text-white hover:from-red-700 hover:to-red-800 hover:shadow-md focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed',
    };

    const sizeStyles = {
      sm: 'px-3 py-1.5 text-sm gap-1.5',
      md: 'px-4 py-2 text-sm gap-2',
      lg: 'px-6 py-3 text-base gap-2',
    };

    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        disabled={isDisabled}
        {...props}
      >
        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        {!loading && icon && iconPosition === 'left' && icon}
        {children}
        {!loading && icon && iconPosition === 'right' && icon}
      </button>
    );
  }
);

Button.displayName = 'Button';

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  label: string;
}

const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className = '', variant = 'default', size = 'md', label, children, ...props }, ref) => {
    const baseStyles =
      'inline-flex items-center justify-center rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500';

    const variantStyles = {
      default:
        'bg-surface-base border border-border text-gray-600 hover:border-border-hover hover:text-gray-900 disabled:opacity-50',
      ghost: 'text-gray-600 hover:bg-surface-base hover:text-gray-900 disabled:opacity-50',
    };

    const sizeStyles = {
      sm: 'w-8 h-8',
      md: 'w-10 h-10',
      lg: 'w-12 h-12',
    };

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        aria-label={label}
        {...props}
      >
        {children}
      </button>
    );
  }
);

IconButton.displayName = 'IconButton';

export { Button, IconButton };
export type { ButtonProps, IconButtonProps };
