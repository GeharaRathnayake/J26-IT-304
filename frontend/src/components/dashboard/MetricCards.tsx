import React from 'react';
import { Card } from '../common/Card';
import { StudentDashboardData } from '../../types';
import './MetricCards.css';

interface MetricCardsProps {
  data: StudentDashboardData;
}

export const MetricCards: React.FC<MetricCardsProps> = ({ data }) => {
  return (
    <div className="metrics-grid">
      {/* 1. CURRENT LEVEL */}
      <Card className="metric-card" hoverEffect>
        <span className="metric-card-label">CURRENT LEVEL</span>
        <div className="metric-card-value-wrapper">
          <span className="metric-card-value metric-value-accent">
            {data.currentLevel.level}
          </span>
        </div>
        <span className="metric-card-subtext">{data.currentLevel.subtext}</span>
      </Card>

      {/* 2. CONCEPTS LEARNED */}
      <Card className="metric-card" hoverEffect>
        <span className="metric-card-label">CONCEPTS LEARNED</span>
        <div className="metric-card-value-wrapper">
          <span className="metric-card-value">{data.conceptsLearned.count}</span>
        </div>
        <span className="metric-card-subtext">{data.conceptsLearned.subtext}</span>
      </Card>

      {/* 3. WEAK TOPICS */}
      <Card className="metric-card" hoverEffect>
        <span className="metric-card-label">WEAK TOPICS</span>
        <div className="metric-card-value-wrapper">
          <span className="metric-card-value">{data.weakTopics.count}</span>
        </div>
        <span className="metric-card-subtext">{data.weakTopics.subtext}</span>
      </Card>

      {/* 4. HELPFUL STYLE */}
      <Card className="metric-card" hoverEffect>
        <span className="metric-card-label">HELPFUL STYLE</span>
        <div className="metric-card-value-wrapper">
          <span className="metric-card-value metric-value-style">
            {data.helpfulStyle.style}
          </span>
        </div>
        <span className="metric-card-subtext">{data.helpfulStyle.subtext}</span>
      </Card>
    </div>
  );
};
