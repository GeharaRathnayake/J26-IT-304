import { useEffect, useState } from 'react';
import type { LocalAudioTrack } from 'livekit-client';
import { AgentAudioVisualizerAura } from '@/components/agents-ui/agent-audio-visualizer-aura';
import { useMicState } from './voiceState';

function usePrefersDark() {
  const [dark, setDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches);
  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => setDark(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  return dark;
}

export default function VoiceAura({ track }: { track: LocalAudioTrack | null }) {
  const dark = usePrefersDark();
  const state = useMicState(track);
  return <AgentAudioVisualizerAura size="lg" color="#1FD5F9" colorShift={0.3} state={state} audioTrack={track ?? undefined} themeMode={dark ? 'dark' : 'light'} className="tutor-voice-aura" />;
}
