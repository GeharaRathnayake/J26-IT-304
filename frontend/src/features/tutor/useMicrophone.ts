import { useEffect, useState } from 'react';
import type { LocalAudioTrack } from 'livekit-client';

// Opens the student's microphone while `active`, and releases it when not.
// livekit-client is imported on demand so it stays out of the main bundle.
export function useMicrophone(active: boolean) {
  const [track, setTrack] = useState<LocalAudioTrack | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    let created: LocalAudioTrack | null = null;
    setError(null);
    import('livekit-client')
      .then(({ createLocalAudioTrack }) => createLocalAudioTrack())
      .then((next) => {
        if (cancelled) { next.stop(); return; }
        created = next;
        setTrack(next);
      })
      .catch(() => {
        if (!cancelled) setError('Microphone access was blocked or no microphone was found.');
      });
    return () => {
      cancelled = true;
      created?.stop();
      setTrack(null);
    };
  }, [active]);

  return { track, error };
}
