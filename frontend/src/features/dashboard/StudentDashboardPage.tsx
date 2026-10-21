import React, { useState } from 'react';
import {
  initialProfile,
  initialWeakTopics,
  initialTeachingMethods,
} from './dashboardData';
import type { WeakTopicItem, TeachingMethodCard, StudentDashboardProfile } from './types';
import type { Strategy } from '../tutor/api/types';
import { Sidebar, type NavItemKey } from './components/Sidebar';
import { DashboardHeader } from './components/DashboardHeader';
import { WelcomeHero } from './components/WelcomeHero';
import { MetricStatCards } from './components/MetricStatCards';
import { WeakTopicsSection } from './components/WeakTopicsSection';
import { PrioritizedTeachingMethodsSection } from './components/PrioritizedTeachingMethodsSection';
import { TopicDiagnosticModal } from './components/TopicDiagnosticModal';
import { SimulateEpisodeModal } from './components/SimulateEpisodeModal';
import { ComponentPreviewModal } from './components/ComponentPreviewModal';

interface StudentDashboardPageProps {
  onNavigateToVoiceTutor?: (initialTopic?: string, initialStrategy?: Strategy) => void;
}

export const StudentDashboardPage: React.FC<StudentDashboardPageProps> = ({
  onNavigateToVoiceTutor,
}) => {
  const [profile, setProfile] = useState<StudentDashboardProfile>(initialProfile);
  const [weakTopics, setWeakTopics] = useState<WeakTopicItem[]>(initialWeakTopics);
  const [teachingMethods, setTeachingMethods] = useState<TeachingMethodCard[]>(initialTeachingMethods);
  const [selectedTopicForPreview, setSelectedTopicForPreview] = useState<WeakTopicItem>(
    initialWeakTopics[0]
  );
  const [inspectingTopic, setInspectingTopic] = useState<WeakTopicItem | null>(null);
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);
  const [currentNav, setCurrentNav] = useState<NavItemKey>('dashboard');
  const [previewNavModal, setPreviewNavModal] = useState<NavItemKey | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Handle nav clicks
  const handleSelectNav = (key: NavItemKey) => {
    if (key === 'dashboard') {
      setCurrentNav('dashboard');
    } else if (key === 'voice_tutor') {
      if (onNavigateToVoiceTutor) {
        onNavigateToVoiceTutor();
      } else {
        alert('Navigating to Voice Tutor');
      }
    } else {
      // Show informational preview for the other 3 team components
      setPreviewNavModal(key);
    }
  };

  // Launch Voice tutor with pre-configured topic
  const handleLaunchVoiceTutor = (topicSlug?: string, strategy?: Strategy) => {
    if (onNavigateToVoiceTutor) {
      onNavigateToVoiceTutor(topicSlug, strategy);
    } else {
      alert(`Launching Voice Tutor for topic: ${topicSlug || 'default'} with strategy: ${strategy || 'default'}`);
    }
  };

  // Resolve a weak topic
  const handleResolveTopic = (id: string) => {
    setWeakTopics((prev) => prev.filter((t) => t.id !== id));
    setProfile((prev) => ({
      ...prev,
      weakTopicsCount: Math.max(0, prev.weakTopicsCount - 1),
      conceptsLearned: prev.conceptsLearned + 1,
    }));
  };

  // Add a newly simulated weak topic
  const handleAddSimulatedTopic = (newTopic: WeakTopicItem) => {
    setWeakTopics((prev) => [newTopic, ...prev]);
    setSelectedTopicForPreview(newTopic);
    setProfile((prev) => ({
      ...prev,
      weakTopicsCount: prev.weakTopicsCount + 1,
    }));
    // Also bump up analogy win telemetry
    setTeachingMethods((prev) =>
      prev.map((m) =>
        m.strategy === 'analogy'
          ? {
              ...m,
              winCount: m.winCount + 1,
              totalUses: m.totalUses + 1,
              successRate: Math.round(((m.winCount + 1) / (m.totalUses + 1)) * 100),
            }
          : m
      )
    );
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#f3f8f7] text-[#13322d] flex flex-row font-sans">
      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        currentNav={currentNav}
        onSelectNav={handleSelectNav}
        studentName={profile.name}
        avatarLetter={profile.avatarLetter}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* 2. Main Dashboard Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Sticky Top Bar */}
        <DashboardHeader
          onOpenVoiceTutor={() => handleLaunchVoiceTutor()}
          onSimulateEpisode={() => setIsSimulateModalOpen(true)}
          studentName={profile.name}
          vapiStatus={profile.vapiEngineStatus}
        />

        {/* Dashboard Main Body */}
        <main className="p-4 md:p-8 space-y-6 md:space-y-8 max-w-7xl w-full mx-auto">
          {/* Welcome Hero Banner */}
          <WelcomeHero
            studentName={profile.name}
            onOpenVoiceTutor={() => handleLaunchVoiceTutor()}
            onResumeTopic={(slug) => handleLaunchVoiceTutor(slug)}
          />

          {/* 4 Metric Stat Cards */}
          <MetricStatCards
            profile={profile}
            onScrollToWeakTopics={() => scrollToSection('weakness-topics')}
            onScrollToTeachingMethods={() => scrollToSection('teaching-methods')}
          />

          {/* Centerpiece 1: Weakness Topic Area */}
          <WeakTopicsSection
            weakTopics={weakTopics}
            onOpenVoiceTutorWithTopic={(slug) => handleLaunchVoiceTutor(slug)}
            onInspectTopic={(topic) => setInspectingTopic(topic)}
            onResolveTopic={handleResolveTopic}
            onOpenQuizModal={(topic) => setInspectingTopic(topic)}
          />

          {/* Centerpiece 2: Prioritized Personalized Teaching Method Cards */}
          <PrioritizedTeachingMethodsSection
            methods={teachingMethods}
            selectedTopicForPreview={selectedTopicForPreview}
            allTopics={weakTopics}
            onSelectTopicForPreview={setSelectedTopicForPreview}
            onOpenVoiceTutorWithStrategy={(strategy) =>
              handleLaunchVoiceTutor(selectedTopicForPreview?.slug, strategy)
            }
          />

          {/* Research Architecture & Pedagogical Strategy Callout */}
          <section className="bg-gradient-to-br from-[#123932] to-[#0c2722] text-white rounded-3xl p-6 md:p-8 shadow-xl shadow-teal-950/10">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="space-y-2 max-w-2xl">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-300">
                    J26-IT-304 Research Architecture
                  </span>
                </div>
                <h3 className="text-xl md:text-2xl font-extrabold tracking-tight">
                  Adaptive Teaching Escalation Engine (Ollama llama3.2:3b)
                </h3>
                <p className="text-xs md:text-sm text-[#9ec4bc] leading-relaxed">
                  When a student sends a message, our hybrid classifier (Rule Layer + TF-IDF Logistic Regression)
                  detects confusion. Rather than looping, the tutor automatically pivots to the highest-ranked
                  personalized pedagogical strategy: <strong className="text-white">Theory âž” Example âž” Simpler âž” Analogy</strong>.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsSimulateModalOpen(true)}
                  className="px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xl border border-white/20 transition-all"
                >
                  Simulate Escalation âš¡
                </button>
                <button
                  type="button"
                  onClick={() => handleLaunchVoiceTutor()}
                  className="px-6 py-2.5 bg-gradient-to-r from-[#0ca58e] to-[#0ba089] hover:from-[#0dae96] hover:to-[#0cb39a] text-white font-extrabold text-xs rounded-xl shadow-lg shadow-teal-900/40 transition-all hover:scale-[1.02]"
                >
                  Launch Voice Tutor ðŸŽ™ï¸
                </button>
              </div>
            </div>
          </section>
        </main>
      </div>

      {/* Modals */}
      <TopicDiagnosticModal
        topic={inspectingTopic}
        onClose={() => setInspectingTopic(null)}
        onLaunchVoiceTutor={(slug) => handleLaunchVoiceTutor(slug)}
      />

      <SimulateEpisodeModal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
        onTopicAdded={handleAddSimulatedTopic}
      />

      <ComponentPreviewModal
        navItem={previewNavModal}
        onClose={() => setPreviewNavModal(null)}
        onOpenVoiceTutor={() => handleLaunchVoiceTutor()}
      />
    </div>
  );
};
