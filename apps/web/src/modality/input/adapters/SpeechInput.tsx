/**
 * Spoken input.
 *
 * Three things here are deliberate and none of them are negotiable:
 *
 *  1. NO RECORDING TIME LIMIT. Not a long one — none. P3 (dysarthria) and P5
 *     (stammer) may need many seconds for one sentence, and a countdown is the
 *     single fastest way to make this product unusable for them (Ethics E6).
 *
 *  2. HONEST DEGRADATION. If the speech service reports no ASR, we say so
 *     plainly and point at the alternative, rather than accepting a recording
 *     that will never be transcribed.
 *
 *  3. NEVER SCORED ON A BAD TRANSCRIPTION. Below the confidence threshold the
 *     learner is asked to confirm what they meant. Marking a misrecognised
 *     answer wrong is exactly how mainstream speech tools fail atypical
 *     speakers, and it is the failure this product exists to correct.
 */
import { useCallback, useRef, useState } from 'react';
import type { LearnerResponse } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { useSpeechCapabilities } from '@/services/capabilities';

import type { InputAdapterProps } from '../registry';
import { buildResponse, needsConfirmation } from '../response';
import { submitButtonStyle } from './TextInput';

/** Injected by the session layer once the speech service is wired up (M6). */
export type Transcriber = (audio: Blob, blockId: string) => Promise<{
  text: string;
  confidence: number;
  audioRef?: string;
  model?: string;
}>;

type Phase = 'idle' | 'recording' | 'transcribing' | 'confirming';

export interface SpeechInputProps extends InputAdapterProps {
  transcribe?: Transcriber;
}

export function SpeechInput({
  block,
  profile,
  sessionId,
  onResponse,
  disabled,
  transcribe,
}: SpeechInputProps) {
  const { speech, loaded } = useSpeechCapabilities();
  const announce = useAnnounce();

  const [phase, setPhase] = useState<Phase>('idle');
  const [pending, setPending] = useState<LearnerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(1);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAt = useRef(new Date());

  const available = speech.asr && typeof transcribe === 'function' && supportsRecording();

  const stop = useCallback(() => {
    recorderRef.current?.stop();
    recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    recorderRef.current = null;
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      startedAt.current = new Date();

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        const audio = new Blob(chunksRef.current, { type: recorder.mimeType });
        setPhase('transcribing');
        announce('Listening to your answer');

        try {
          const result = await transcribe!(audio, block.id);
          const response = buildResponse({
            block,
            profile,
            sessionId,
            inputMode: 'speech',
            text: result.text,
            startedAt: startedAt.current,
            attempts,
            confidence: result.confidence,
            raw: {
              ...(result.audioRef ? { audio_ref: result.audioRef } : {}),
              asr_text: result.text,
              ...(result.model ? { asr_model: result.model } : {}),
            },
          });

          if (needsConfirmation(response)) {
            // Not an error and not a failure — just uncertainty we refuse to
            // resolve on the learner's behalf.
            setPending(response);
            setPhase('confirming');
            announce('Please check what I heard');
          } else {
            onResponse(response);
            setAttempts((n) => n + 1);
            setPhase('idle');
            announce('Answer sent');
          }
        } catch {
          setError('Your answer could not be processed. Please try again, or type it instead.');
          setPhase('idle');
        }
      };

      recorder.start();
      recorderRef.current = recorder;
      setPhase('recording');
      announce('Recording. Take as long as you need.');
    } catch {
      setError('The microphone is not available. Check permissions, or type your answer instead.');
      setPhase('idle');
    }
  }, [announce, attempts, block, onResponse, profile, sessionId, transcribe]);

  if (loaded && !available) {
    return <SpeechUnavailable reason={speech.asr ? 'browser' : 'service'} />;
  }

  if (phase === 'confirming' && pending) {
    return (
      <ConfirmHeard
        response={pending}
        onAccept={() => {
          onResponse(pending);
          setPending(null);
          setAttempts((n) => n + 1);
          setPhase('idle');
          announce('Answer sent');
        }}
        onRetry={() => {
          setPending(null);
          setPhase('idle');
          announce('Try again');
        }}
      />
    );
  }

  return (
    <div data-input-mode="speech">
      <p style={{ margin: '0 0 var(--space-sm, 0.5rem)', color: 'var(--colour-fg-muted)' }}>
        Say: <strong style={{ color: 'var(--colour-fg)' }}>{block.canonical_text}</strong>
      </p>
      <p style={{ margin: '0 0 var(--space-md, 1rem)', color: 'var(--colour-fg-muted)' }}>
        Take as long as you need. Recording does not stop on its own.
      </p>

      {phase === 'recording' ? (
        <button type="button" onClick={stop} style={submitButtonStyle(false)}>
          Stop recording
        </button>
      ) : (
        <button
          type="button"
          onClick={start}
          disabled={disabled || phase === 'transcribing'}
          style={submitButtonStyle(Boolean(disabled) || phase === 'transcribing')}
        >
          {phase === 'transcribing' ? 'Working…' : 'Start recording'}
        </button>
      )}

      {error && (
        <p role="alert" style={{ marginTop: 'var(--space-sm, 0.5rem)', color: 'var(--colour-fg)' }}>
          {error}
        </p>
      )}
    </div>
  );
}

function ConfirmHeard({
  response,
  onAccept,
  onRetry,
}: {
  response: LearnerResponse;
  onAccept: () => void;
  onRetry: () => void;
}) {
  return (
    <div data-input-mode="speech" data-phase="confirming">
      {/* Framed as the tool's uncertainty, never as the learner's mistake.
          "I heard" and not "you said". */}
      <p style={{ margin: 0 }}>I heard:</p>
      <p
        style={{
          fontSize: 'var(--type-lg, 1.375rem)',
          fontWeight: 700,
          margin: 'var(--space-sm, 0.5rem) 0',
        }}
      >
        “{response.canonical_text}”
      </p>
      <p style={{ margin: '0 0 var(--space-md, 1rem)', color: 'var(--colour-fg-muted)' }}>
        Is that what you meant?
      </p>

      <div style={{ display: 'flex', gap: 'var(--space-sm, 0.5rem)', flexWrap: 'wrap' }}>
        <button type="button" onClick={onAccept} style={submitButtonStyle(false)}>
          Yes, that&apos;s right
        </button>
        <button
          type="button"
          onClick={onRetry}
          style={{ ...submitButtonStyle(true), cursor: 'pointer' }}
        >
          No, let me say it again
        </button>
      </div>
    </div>
  );
}

function SpeechUnavailable({ reason }: { reason: 'service' | 'browser' }) {
  return (
    <div data-input-mode="speech" data-state="unavailable">
      <p style={{ margin: 0 }}>
        {reason === 'browser'
          ? 'This browser cannot record audio.'
          : 'Spoken answers are not available yet.'}
      </p>
      <p style={{ margin: 'var(--space-sm, 0.5rem) 0 0', color: 'var(--colour-fg-muted)' }}>
        You can still complete this lesson — answer another way instead. Nothing here needs
        speech.
      </p>
    </div>
  );
}

function supportsRecording(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.MediaRecorder !== 'undefined' &&
    typeof navigator !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getUserMedia)
  );
}
