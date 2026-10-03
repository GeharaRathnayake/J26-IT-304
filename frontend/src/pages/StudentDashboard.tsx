import React, { useEffect, useState } from 'react';
import { HeroBanner } from '../components/dashboard/HeroBanner';
import { MetricCards } from '../components/dashboard/MetricCards';
import { WeaknessTopicCard } from '../components/dashboard/WeaknessTopicCard';
import { StrategyEffectivenessCard } from '../components/dashboard/StrategyEffectivenessCard';
import { fetchStudentDashboardData } from '../services/dashboardService';
import { StudentDashboardData } from '../types';
import './StudentDashboard.css';

export const StudentDashboard: React.FC = () => {
  const [data, setData] = useState<StudentDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    fetchStudentDashboardData()
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load dashboard data', err);
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (loading || !data) {
    return (
      <div className="dashboard-loading-container">
        <div className="dashboard-loading-spinner" />
        <span>Loading your personalized dashboard...</span>
      </div>
    );
  }

  return (
    <div className="student-dashboard animate-fade-in">
      {/* Top Welcome Hero Banner */}
      <HeroBanner studentName={data.student.name} />

      {/* 4 Metric Stats Cards */}
      <MetricCards data={data} />

      {/* Bottom 2 Split Cards: Weakness Area & Strategy Effectiveness */}
      <div className="dashboard-bottom-grid">
        <div className="dashboard-bottom-col">
          <WeaknessTopicCard topics={data.weaknessList} />
        </div>
        <div className="dashboard-bottom-col">
          <StrategyEffectivenessCard strategies={data.strategyEffectiveness} />
        </div>
      </div>
    </div>
  );
};
