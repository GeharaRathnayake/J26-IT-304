import React from 'react';
import { Breadcrumbs } from '../components/common/Breadcrumbs';
import { Badge } from '../components/common/Badge';
import './Header.css';

interface HeaderProps {
  breadcrumbs?: Array<{ label: string; isCurrent?: boolean }>;
  badgeText?: string;
}

export const Header: React.FC<HeaderProps> = ({
  breadcrumbs = [
    { label: 'Java LMS' },
    { label: 'Student Dashboard' },
    { label: 'Demo', isCurrent: true },
  ],
  badgeText = 'VAPI',
}) => {
  return (
    <header className="main-header">
      <div className="header-left">
        <Breadcrumbs items={breadcrumbs} />
      </div>
      <div className="header-right">
        <Badge variant="vapi" size="sm">
          {badgeText}
        </Badge>
      </div>
    </header>
  );
};
