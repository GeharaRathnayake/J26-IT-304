import React from 'react';
import { Mic, PlusCircle, MessageSquare, MicOff } from 'lucide-react';
import { VoiceState } from './VoiceVisualizerOrb';
import './VoiceControlBar.css';

interface VoiceControlBarProps {
  voiceState: VoiceState;
  onToggleMic: () => void;
  onNewSession: () => void;
}

export const VoiceControlBar: React.FC<VoiceControlBarProps> = ({
  voiceState,
  onToggleMic,
  onNewSession,
}) => {
  const isRecording = voiceState === 'LISTENING';

  return (
    <div className="voice-control-bar-wrapper">
      <div className="voice-control-pill">
        <button
          className="control-pill-btn"
          onClick={onNewSession}
          title="Start fresh conversation"
          type="button"
        >
          <PlusCircle size={15} />
          <span>New session</span>
        </button>

        <div className="control-pill-divider" />

        <div className="control-pill-status">
          <MessageSquare size={15} />
          <span>Conversation</span>
        </div>

        {/* Central Floating Mic Action Button */}
        <button
          className={`control-pill-mic-btn ${isRecording ? 'mic-btn-active' : ''}`}
          onClick={onToggleMic}
          title={isRecording ? 'Stop listening' : 'Start speaking with Java Tutor'}
          type="button"
        >
          {isRecording ? <MicOff size={22} /> : <Mic size={22} />}
          {isRecording && <span className="mic-pulse-ring" />}
        </button>
      </div>
    </div>
  );
};
