import React, { useState } from 'react';
import { VoiceVisualizerOrb, VoiceState } from '../components/voice/VoiceVisualizerOrb';
import { ConversationStream, DialogueTurn } from '../components/voice/ConversationStream';
import { VoiceControlBar } from '../components/voice/VoiceControlBar';
import { Card } from '../components/common/Card';
import './JavaVoiceTutor.css';

const INITIAL_DIALOGUE: DialogueTurn[] = [
  {
    id: 'turn-1',
    sender: 'AGENT',
    text: 'Hi Demo. Name a Java topic, such as class and object, and I will explain it.',
    timestamp: 'Just now',
    strategyUsed: 'Adaptive Theory',
  },
];

const SAMPLE_EXPLANATION = {
  text: 'In Java, a Class is a user-defined blueprint or prototype from which objects are created. It represents the set of properties (fields) and behaviors (methods) that are common to all objects of one type.',
  code: 'public class Car {\n    String model;\n    void drive() {\n        System.out.println("Driving...");\n    }\n}',
};

export const JavaVoiceTutor: React.FC = () => {
  const [voiceState, setVoiceState] = useState<VoiceState>('IDLE');
  const [dialogues, setDialogues] = useState<DialogueTurn[]>(INITIAL_DIALOGUE);

  // Toggle Microphone (Start / Stop listening)
  const handleToggleMic = () => {
    if (voiceState === 'LISTENING') {
      // User finished speaking -> Transition to Thinking -> Speaking
      setVoiceState('THINKING');

      setTimeout(() => {
        // Add student message turn
        const studentTurn: DialogueTurn = {
          id: `turn-std-${Date.now()}`,
          sender: 'STUDENT',
          text: 'Can you explain Classes and Objects in Java?',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        setDialogues((prev) => [...prev, studentTurn]);
        setVoiceState('SPEAKING');

        // Play audio synthesis if supported
        speakText(SAMPLE_EXPLANATION.text);

        // Add AI Agent response turn
        setTimeout(() => {
          const agentTurn: DialogueTurn = {
            id: `turn-agent-${Date.now()}`,
            sender: 'AGENT',
            text: SAMPLE_EXPLANATION.text,
            codeSnippet: SAMPLE_EXPLANATION.code,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            strategyUsed: 'Adaptive Explanation',
          };
          setDialogues((prev) => [...prev, agentTurn]);

          // Return back to idle after speech completes
          setTimeout(() => {
            setVoiceState('IDLE');
          }, 3500);
        }, 1200);
      }, 900);
    } else {
      // Start listening
      setVoiceState('LISTENING');
    }
  };

  // Trigger speech synthesis
  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Replay Audio for an existing message
  const handlePlayAudio = (text: string) => {
    speakText(text);
    setVoiceState('SPEAKING');
    setTimeout(() => {
      setVoiceState('IDLE');
    }, 2800);
  };

  // Reset to new session
  const handleNewSession = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setVoiceState('IDLE');
    setDialogues(INITIAL_DIALOGUE);
  };

  return (
    <div className="java-voice-tutor-page animate-fade-in">
      <div className="voice-tutor-layout">
        {/* Left Column: Interactive 3D Voice Orb */}
        <div className="voice-tutor-left-column">
          <Card className="voice-tutor-main-card">
            <div className="voice-tutor-header">
              <h2 className="voice-tutor-title">Java Voice Tutor</h2>
              <span className="voice-tutor-component-tag">2ND COMPONENT</span>
            </div>

            {/* Glowing 3D Orb Visualizer */}
            <VoiceVisualizerOrb
              state={voiceState}
              onClick={handleToggleMic}
            />
          </Card>
        </div>

        {/* Right Column: Live Conversation Stream */}
        <div className="voice-tutor-right-column">
          <ConversationStream
            dialogues={dialogues}
            onPlayAudio={handlePlayAudio}
            isAgentSpeaking={voiceState === 'THINKING' || voiceState === 'SPEAKING'}
          />
        </div>
      </div>

      {/* Floating Bottom Capsule Control Bar */}
      <VoiceControlBar
        voiceState={voiceState}
        onToggleMic={handleToggleMic}
        onNewSession={handleNewSession}
      />
    </div>
  );
};
