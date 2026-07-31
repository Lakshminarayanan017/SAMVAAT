/**
 * Runtime helpers shared by the client and any Node tooling.
 *
 * These encode contract *behaviour* that a JSON Schema cannot express — the
 * fallback chains, and the confidence threshold below which a transcription is
 * never treated as a wrong answer.
 */
import type { ContentBlock, CommunicationAbilityProfile, OutputChannel } from '../generated/types.js';

/**
 * Below this, `canonical_text` is too unreliable to score.
 *
 * The client asks the learner to confirm what they meant instead of marking the
 * answer wrong. Scoring a bad transcription as a bad answer is precisely how
 * mainstream speech tools fail people with atypical speech (ADR-0002).
 */
export const CONFIDENCE_CONFIRM_THRESHOLD = 0.75;

/**
 * Deterministic degradation when a representation is missing.
 *
 * Missing representations are a build-time warning from the content validator,
 * never a runtime surprise — but the chain guarantees a learner always gets
 * *something* rather than an empty screen.
 */
export const FALLBACK_CHAIN: Record<OutputChannel, OutputChannel[]> = {
  isl: ['captioned_text', 'easy_read'],
  pictograph: ['easy_read', 'captioned_text'],
  easy_read: ['captioned_text'],
  audio: ['captioned_text'],
  captioned_text: [],
};

/** Does this block carry a usable representation for the given channel? */
export function hasRepresentation(block: ContentBlock, channel: OutputChannel): boolean {
  const r = block.representations ?? {};
  switch (channel) {
    case 'audio':
      return Boolean(r.audio_native ?? r.audio_slow);
    case 'captioned_text':
      return Boolean(r.caption ?? block.canonical_text);
    case 'isl':
      return Boolean(r.isl_clip);
    case 'pictograph':
      return Boolean(r.pictographs?.length);
    case 'easy_read':
      return Boolean(r.easy_read);
  }
}

/**
 * The channel the router should actually render, walking the fallback chain.
 * Returns `captioned_text` as the floor — every block has `canonical_text`.
 */
export function resolveChannel(block: ContentBlock, preferred: OutputChannel): OutputChannel {
  if (hasRepresentation(block, preferred)) return preferred;
  for (const next of FALLBACK_CHAIN[preferred]) {
    if (hasRepresentation(block, next)) return next;
  }
  return 'captioned_text';
}

/**
 * The channels to render for a profile: the primary, plus every supporting
 * channel the block can actually satisfy. A learner using Easy-Read typically
 * gets pictographs and narrated audio alongside it, simultaneously.
 */
export function channelsFor(
  block: ContentBlock,
  profile: CommunicationAbilityProfile,
): { primary: OutputChannel; support: OutputChannel[] } {
  const [first, ...rest] = profile.output_channels;
  return {
    primary: resolveChannel(block, first),
    support: rest.filter((c) => hasRepresentation(block, c)),
  };
}

/** Can this learner answer this block at all? Guards against authoring mistakes. */
export function canRespond(block: ContentBlock, profile: CommunicationAbilityProfile): boolean {
  return block.interaction.accepted_input_modes.some((m) => profile.input_channels.includes(m));
}
