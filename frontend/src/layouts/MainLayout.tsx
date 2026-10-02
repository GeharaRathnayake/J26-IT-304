import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import './MainLayout.css';

export const MainLayout: React.FC = () => {
  const location = useLocation();

  // Dynamic breadcrumbs based on route
  const getBreadcrumbs = () => {
    const base = [{ label: 'Java LMS' }];
    if (location.pathname === '/dashboard' || location.pathname === '/') {
      return [...base, { label: 'Student Dashboard' }, { label: 'Demo', isCurrent: true }];
    } else if (location.pathname === '/ide-tutor') {
      return [...base, { label: 'Java IDE Tutor' }, { label: '1st Component', isCurrent: true }];
    } else if (location.pathname === '/voice-tutor') {
      return [...base, { label: 'Java Voice Tutor' }, { label: '2nd Component', isCurrent: true }];
    } else if (location.pathname === '/adaptive-quiz') {
      return [...base, { label: 'Adaptive Quiz' }, { label: '3rd Component', isCurrent: true }];
    } else if (location.pathname === '/smart-video') {
      return [...base, { label: 'Smart Video Learning' }, { label: '4th Component', isCurrent: true }];
    }
    return base;
  };

  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-viewport">
        <Header breadcrumbs={getBreadcrumbs()} />
        <main className="main-content-area">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
