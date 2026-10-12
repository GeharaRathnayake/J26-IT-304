import { useTrackVolume } from '@livekit/components-react';
import type { LocalAudioTrack } from 'livekit-client';

// The visualizers only mirror the student's own voice: "speaking" while the
// microphone is picking up sound, otherwise a calm "idle". Tutor output and
// thinking states are never shown.
export function useMicState(track: LocalAudioTrack | null) {
  const volume = useTrackVolume(track as never, { fftSize: 512, smoothingTimeConstant: 0.55 });
  return volume > 0.03 ? ('speaking' as const) : ('idle' as const);
}
