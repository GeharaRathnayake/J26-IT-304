import React from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { CheckCircle2, Sparkles } from 'lucide-react';

export const AdaptiveQuiz: React.FC = () => {
  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '16px' }}>
          <div style={{
            background: 'var(--color-primary-light)',
            color: 'var(--color-primary)',
            padding: '12px',
            borderRadius: '12px',
            display: 'flex'
          }}>
            <CheckCircle2 size={24} />
          </div>
          <div>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              COMPONENT 3
            </span>
            <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-dark)' }}>
              Adaptive Quiz Engine
            </h2>
          </div>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px', maxWidth: '650px' }}>
          Personalized dynamic quiz generator that adjusts question difficulty according to your knowledge profile and automatically tracks weak areas like Object &amp; Class.
        </p>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="primary" icon={<Sparkles size={16} />}>
            Generate Adaptive Quiz
          </Button>
        </div>
      </Card>
    </div>
  );
};
