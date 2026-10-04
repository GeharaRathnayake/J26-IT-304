import React, { useRef, useEffect } from 'react';
import { Card } from '../common/Card';
import { Volume2, Sparkles, User } from 'lucide-react';
import './ConversationStream.css';

export interface DialogueTurn {
  id: string;
  sender: 'AGENT' | 'STUDENT';
  text: string;
  timestamp: string;
  strategyUsed?: string;
  codeSnippet?: string;
}

interface ConversationStreamProps {
  dialogues: DialogueTurn[];
  onPlayAudio?: (text: string) => void;
  isAgentSpeaking?: boolean;
}

export const ConversationStream: React.FC<ConversationStreamProps> = ({
  dialogues,
  onPlayAudio,
  isAgentSpeaking,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [dialogues]);

  return (
    <Card className="conversation-card">
      <div className="conversation-card-header">
        <div className="conversation-title-row">
          <h3 className="conversation-title">Conversation</h3>
          <span className="conversation-turns-count">
            {dialogues.length} {dialogues.length === 1 ? 'turn' : 'turns'}
          </span>
        </div>
        <p className="conversation-subtitle">
          Agent and student turns appear as paragraphs. This list scrolls in place.
        </p>
      </div>

      <div className="conversation-stream-container">
        {dialogues.map((turn, index) => {
          const isAgent = turn.sender === 'AGENT';
          return (
            <div
              key={turn.id || index}
              className={`conversation-turn-wrapper ${isAgent ? 'turn-agent' : 'turn-student'}`}
            >
              <div className="turn-meta">
                <div className="turn-sender-badge">
                  {isAgent ? (
                    <>
                      <Sparkles size={13} className="turn-icon-agent" />
                      <span className="turn-sender-name">AGENT</span>
                    </>
                  ) : (
                    <>
                      <User size={13} className="turn-icon-student" />
                      <span className="turn-sender-name">STUDENT</span>
                    </>
                  )}
                </div>

                {turn.strategyUsed && (
                  <span className="turn-strategy-tag">
                    Strategy: {turn.strategyUsed}
                  </span>
                )}

                <span className="turn-timestamp">{turn.timestamp}</span>
              </div>

              <div className="turn-content-box">
                <p className="turn-text">{turn.text}</p>

                {turn.codeSnippet && (
                  <pre className="turn-code-box">
                    <code>{turn.codeSnippet}</code>
                  </pre>
                )}

                {isAgent && (
                  <button
                    className="turn-audio-btn"
                    onClick={() => onPlayAudio && onPlayAudio(turn.text)}
                    title="Listen to audio explanation"
                    type="button"
                  >
                    <Volume2 size={14} />
                    <span>Replay Audio</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {isAgentSpeaking && (
          <div className="conversation-turn-wrapper turn-agent turn-typing">
            <div className="turn-sender-badge">
              <Sparkles size={13} className="turn-icon-agent" />
              <span className="turn-sender-name">AGENT</span>
            </div>
            <div className="typing-indicator">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </Card>
  );
};
