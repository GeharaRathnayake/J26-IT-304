import React from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Video, Eye } from 'lucide-react';

export const SmartVideoLearning: React.FC = () => {
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
            <Video size={24} />
          </div>
          <div>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              COMPONENT 4
            </span>
            <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-dark)' }}>
              Smart Video Learning
            </h2>
          </div>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px', maxWidth: '650px' }}>
          Real-time attention tracking during video lectures with inline adaptive MCQs triggered whenever conceptual lapses or attention dropoffs are detected.
        </p>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="primary" icon={<Eye size={16} />}>
            Launch Video Session
          </Button>
        </div>
      </Card>
    </div>
  );
};
