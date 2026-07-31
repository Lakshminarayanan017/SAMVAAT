/**
 * Indian Sign Language input.
 *
 * Serves P2 (Meena), whose first language is ISL.
 *
 * NOT YET IMPLEMENTED — the recogniser lands in M16. Rather than shipping a
 * control that silently does nothing, this states the position plainly and
 * points at the working alternative. A learner discovering a dead button is
 * worse than a learner reading one honest sentence.
 *
 * The commitment recorded here for when M16 lands (Ethics E4, enforced by
 * tests/e2e/no-video-egress.spec.ts):
 *
 *   Camera frames are processed entirely on-device via MediaPipe Holistic.
 *   Only the predicted sign label leaves the client. No video frame is
 *   transmitted, stored or logged, at any quality, for any purpose, ever.
 */
import type { InputAdapterProps } from '../registry';

export function SignInput({ block }: InputAdapterProps) {
  const alternatives = block.interaction.accepted_input_modes.filter((mode) => mode !== 'sign');

  return (
    <div data-input-mode="sign" data-state="unavailable">
      <p style={{ margin: 0 }}>Signing to the camera is not ready yet.</p>

      <p style={{ margin: 'var(--space-sm, 0.5rem) 0 0', color: 'var(--colour-fg-muted)' }}>
        {alternatives.length > 0
          ? 'You can still complete this lesson — type your answer, or choose from the options.'
          : 'You can still complete this lesson another way.'}
      </p>

      <p style={{ margin: 'var(--space-sm, 0.5rem) 0 0', color: 'var(--colour-fg-muted)' }}>
        When it arrives, your camera will be read on this device only. Video never leaves your
        phone.
      </p>
    </div>
  );
}
