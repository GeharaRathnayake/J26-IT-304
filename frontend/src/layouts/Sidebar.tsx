import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
  Code2,
  Mic,
  CheckCircle2,
  Video,
  LogOut,
} from 'lucide-react';
import './Sidebar.css';

interface SidebarProps {
  userName?: string;
  userRole?: string;
  onLogout?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  userName = 'Demo',
  userRole = 'Logged in',
  onLogout,
}) => {
  const navItems = [
    {
      to: '/dashboard',
      title: 'Student Dashboard',
      subtitle: 'Overview',
      icon: <LayoutGrid size={18} strokeWidth={2.2} />,
    },
    {
      to: '/ide-tutor',
      title: 'Java IDE Tutor',
      subtitle: '1st component',
      icon: <Code2 size={18} strokeWidth={2.2} />,
    },
    {
      to: '/voice-tutor',
      title: 'Java Voice Tutor',
      subtitle: '2nd component',
      icon: <Mic size={18} strokeWidth={2.2} />,
    },
    {
      to: '/adaptive-quiz',
      title: 'Adaptive Quiz',
      subtitle: '3rd component',
      icon: <CheckCircle2 size={18} strokeWidth={2.2} />,
    },
    {
      to: '/smart-video',
      title: 'Smart Video Learning',
      subtitle: 'Attention & adaptive MCQs',
      icon: <Video size={18} strokeWidth={2.2} />,
    },
  ];

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="sidebar-logo-icon">
          <span>J</span>
        </div>
        <div className="sidebar-brand-text">
          <h1 className="sidebar-brand-title">Java LMS</h1>
          <span className="sidebar-brand-subtitle">Java Programming</span>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="sidebar-nav-container">
        <div className="sidebar-section-label">NAVIGATION</div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `sidebar-nav-item ${isActive ? 'sidebar-nav-item-active' : ''}`
              }
            >
              <div className="sidebar-nav-icon-wrapper">{item.icon}</div>
              <div className="sidebar-nav-text">
                <span className="sidebar-nav-title">{item.title}</span>
                <span className="sidebar-nav-subtitle">{item.subtitle}</span>
              </div>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* User Info & Logout Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-user-card">
          <div className="sidebar-user-avatar">
            <span>{userName.charAt(0).toUpperCase()}</span>
          </div>
          <div className="sidebar-user-info">
            <span className="sidebar-user-name">{userName}</span>
            <span className="sidebar-user-status">{userRole}</span>
          </div>
        </div>
        <button
          className="sidebar-logout-btn"
          onClick={onLogout || (() => alert('Logged out successfully!'))}
          type="button"
        >
          <LogOut size={15} />
          <span>Log out</span>
        </button>
      </div>
    </aside>
  );
};
