/**
 * Input quality analysis — pure functions over sample buffers.
 *
 * This runs BEFORE recording starts, and it is the highest-value hundred lines
 * in the speech half of the product. A learner who records ten attempts in a
 * noisy room gets ten bad scores and concludes the app does not understand
 * them — when the real problem was a microphone two metres away.
 *
 * Catching that before they speak is worth more than any model improvement.
 *
 * IMPORTANT: quality is measured against the ROOM, never against the speaker.
 * There is no check anywhere in this file for "clear enough" speech, and there
 * must never be. We are asking "can the microphone hear you?", not "do you
 * speak well enough?" (Ethics E1).
 */

/** Loud enough that clipping is likely; the signal is distorted. */
const CLIPPING_THRESHOLD = 0.98;

/** Fraction of clipped samples above which we warn. */
const CLIPPING_RATIO_LIMIT = 0.005;

export interface QualityReading {
  /** RMS level, 0-1. */
  level: number;
  /** Peak absolute sample, 0-1. */
  peak: number;
  /** Fraction of samples at or beyond the clipping threshold. */
  clippedRatio: number;
  /** Estimated signal-to-noise ratio in dB. Null until a noise floor is known. */
  snrDb: number | null;
}

export type QualityVerdict = 'good' | 'quiet' | 'loud' | 'noisy' | 'silent';

export interface QualityAssessment {
  verdict: QualityVerdict;
  reading: QualityReading;
  /** Learner-facing, plain language, never blaming the learner. */
  message: string;
  /** False only when recording would be pointless, not merely imperfect. */
  canRecord: boolean;
}

export function rms(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (const sample of samples) sum += sample * sample;
  return Math.sqrt(sum / samples.length);
}

export function peak(samples: Float32Array): number {
  let highest = 0;
  for (const sample of samples) {
    const magnitude = Math.abs(sample);
    if (magnitude > highest) highest = magnitude;
  }
  return highest;
}

export function clippedRatio(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let clipped = 0;
  for (const sample of samples) {
    if (Math.abs(sample) >= CLIPPING_THRESHOLD) clipped++;
  }
  return clipped / samples.length;
}

/**
 * Signal-to-noise ratio in dB, given a measured noise floor.
 *
 * The caller supplies the noise floor from a second of room tone captured
 * before the learner speaks — that is far more reliable than trying to separate
 * speech from noise inside a single buffer, and it costs the learner nothing.
 */
export function snr(signalRms: number, noiseRms: number): number | null {
  if (noiseRms <= 0 || signalRms <= 0) return null;
  return 20 * Math.log10(signalRms / noiseRms);
}

export function analyse(samples: Float32Array, noiseFloor: number | null = null): QualityReading {
  const level = rms(samples);
  return {
    level,
    peak: peak(samples),
    clippedRatio: clippedRatio(samples),
    snrDb: noiseFloor === null ? null : snr(level, noiseFloor),
  };
}

/**
 * Turn a reading into a verdict and a sentence a learner can act on.
 *
 * Every message names something in the environment — the room, the distance,
 * the microphone. None of them refers to how the person speaks.
 */
export function assess(reading: QualityReading): QualityAssessment {
  const { level, clippedRatio: clipped, snrDb } = reading;

  if (level < 0.005) {
    return {
      verdict: 'silent',
      reading,
      message: 'I cannot hear the microphone. Check it is switched on and allowed.',
      // The one case where recording is genuinely pointless.
      canRecord: false,
    };
  }

  if (clipped > CLIPPING_RATIO_LIMIT || level > 0.7) {
    return {
      verdict: 'loud',
      reading,
      message: 'That is very loud. Try moving the microphone a little further away.',
      canRecord: true,
    };
  }

  if (snrDb !== null && snrDb < 10) {
    return {
      verdict: 'noisy',
      reading,
      message: 'It is noisy here. A quieter place will help, but you can carry on.',
      canRecord: true,
    };
  }

  if (level < 0.02) {
    return {
      verdict: 'quiet',
      reading,
      message: 'That is quite quiet. Try moving a little closer to the microphone.',
      canRecord: true,
    };
  }

  return {
    verdict: 'good',
    reading,
    message: 'The microphone is working well.',
    canRecord: true,
  };
}

/**
 * Trim leading and trailing silence, keeping padding.
 *
 * The padding is not cosmetic. A stammering block often begins with a silent
 * closure before the sound arrives; trimming tightly would delete the exact
 * event the disfluency detector needs to see, and would also clip the onset
 * that pronunciation scoring measures.
 */
export function trimSilence(
  samples: Float32Array,
  sampleRate: number,
  threshold = 0.01,
  paddingMs = 300,
): Float32Array {
  const padding = Math.floor((paddingMs / 1000) * sampleRate);

  let start = 0;
  while (start < samples.length && Math.abs(samples[start]!) < threshold) start++;

  let end = samples.length - 1;
  while (end > start && Math.abs(samples[end]!) < threshold) end--;

  // All silence: hand back the original rather than an empty buffer, so the
  // caller can tell the learner nothing was heard instead of failing oddly.
  if (start >= end) return samples;

  return samples.slice(Math.max(0, start - padding), Math.min(samples.length, end + padding + 1));
}
