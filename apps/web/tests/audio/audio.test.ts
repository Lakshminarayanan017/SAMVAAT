/**
 * Audio format conversion and input-quality analysis.
 *
 * These are the highest-value tests in the speech half of the client. Most
 * speech-application failures are capture failures, not model failures — and a
 * capture bug is invisible until it has already produced a hundred bad scores
 * for a learner who will reasonably conclude the app does not understand them.
 */
import { describe, expect, it } from 'vitest';

import {
  TARGET_SAMPLE_RATE,
  decodeWav,
  encodeWav,
  resample,
  toMono,
} from '@/audio/wav';
import {
  analyse,
  assess,
  clippedRatio,
  peak,
  rms,
  snr,
  trimSilence,
} from '@/audio/quality';

/** A sine wave, the standard test signal. */
function tone(seconds: number, frequency = 440, sampleRate = TARGET_SAMPLE_RATE, amplitude = 0.5) {
  const samples = new Float32Array(Math.floor(seconds * sampleRate));
  for (let i = 0; i < samples.length; i++) {
    samples[i] = amplitude * Math.sin((2 * Math.PI * frequency * i) / sampleRate);
  }
  return samples;
}

function silence(seconds: number, sampleRate = TARGET_SAMPLE_RATE) {
  return new Float32Array(Math.floor(seconds * sampleRate));
}

