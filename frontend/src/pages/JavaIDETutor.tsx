import React from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Code2, Play, Terminal } from 'lucide-react';

export const JavaIDETutor: React.FC = () => {
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
            <Code2 size={24} />
          </div>
          <div>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              COMPONENT 1
            </span>
            <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-dark)' }}>
              Java IDE Tutor
            </h2>
          </div>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px', maxWidth: '650px' }}>
          Interactive Java code environment with real-time AI error diagnosis, intelligent step-by-step hints, and adaptive code completion.
        </p>

        <div style={{
          background: '#0F172A',
          borderRadius: '12px',
          padding: '20px',
          color: '#F8FAFC',
          fontFamily: 'var(--font-mono)',
          fontSize: '13.5px',
          lineHeight: '1.6',
          marginBottom: '20px'
        }}>
          <div style={{ color: '#64748B', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={16} /> // Java Interactive Workspace
          </div>
          <div><span style={{ color: '#EC4899' }}>public class</span> <span style={{ color: '#F59E0B' }}>Main</span> &#123;</div>
          <div style={{ paddingLeft: '20px' }}>
            <span style={{ color: '#EC4899' }}>public static void</span> <span style={{ color: '#38BDF8' }}>main</span>(String[] args) &#123;
          </div>
          <div style={{ paddingLeft: '40px', color: '#10B981' }}>
            System.out.println(<span style={{ color: '#A3E635' }}>"Welcome to Java AI Tutor!"</span>);
          </div>
          <div style={{ paddingLeft: '20px' }}>&#125;</div>
          <div>&#125;</div>
        </div>

        <Button variant="primary" icon={<Play size={16} />}>
          Run Code Workspace
        </Button>
      </Card>
    </div>
  );
};
