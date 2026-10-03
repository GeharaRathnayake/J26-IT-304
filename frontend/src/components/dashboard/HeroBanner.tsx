import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import './HeroBanner.css';

interface HeroBannerProps {
  studentName?: string;
  onOpenVoiceTutor?: () => void;
}

export const HeroBanner: React.FC<HeroBannerProps> = ({
  studentName = 'Demo',
  onOpenVoiceTutor,
}) => {
  const navigate = useNavigate();

  const handleOpenVoiceTutor = () => {
    if (onOpenVoiceTutor) {
      onOpenVoiceTutor();
    } else {
      navigate('/voice-tutor');
    }
  };

  return (
    <Card className="hero-banner">
      <div className="hero-banner-content">
        <span className="hero-banner-tag">STUDENT DASHBOARD</span>
        <h2 className="hero-banner-title">Welcome, {studentName}</h2>
        <p className="hero-banner-description">
          Start with Java Voice Tutor. Topic progress will appear on this dashboard.
        </p>
        <div className="hero-banner-actions">
          <Button
            variant="primary"
            size="md"
            onClick={handleOpenVoiceTutor}
            className="hero-banner-btn"
          >
            Open Java Voice Tutor
          </Button>
        </div>
      </div>
    </Card>
  );
};
