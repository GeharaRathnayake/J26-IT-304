import type { LocalAudioTrack } from 'livekit-client';
import { AgentAudioVisualizerWave } from '@/components/agents-ui/agent-audio-visualizer-wave';
import { useMicState } from './voiceState';

export default function VoiceWave({ track }: { track: LocalAudioTrack | null }) {
  const state = useMicState(track);
  return <AgentAudioVisualizerWave size="sm" color="#3F6F91" colorShift={0.3} lineWidth={2} state={state} audioTrack={track ?? undefined} className="aspect-auto h-full w-full" />;
}
