/**
 * Microphone capture.
 *
 * Browser glue only — the maths lives in wav.ts and quality.ts so it can be
 * tested without a Web Audio implementation.
 *
 * THERE IS NO MAXIMUM RECORDING LENGTH. Not a long one, none. A learner with
 * dysarthria or a stammer may need thirty seconds for one sentence, and a
 * recorder that cuts them off mid-word is a recorder they will not use twice
 * (Ethics E6).
 *
 * The only automatic stop is a long silence, it is generous, and it is
 * switchable off entirely from the profile.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { analyse, assess, trimSilence, type QualityAssessment } from './quality';
import { TARGET_SAMPLE_RATE, encodeWav, resample, toMono } from './wav';

export type RecorderState = 'idle' | 'checking' | 'ready' | 'recording' | 'processing' | 'error';

export interface Recording {
  wav: Blob;
  durationSeconds: number;
  sampleRate: number;
}

export interface RecorderOptions {
  /**
   * Stop after this many seconds of continuous silence. Generous by default,
   * and `null` disables it. This is a convenience for people who cannot easily
   * press stop, never a limit on how long someone may take.
   */
  silenceStopSeconds?: number | null;
  onRecording?: (recording: Recording) => void;
}

interface RecorderApi {
  state: RecorderState;
  quality: QualityAssessment | null;
  elapsedSeconds: number;
  error: string | null;
  /** Open the microphone and start measuring the room. Does not record yet. */
  check: () => Promise<void>;
  start: () => void;
  stop: () => void;
  cancel: () => void;
}

const SILENCE_LEVEL = 0.01;

export function useAudioRecorder(options: RecorderOptions = {}): RecorderApi {
  const { silenceStopSeconds = 8, onRecording } = options;

  const [state, setState] = useState<RecorderState>('idle');
  const [quality, setQuality] = useState<QualityAssessment | null>(null);
  const [elapsedSeconds, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const noiseFloorRef = useRef<number | null>(null);
  const startedAtRef = useRef<number>(0);
  const silentSinceRef = useRef<number | null>(null);
  const frameRef = useRef<number | null>(null);

  const teardown = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;

    recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    streamRef.current?.getTracks().forEach((track) => track.stop());
    void contextRef.current?.close();

    recorderRef.current = null;
    streamRef.current = null;
    contextRef.current = null;
    analyserRef.current = null;
  }, []);

  useEffect(() => teardown, [teardown]);

  // ── monitoring loop ────────────────────────────────────────────────────────

  const monitor = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const buffer = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(buffer);

    const reading = analyse(buffer, noiseFloorRef.current);
    setQuality(assess(reading));

    if (recorderRef.current?.state === 'recording') {
      setElapsed((Date.now() - startedAtRef.current) / 1000);

      if (silenceStopSeconds !== null) {
        if (reading.level < SILENCE_LEVEL) {
          silentSinceRef.current ??= Date.now();
          if (Date.now() - silentSinceRef.current > silenceStopSeconds * 1000) {
            recorderRef.current.stop();
          }
        } else {
          silentSinceRef.current = null;
        }
      }
    }

    frameRef.current = requestAnimationFrame(monitor);
  }, [silenceStopSeconds]);

  // ── open the microphone and measure the room ───────────────────────────────

  const check = useCallback(async () => {
    setError(null);
    setState('checking');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);

      streamRef.current = stream;
      contextRef.current = context;
      analyserRef.current = analyser;

      // Measure room tone before the learner speaks. A noise floor measured
      // this way is far more reliable than trying to separate speech from noise
      // inside a single buffer, and it costs the learner nothing.
      await new Promise((resolve) => setTimeout(resolve, 400));
      const roomTone = new Float32Array(analyser.fftSize);
      analyser.getFloatTimeDomainData(roomTone);
      noiseFloorRef.current = analyse(roomTone).level || null;

      setState('ready');
      frameRef.current = requestAnimationFrame(monitor);
    } catch {
      setError('The microphone is not available. Check permissions, or answer another way.');
      setState('error');
    }
  }, [monitor]);

  // ── record ─────────────────────────────────────────────────────────────────

  const start = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;

    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    silentSinceRef.current = null;
    startedAtRef.current = Date.now();
    setElapsed(0);

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };

    recorder.onstop = async () => {
      setState('processing');
      try {
        const recording = await toWav(new Blob(chunksRef.current, { type: recorder.mimeType }));
        onRecording?.(recording);
        setState('ready');
      } catch {
        setError('That recording could not be processed. Please try again.');
        setState('error');
      }
    };

    recorder.start();
    recorderRef.current = recorder;
    setState('recording');
  }, [onRecording]);

  const stop = useCallback(() => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
  }, []);

  const cancel = useCallback(() => {
    teardown();
    setState('idle');
    setQuality(null);
    setElapsed(0);
  }, [teardown]);

  return { state, quality, elapsedSeconds, error, check, start, stop, cancel };
}

/**
 * Decode whatever the browser recorded and normalise it to 16 kHz mono WAV.
 *
 * `OfflineAudioContext` does the resampling, so the browser applies a proper
 * anti-aliasing filter rather than our linear interpolation. The helpers in
 * wav.ts are the fallback for environments without it.
 */
export async function toWav(blob: Blob): Promise<Recording> {
  const arrayBuffer = await blob.arrayBuffer();

  const context = new AudioContext();
  const decoded = await context.decodeAudioData(arrayBuffer);
  void context.close();

  const offline = new OfflineAudioContext(
    1,
    Math.ceil((decoded.duration * TARGET_SAMPLE_RATE) || 1),
    TARGET_SAMPLE_RATE,
  );
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();

  const rendered = await offline.startRendering();
  const mono = toMono([rendered.getChannelData(0)]);

  const resampled =
    rendered.sampleRate === TARGET_SAMPLE_RATE
      ? mono
      : resample(mono, rendered.sampleRate, TARGET_SAMPLE_RATE);

  const trimmed = trimSilence(resampled, TARGET_SAMPLE_RATE);

  return {
    wav: new Blob([encodeWav(trimmed, TARGET_SAMPLE_RATE)], { type: 'audio/wav' }),
    durationSeconds: trimmed.length / TARGET_SAMPLE_RATE,
    sampleRate: TARGET_SAMPLE_RATE,
  };
}
