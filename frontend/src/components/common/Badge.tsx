import React from 'react';
import './Badge.css';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'danger' | 'success' | 'teal' | 'subtle' | 'vapi';
  className?: string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'subtle',
  className = '',
  size = 'sm',
}) => {
  return (
    <span className={`custom-badge custom-badge-${variant} custom-badge-${size} ${className}`}>
      {children}
    </span>
  );
};