function concat(...parts: Float32Array[]) {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Float32Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

// ── Format conversion ─────────────────────────────────────────────────────────

describe('toMono', () => {
  it('averages channels rather than dropping one', () => {
    // A learner on a stereo headset may be much louder on one side; picking a
    // channel would halve their signal.
    const left = new Float32Array([1, 1, 1]);
    const right = new Float32Array([0, 0, 0]);
    expect([...toMono([left, right])]).toEqual([0.5, 0.5, 0.5]);
  });

  it('passes a single channel through untouched', () => {
    const mono = new Float32Array([0.1, 0.2]);
    expect(toMono([mono])).toBe(mono);
  });

  it('handles an empty input', () => {
    expect(toMono([]).length).toBe(0);
  });
});

describe('resample', () => {
  it('is a no-op at the same rate', () => {
    const input = tone(0.1);
    expect(resample(input, TARGET_SAMPLE_RATE, TARGET_SAMPLE_RATE)).toBe(input);
  });

  it('produces the expected length when downsampling', () => {
    const input = tone(1, 440, 48_000);
    const output = resample(input, 48_000, TARGET_SAMPLE_RATE);
    // One second in, one second out.
    expect(output.length).toBeCloseTo(TARGET_SAMPLE_RATE, -2);
  });

  it('preserves signal amplitude', () => {
    const output = resample(tone(0.5, 200, 48_000, 0.5), 48_000, TARGET_SAMPLE_RATE);
    expect(peak(output)).toBeGreaterThan(0.4);
    expect(peak(output)).toBeLessThanOrEqual(0.51);
  });

  it('does not choke on an empty buffer', () => {
    expect(resample(new Float32Array(0), 48_000).length).toBe(0);
  });
});

describe('WAV encoding', () => {
  it('writes a valid RIFF/WAVE header at 16 kHz mono 16-bit', () => {
    const buffer = encodeWav(tone(0.1));
    const view = new DataView(buffer);
    const ascii = (offset: number, length: number) =>
      String.fromCharCode(...new Uint8Array(buffer, offset, length));

    expect(ascii(0, 4)).toBe('RIFF');
    expect(ascii(8, 4)).toBe('WAVE');
    expect(view.getUint16(20, true)).toBe(1); // PCM
    expect(view.getUint16(22, true)).toBe(1); // mono
    expect(view.getUint32(24, true)).toBe(TARGET_SAMPLE_RATE);
    expect(view.getUint16(34, true)).toBe(16); // bit depth
  });

  it('round-trips samples within 16-bit precision', () => {
    const original = tone(0.05);
    const { samples, sampleRate } = decodeWav(encodeWav(original));

    expect(sampleRate).toBe(TARGET_SAMPLE_RATE);
    expect(samples.length).toBe(original.length);
    for (let i = 0; i < original.length; i++) {
      expect(samples[i]).toBeCloseTo(original[i]!, 4);
    }
  });

  it('clamps out-of-range samples instead of wrapping them', () => {
    // Without clamping, an overshooting sample wraps to the opposite extreme
    // and turns a loud syllable into a burst of noise.
    const { samples } = decodeWav(encodeWav(new Float32Array([2, -2])));
    expect(samples[0]).toBeCloseTo(1, 3);
    expect(samples[1]).toBeCloseTo(-1, 3);
  });
});

// ── Quality analysis ──────────────────────────────────────────────────────────

describe('level measurement', () => {
  it('reports rms below peak for a sine wave', () => {
    const signal = tone(0.2, 440, TARGET_SAMPLE_RATE, 0.5);
    expect(rms(signal)).toBeCloseTo(0.5 / Math.SQRT2, 2);
    expect(peak(signal)).toBeCloseTo(0.5, 2);
  });

  it('reports zero for silence', () => {
    expect(rms(silence(0.1))).toBe(0);
    expect(peak(silence(0.1))).toBe(0);
  });

  it('detects clipping', () => {
    expect(clippedRatio(tone(0.1, 440, TARGET_SAMPLE_RATE, 0.5))).toBe(0);
    expect(clippedRatio(new Float32Array([1, 1, 0, 0]))).toBeCloseTo(0.5, 5);
  });

  it('computes SNR in dB, and returns null without a noise floor', () => {
    // Ten times the amplitude is 20 dB by definition.
    expect(snr(0.1, 0.01)).toBeCloseTo(20, 5);
    expect(snr(0.1, 0)).toBeNull();
  });
});

describe('quality verdicts', () => {
  it('passes a good signal', () => {
    expect(assess(analyse(tone(0.2, 440, TARGET_SAMPLE_RATE, 0.2))).verdict).toBe('good');
  });

  it('reports a dead microphone and blocks recording', () => {
    const result = assess(analyse(silence(0.2)));
    expect(result.verdict).toBe('silent');
    expect(result.canRecord).toBe(false);
  });

  it('warns about a loud or clipping signal but still allows recording', () => {
    const result = assess(analyse(tone(0.2, 440, TARGET_SAMPLE_RATE, 0.99)));
    expect(result.verdict).toBe('loud');
    expect(result.canRecord).toBe(true);
  });

  it('warns about a quiet signal', () => {
    expect(assess(analyse(tone(0.2, 440, TARGET_SAMPLE_RATE, 0.015))).verdict).toBe('quiet');
  });

  it('warns about a noisy room using the measured noise floor', () => {
    const speech = tone(0.2, 440, TARGET_SAMPLE_RATE, 0.1);
    // A noise floor close to the signal is a poor SNR.
    expect(assess(analyse(speech, 0.05)).verdict).toBe('noisy');
  });

  it('never blocks recording for anything except a dead microphone', () => {
    const signals = [
      tone(0.2, 440, TARGET_SAMPLE_RATE, 0.99),
      tone(0.2, 440, TARGET_SAMPLE_RATE, 0.015),
      tone(0.2, 440, TARGET_SAMPLE_RATE, 0.2),
    ];
    for (const signal of signals) {
      expect(assess(analyse(signal)).canRecord).toBe(true);
    }
  });

  it('describes the room, never the speaker', () => {
    /**
     * Ethics E1. This module asks "can the microphone hear you?", never "do you
     * speak well enough?". A quality check that comments on the person is a
     * judgement, and it is exactly the judgement this product exists to remove.
     */
    const messages = [
      assess(analyse(silence(0.1))).message,
      assess(analyse(tone(0.2, 440, TARGET_SAMPLE_RATE, 0.99))).message,
      assess(analyse(tone(0.2, 440, TARGET_SAMPLE_RATE, 0.015))).message,
      assess(analyse(tone(0.2, 440, TARGET_SAMPLE_RATE, 0.1), 0.05)).message,
    ];

    const banned = [
      'unclear', 'mumbl', 'slur', 'speak more clearly', 'pronounce',
      'articulat', 'your speech', 'you are too', 'louder please',
    ];

    for (const message of messages) {
      const lower = message.toLowerCase();
      for (const word of banned) {
        expect(lower, `"${message}" comments on the speaker`).not.toContain(word);
      }
    }
  });
});

describe('trimSilence', () => {
  it('removes leading and trailing silence', () => {
    const original = concat(silence(1), tone(0.5), silence(1));
    const trimmed = trimSilence(original, TARGET_SAMPLE_RATE);
    expect(trimmed.length).toBeLessThan(original.length);
  });

  it('keeps padding around the speech', () => {
    /**
     * The padding is not cosmetic. A stammering block often begins with a
     * silent closure before any sound arrives; trimming tightly would delete
     * the exact event the disfluency detector needs to see.
     */
    const speech = tone(0.5);
    const trimmed = trimSilence(concat(silence(1), speech, silence(1)), TARGET_SAMPLE_RATE);

    const paddingSamples = 0.3 * TARGET_SAMPLE_RATE;
    expect(trimmed.length).toBeGreaterThan(speech.length + paddingSamples);
  });

  it('returns the original when everything is silence', () => {
    // So the caller can say "I did not hear anything" rather than failing oddly
    // on an empty buffer.
    const original = silence(1);
    expect(trimSilence(original, TARGET_SAMPLE_RATE)).toBe(original);
  });

  it('leaves speech that fills the whole buffer alone', () => {
    const speech = tone(1);
    expect(trimSilence(speech, TARGET_SAMPLE_RATE).length).toBe(speech.length);
  });
});
