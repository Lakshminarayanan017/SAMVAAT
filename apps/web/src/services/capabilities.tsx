/**
 * What the backend can actually do right now.
 *
 * Mirrors the speech service's `/capabilities` endpoint. The client reads this
 * rather than assuming, so it can degrade *honestly* — telling a learner
 * "spoken feedback isn't available yet, you can type instead" rather than
 * showing them a spinner that will never resolve.
 *
 * Everything defaults to false. A capability is only true once the module
 * implementing it has landed with a passing evaluation run.
 */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export interface SpeechCapabilities {
  asr: boolean;
  forced_alignment: boolean;
  gop: boolean;
  prosody: boolean;
  disfluency: boolean;
  personalised_asr: boolean;
  ppi: boolean;
}

export const NO_CAPABILITIES: SpeechCapabilities = {
  asr: false,
  forced_alignment: false,
  gop: false,
  prosody: false,
  disfluency: false,
  personalised_asr: false,
  ppi: false,
};

interface CapabilitiesValue {
  speech: SpeechCapabilities;
  /** False until the first probe resolves, so the UI can avoid flicker. */
  loaded: boolean;
}

const CapabilitiesContext = createContext<CapabilitiesValue>({
  speech: NO_CAPABILITIES,
  loaded: false,
});

export function CapabilitiesProvider({
  children,
  speechServiceUrl = import.meta.env['VITE_SPEECH_SERVICE_URL'] ?? 'http://localhost:8100',
  initial,
}: {
  children: ReactNode;
  speechServiceUrl?: string;
  /** Injected in tests and in the comparison view; skips the network probe. */
  initial?: SpeechCapabilities;
}) {
  const [speech, setSpeech] = useState<SpeechCapabilities>(initial ?? NO_CAPABILITIES);
  const [loaded, setLoaded] = useState(initial !== undefined);

  useEffect(() => {
    if (initial !== undefined) return;

    const controller = new AbortController();

    fetch(`${speechServiceUrl}/capabilities`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : NO_CAPABILITIES))
      .then((data: SpeechCapabilities) => setSpeech({ ...NO_CAPABILITIES, ...data }))
      // An unreachable speech service is indistinguishable, from the learner's
      // point of view, from one with nothing implemented: either way speech is
      // unavailable and they need the alternative path. So we do not surface an
      // error, we just stay at NO_CAPABILITIES.
      .catch(() => setSpeech(NO_CAPABILITIES))
      .finally(() => setLoaded(true));

    return () => controller.abort();
  }, [speechServiceUrl, initial]);

  const value = useMemo(() => ({ speech, loaded }), [speech, loaded]);

  return <CapabilitiesContext.Provider value={value}>{children}</CapabilitiesContext.Provider>;
}

export function useSpeechCapabilities(): CapabilitiesValue {
  return useContext(CapabilitiesContext);
}
