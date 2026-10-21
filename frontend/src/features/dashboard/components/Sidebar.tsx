import { useState } from 'react';

export type DashboardNavSection =
  | 'overview'
  | 'weak-topics'
  | 'teaching-methods'
  | 'pedagogy-audit'
  | 'tutor-chat';

interface SidebarProps {
  currentSection: DashboardNavSection;
  onSelectSection: (section: DashboardNavSection) => void;
  onOpenTutor: () => void;
  weakTopicsCount: number;
}

export function Sidebar({
  currentSection,
  onSelectSection,
  onOpenTutor,
  weakTopicsCount,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`relative flex flex-col border-r border-[#d7e4ed] bg-white transition-all duration-200 select-none ${
        collapsed ? 'w-[72px]' : 'w-[260px]'
      }`}
      aria-label="Dashboard navigation"
    >
      {/* Brand Header */}
      <div className="flex h-[72px] items-center justify-between border-b border-[#e5eff6] px-4">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#0284c7] to-[#0369a1] text-white shadow-sm">
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-[#1e293b] leading-tight">Java AI Tutor</span>
              <span className="text-[11px] font-semibold tracking-wide text-[#0284c7] uppercase">
                Pedagogy Dashboard
              </span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[#617687] hover:bg-[#f4f8fb] hover:text-[#1e293b]"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            className={`h-4 w-4 transform transition-transform ${collapsed ? 'rotate-180' : ''}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1.5 p-3 overflow-y-auto">
        <div className={`px-2 py-1 text-[11px] font-extrabold tracking-wider text-[#8da0ad] uppercase ${collapsed ? 'sr-only' : ''}`}>
          Analytics & Insights
        </div>

        {/* Overview Dashboard */}
        <button
          type="button"
          onClick={() => onSelectSection('overview')}
          className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
            currentSection === 'overview'
              ? 'bg-[#e0f2fe] text-[#0369a1]'
              : 'text-[#617687] hover:bg-[#f4f8fb] hover:text-[#1e293b]'
          }`}
          title="Dashboard Overview"
        >
          <svg
            className="h-5 w-5 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect width="7" height="9" x="3" y="3" rx="1" />
            <rect width="7" height="5" x="14" y="3" rx="1" />
            <rect width="7" height="9" x="14" y="12" rx="1" />
            <rect width="7" height="5" x="3" y="16" rx="1" />
          </svg>
          {!collapsed && <span>Overview Dashboard</span>}
        </button>

        {/* Weak Topic Areas */}
        <button
          type="button"
          onClick={() => onSelectSection('weak-topics')}
          className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
            currentSection === 'weak-topics'
              ? 'bg-[#fee2e2] text-[#b91c1c]'
              : 'text-[#617687] hover:bg-[#f4f8fb] hover:text-[#1e293b]'
          }`}
          title="Weakness Topic Areas"
        >
          <div className="flex items-center gap-3 min-w-0">
            <svg
              className="h-5 w-5 shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            {!collapsed && <span className="truncate">Weak Topic Areas</span>}
          </div>
          {!collapsed && (
            <span className="flex h-5 items-center justify-center rounded-full bg-[#ef4444] px-2 text-[11px] font-bold text-white">
              {weakTopicsCount}
            </span>
          )}
        </button>

        {/* Teaching Methods */}
        <button
          type="button"
          onClick={() => onSelectSection('teaching-methods')}
          className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
            currentSection === 'teaching-methods'
              ? 'bg-[#e0f2fe] text-[#0369a1]'
              : 'text-[#617687] hover:bg-[#f4f8fb] hover:text-[#1e293b]'
          }`}
          title="Teaching Strategies & Methods"
        >
          <svg
            className="h-5 w-5 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
            <path d="M6 6h10" />
            <path d="M6 10h10" />
          </svg>
          {!collapsed && <span>Teaching Methods</span>}
        </button>

        {/* Pedagogy Audit / Escalation Engine */}
        <button
          type="button"
          onClick={() => onSelectSection('pedagogy-audit')}
          className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
            currentSection === 'pedagogy-audit'
              ? 'bg-[#e0f2fe] text-[#0369a1]'
              : 'text-[#617687] hover:bg-[#f4f8fb] hover:text-[#1e293b]'
          }`}
          title="3-Strategy Rule & Escalations"
        >
          <svg
            className="h-5 w-5 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 20v-6M6 20V10M18 20V4" />
          </svg>
          {!collapsed && <span>3-Strategy Rule Audit</span>}
        </button>

        <div className="pt-4">
          <div className={`px-2 py-1 text-[11px] font-extrabold tracking-wider text-[#8da0ad] uppercase ${collapsed ? 'sr-only' : ''}`}>
            Interactive Learning
          </div>

          {/* AI Voice Tutor Launch */}
          <button
            type="button"
            onClick={onOpenTutor}
            className="group flex w-full items-center gap-3 rounded-xl border border-[#bae6fd] bg-gradient-to-r from-[#f0f9ff] to-[#e0f2fe] px-3 py-3 text-sm font-bold text-[#0369a1] shadow-sm transition hover:shadow-md"
            title="Switch to AI Voice Tutor"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#0284c7] text-white">
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            </div>
            {!collapsed && (
              <div className="flex flex-col text-left">
                <span className="leading-tight">AI Voice Tutor</span>
                <span className="text-[11px] font-normal text-[#0369a1]">Launch interactive session</span>
              </div>
            )}
          </button>
        </div>
      </nav>

      {/* Student Profile Footer */}
      <div className="border-t border-[#e5eff6] p-3">
        <div className={`flex items-center gap-3 rounded-xl bg-[#f4f8fb] p-2.5 ${collapsed ? 'justify-center' : ''}`}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#0284c7]/15 font-bold text-[#0284c7]">
            AR
          </div>
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="truncate text-xs font-bold text-[#1e293b]">Alex Rivera</span>
              <span className="truncate text-[11px] text-[#617687]">CS102 Â· IT-304 Cohort</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
