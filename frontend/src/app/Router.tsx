import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';
import { StudentDashboard } from '../pages/StudentDashboard';
import { JavaIDETutor } from '../pages/JavaIDETutor';
import { JavaVoiceTutor } from '../pages/JavaVoiceTutor';
import { AdaptiveQuiz } from '../pages/AdaptiveQuiz';
import { SmartVideoLearning } from '../pages/SmartVideoLearning';

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<StudentDashboard />} />
        <Route path="ide-tutor" element={<JavaIDETutor />} />
        <Route path="voice-tutor" element={<JavaVoiceTutor />} />
        <Route path="adaptive-quiz" element={<AdaptiveQuiz />} />
        <Route path="smart-video" element={<SmartVideoLearning />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
};
