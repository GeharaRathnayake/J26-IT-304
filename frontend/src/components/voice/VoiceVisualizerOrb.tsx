import React from 'react';
import './VoiceVisualizerOrb.css';

export type VoiceState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING';

interface VoiceVisualizerOrbProps {
  state: VoiceState;
  onClick?: () => void;
}

export const VoiceVisualizerOrb: React.FC<VoiceVisualizerOrbProps> = ({ state, onClick }) => {
  const getStatusLabel = () => {
    switch (state) {
      case 'LISTENING':
        return 'LISTENING...';
      case 'THINKING':
        return 'PROCESSING...';
      case 'SPEAKING':
        return 'SPEAKING';
      default:
        return 'IDLE';
    }
  };

  const getStatusDesc = () => {
    switch (state) {
      case 'LISTENING':
        return 'Listening to your voice. Speak clearly...';
      case 'THINKING':
        return 'Adapting explanation to your learning level...';
      case 'SPEAKING':
        return 'AI Tutor is explaining the concept...';
      default:
        return 'Press the microphone. The circle shows when the agent is hearing or speaking.';
    }
  };

  return (
    <div className="orb-container">
      <div className="orb-wrapper" onClick={onClick} role="button" tabIndex={0}>
        <div className={`orb-glow orb-glow-${state.toLowerCase()}`} />
        <div className={`orb-ripple orb-ripple-${state.toLowerCase()}`} />
        <div className={`orb-core orb-core-${state.toLowerCase()}`}>
          <div className="orb-highlight" />
          <div className="orb-inner-shadow" />
          {state === 'SPEAKING' && (
            <div className="orb-soundwave">
              <span className="wave-bar bar-1" />
              <span className="wave-bar bar-2" />
              <span className="wave-bar bar-3" />
              <span className="wave-bar bar-4" />
              <span className="wave-bar bar-5" />
            </div>
          )}
        </div>
      </div>

      <div className="orb-status-text">
        <span className={`orb-state-label orb-state-${state.toLowerCase()}`}>
          {getStatusLabel()}
        </span>
        <p className="orb-state-desc">{getStatusDesc()}</p>
      </div>
    </div>
  );
};
