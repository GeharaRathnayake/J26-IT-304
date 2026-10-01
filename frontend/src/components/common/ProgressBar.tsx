import React from 'react';
import './ProgressBar.css';

interface ProgressBarProps {
  label: string;
  percentage: number;
  className?: string;
  fillColor?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  label,
  percentage,
  className = '',
  fillColor = 'var(--bg-progress-fill)',
}) => {
  return (
    <div className={`progress-bar-container ${className}`}>
      <div className="progress-bar-label-group">
        <span className="progress-bar-label">{label}</span>
      </div>
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{
            width: `${Math.min(Math.max(percentage, 0), 100)}%`,
            backgroundColor: fillColor,
          }}
        />
      </div>
      <span className="progress-bar-percentage">{percentage}%</span>
    </div>
  );
};
