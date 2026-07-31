/**
 * Audio format conversion — pure functions, no browser APIs.
 *
 * The speech pipeline requires **16 kHz mono PCM**, fixed. Inconsistent input
 * silently destroys every downstream metric: forced alignment drifts, GOP
 * posteriors shift, and speech-rate figures become meaningless. Most failures
 * in speech applications are capture failures, not model failures.
 *
 * Kept free of Web Audio so the maths is directly testable. The browser glue
 * lives in useAudioRecorder.ts.
 */

/** The one sample rate the speech service accepts. Not negotiable. */
export const TARGET_SAMPLE_RATE = 16_000;

/**
 * Average multi-channel audio down to mono.
 *
 * Averaging, not channel-picking: a learner using a stereo headset may be
 * louder on one side, and dropping a channel would halve their signal.
 */
export function toMono(channels: Float32Array[]): Float32Array {
  if (channels.length === 0) return new Float32Array(0);
  if (channels.length === 1) return channels[0]!;

  const length = channels[0]!.length;
  const mono = new Float32Array(length);

  for (let i = 0; i < length; i++) {
    let sum = 0;
    for (const channel of channels) sum += channel[i] ?? 0;
    mono[i] = sum / channels.length;
  }
  return mono;
}

/**
 * Resample by linear interpolation.
 *
 * Adequate when downsampling from 44.1/48 kHz to 16 kHz *after* the browser has
 * already low-pass filtered during decode. If we ever resample raw captured
 * audio we will need a proper windowed-sinc filter to avoid aliasing, which
 * would show up as spurious high-frequency energy in the prosody features.
 */
export function resample(
  input: Float32Array,
  fromRate: number,
  toRate: number = TARGET_SAMPLE_RATE,
): Float32Array {
  if (fromRate === toRate) return input;
  if (input.length === 0) return input;

  const ratio = fromRate / toRate;
  const outputLength = Math.floor(input.length / ratio);
  const output = new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i++) {
    const position = i * ratio;
    const index = Math.floor(position);
    const fraction = position - index;
    const current = input[index] ?? 0;
    const next = input[index + 1] ?? current;
    output[i] = current + (next - current) * fraction;
  }

  return output;
}

/**
 * Encode mono Float32 samples as a 16-bit PCM WAV.
 *
 * WAV rather than a compressed format on purpose: lossy codecs discard exactly
 * the spectral detail that pronunciation scoring depends on, and the artefacts
 * fall hardest on atypical speech, which is already at the edge of what the
 * codec was tuned for.
 */
export function encodeWav(
  samples: Float32Array,
  sampleRate: number = TARGET_SAMPLE_RATE,
): ArrayBuffer {
  const bytesPerSample = 2;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);

  const writeAscii = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };

  writeAscii(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * bytesPerSample, true);
  writeAscii(8, 'WAVE');

  writeAscii(12, 'fmt ');
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // format: PCM
  view.setUint16(22, 1, true); // channels: mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true); // byte rate
  view.setUint16(32, bytesPerSample, true); // block align
  view.setUint16(34, 16, true); // bits per sample

  writeAscii(36, 'data');
  view.setUint32(40, samples.length * bytesPerSample, true);

  let offset = 44;
  for (const sample of samples) {
    // Clamp before scaling: a value outside [-1, 1] would wrap around and turn
    // a loud syllable into a burst of noise.
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += bytesPerSample;
  }

  return buffer;
}

/** Round-trip helper for tests and for the offline queue. */
export function decodeWav(buffer: ArrayBuffer): { samples: Float32Array; sampleRate: number } {
  const view = new DataView(buffer);
  const sampleRate = view.getUint32(24, true);
  const dataLength = view.getUint32(40, true);
  const samples = new Float32Array(dataLength / 2);

  for (let i = 0; i < samples.length; i++) {
    const value = view.getInt16(44 + i * 2, true);
    samples[i] = value < 0 ? value / 0x8000 : value / 0x7fff;
  }

  return { samples, sampleRate };
}
