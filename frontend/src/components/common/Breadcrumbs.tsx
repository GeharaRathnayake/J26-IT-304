import React from 'react';
import './Breadcrumbs.css';

interface BreadcrumbsProps {
  items: Array<{
    label: string;
    path?: string;
    isCurrent?: boolean;
  }>;
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ items }) => {
  return (
    <nav className="breadcrumbs-nav" aria-label="Breadcrumb">
      <ol className="breadcrumbs-list">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={index} className="breadcrumbs-item">
              {item.isCurrent || isLast ? (
                <span className="breadcrumbs-current" aria-current="page">
                  {item.label}
                </span>
              ) : (
                <span className="breadcrumbs-link">{item.label}</span>
              )}
              {!isLast && <span className="breadcrumbs-separator">/</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
