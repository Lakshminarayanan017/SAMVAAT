/**
 * Spoken input.
 *
 * Capture, resampling and quality analysis live in `@/audio`; this adapter is
 * the conversation around them. Four things here are deliberate:
 *
 *  1. THE QUALITY CHECK COMES FIRST. The microphone is opened and the room
 *     measured before the learner speaks. Ten attempts in a noisy room produce
 *     ten bad scores and a learner who reasonably concludes the app does not
 *     understand them — when the real problem was a microphone two metres away.
 *
 *  2. NO RECORDING TIME LIMIT. Not a long one, none. A learner with dysarthria
 *     or a stammer may need thirty seconds for one sentence (Ethics E6).
 *
 *  3. HONEST DEGRADATION. If the speech service reports no ASR, we say so
 *     plainly and point at the alternative, rather than accepting a recording
 *     that will never be transcribed.
 *
 *  4. NEVER SCORED ON A BAD TRANSCRIPTION. Below the confidence threshold the
 *     learner is asked to confirm what they meant. Marking a misrecognised
 *     answer wrong is how mainstream speech tools fail atypical speakers, and
 *     it is the failure this product exists to correct.
 */
import { useCallback, useRef, useState } from 'react';
import type { LearnerResponse } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { InputQualityMeter } from '@/audio/InputQualityMeter';
import { useAudioRecorder, type Recording } from '@/audio/useAudioRecorder';
import { useSpeechCapabilities } from '@/services/capabilities';

import type { InputAdapterProps } from '../registry';
import { buildResponse, needsConfirmation } from '../response';
import { submitButtonStyle } from './TextInput';

/** Injected by the session layer once the speech service is wired up (M6). */
export type Transcriber = (
  audio: Blob,
  blockId: string,
) => Promise<{ text: string; confidence: number; audioRef?: string; model?: string }>;

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

  const [pending, setPending] = useState<LearnerResponse | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const attemptsRef = useRef(1);
  const startedAtRef = useRef(new Date());

  const handleRecording = useCallback(
    async (recording: Recording) => {
      if (!transcribe) return;

      setTranscribing(true);
      announce('Listening to your answer');

      try {
        const result = await transcribe(recording.wav, block.id);
        const response = buildResponse({
          block,
          profile,
          sessionId,
          inputMode: 'speech',
          text: result.text,
          startedAt: startedAtRef.current,
          attempts: attemptsRef.current,
          confidence: result.confidence,
          raw: {
            ...(result.audioRef ? { audio_ref: result.audioRef } : {}),
            asr_text: result.text,
            ...(result.model ? { asr_model: result.model } : {}),
          },
        });

        if (needsConfirmation(response)) {
          // Not an error and not a failure — uncertainty we refuse to resolve
          // on the learner's behalf.
          setPending(response);
          announce('Please check what I heard');
        } else {
          onResponse(response);
          attemptsRef.current += 1;
          startedAtRef.current = new Date();
          announce('Answer sent');
        }
      } catch {
        setError('Your answer could not be processed. Please try again, or type it instead.');
      } finally {
        setTranscribing(false);
      }
    },
    [announce, block, onResponse, profile, sessionId, transcribe],
  );

  const recorder = useAudioRecorder({ onRecording: handleRecording });

  const available = speech.asr && typeof transcribe === 'function' && supportsRecording();

  if (loaded && !available) {
    return <SpeechUnavailable reason={speech.asr ? 'browser' : 'service'} />;
  }

  if (pending) {
    return (
      <ConfirmHeard
        response={pending}
        onAccept={() => {
          onResponse(pending);
          setPending(null);
          attemptsRef.current += 1;
          startedAtRef.current = new Date();
          announce('Answer sent');
        }}
        onRetry={() => {
          setPending(null);
          announce('Try again');
        }}
      />
    );
  }

  const recording = recorder.state === 'recording';
  const busy = transcribing || recorder.state === 'processing';

  return (
    <div data-input-mode="speech" data-state={recorder.state}>
      <p style={{ margin: '0 0 var(--space-sm, 0.5rem)', color: 'var(--colour-fg-muted)' }}>
        Say: <strong style={{ color: 'var(--colour-fg)' }}>{block.canonical_text}</strong>
      </p>
      <p style={{ margin: '0 0 var(--space-md, 1rem)', color: 'var(--colour-fg-muted)' }}>
        Take as long as you need. Recording does not stop on its own.
      </p>

      {recorder.quality && <InputQualityMeter quality={recorder.quality} />}

      <div style={{ marginTop: 'var(--space-md, 1rem)', display: 'flex', gap: 'var(--space-sm, 0.5rem)', flexWrap: 'wrap' }}>
        {recorder.state === 'idle' || recorder.state === 'error' ? (
          <button
            type="button"
            onClick={() => void recorder.check()}
            disabled={disabled}
            style={submitButtonStyle(Boolean(disabled))}
          >
            Check my microphone
          </button>
        ) : recording ? (
          <button type="button" onClick={recorder.stop} style={submitButtonStyle(false)}>
            Stop recording
          </button>
        ) : (
          <button
            type="button"
            onClick={recorder.start}
            // Blocked only when the microphone is genuinely dead — a noisy or
            // quiet room is a hint, never a barrier.
            disabled={disabled || busy || recorder.quality?.canRecord === false}
            style={submitButtonStyle(
              Boolean(disabled) || busy || recorder.quality?.canRecord === false,
            )}
          >
            {busy ? 'Working…' : 'Start recording'}
          </button>
        )}
      </div>

      {recording && (
        // Elapsed time is shown because a learner should know they are being
        // recorded — it counts up, never down, and nothing happens when it
        // reaches any particular number.
        <p role="status" style={{ marginTop: 'var(--space-sm, 0.5rem)' }}>
          Recording — {Math.floor(recorder.elapsedSeconds)} seconds
        </p>
      )}

      {(error ?? recorder.error) && (
        <p role="alert" style={{ marginTop: 'var(--space-sm, 0.5rem)' }}>
          {error ?? recorder.error}
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
      {/* Framed as the tool's uncertainty, never the learner's mistake.
          "I heard", not "you said". */}
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
