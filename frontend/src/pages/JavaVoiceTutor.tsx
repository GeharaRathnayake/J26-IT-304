import React from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Mic, Volume2 } from 'lucide-react';

export const JavaVoiceTutor: React.FC = () => {
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
            <Mic size={24} />
          </div>
          <div>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              COMPONENT 2
            </span>
            <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-dark)' }}>
              Java Voice Tutor
            </h2>
          </div>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px', maxWidth: '650px' }}>
          Conversational voice-driven Java instruction powered by VAPI. Speak naturally to ask questions, receive multi-strategy explanations, and evaluate your understanding in real time.
        </p>

        <div style={{
          padding: '24px',
          background: 'var(--bg-subtle)',
          borderRadius: '14px',
          border: '1px dashed var(--border-light)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '14px',
          textAlign: 'center',
          marginBottom: '20px'
        }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            background: 'var(--color-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FFFFFF',
            boxShadow: '0 8px 20px rgba(0, 163, 150, 0.3)'
          }}>
            <Mic size={28} />
          </div>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-dark)' }}>
              Voice Session Ready
            </h3>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Press the button below to start talking with your AI tutor
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="primary" icon={<Volume2 size={16} />}>
            Start Voice Conversation
          </Button>
        </div>
      </Card>
    </div>
  );
};
