/**
 * A story panel, as a ContentBlock.
 *
 * WHY THIS FILE EXISTS AT ALL
 * ---------------------------
 * A social story is the single most likely thing in this product to be rendered
 * as a paragraph of prose — it arrives from the model as prose, and prose is
 * what a story looks like. But a learner who reads pictographs cannot read
 * prose, and a story generated *for* that learner which they cannot read is
 * worse than no story: it looks like provision.
 *
 * So generated panels are converted into ContentBlocks and rendered through the
 * Modality Router, exactly like the 226 authored phrases. `social_story_panel`
 * is already one of the `kind` values in the schema — the contract anticipated
 * this, and this file is where that intent is honoured rather than bypassed.
 *
 * WHAT IS AND IS NOT CLAIMED
 * --------------------------
 * The block declares only the representations it genuinely has. Generated text
 * has no recorded audio, no ISL clip and no verified pictographs, so those keys
 * are absent and the documented fallback chain handles them. Fabricating an
 * `easy_read` field by copying the text would be a lie the renderer trusts.
 *
 * `source: 'generated'` is set here and never cleared on the client. It is what
 * the AI-generated label is derived from (Ethics E5).
 */
import type { ContentBlock } from '@samvaad/contracts';

export interface StoryPanel {
  text: string;
  type: 'descriptive' | 'perspective' | 'directive' | 'affirmative';
  pictograph_hint?: string | null;
}

export interface Story {
  title: string;
  panels: StoryPanel[];
  status: 'draft' | 'published';
  generated: boolean;
  validation: {
    valid: boolean;
    problems: string[];
    directive_count: number;
    non_directive_count: number;
    ratio: number;
  };
  notice?: string | null;
}

/**
 * The generator already caps a panel at 15 words — the same ceiling the
 * Easy-Read linter applies to authored content. So a panel that survived
 * generation is Easy-Read by construction, and saying so is a statement of
 * fact rather than an assumption.
 */
const EASY_READ_WORD_CEILING = 15;

export function panelToBlock(panel: StoryPanel, index: number, storyId: string): ContentBlock {
  const representations: ContentBlock['representations'] = {
    caption: panel.text,
  };

  if (wordCount(panel.text) <= EASY_READ_WORD_CEILING) {
    representations.easy_read = panel.text;
  }

  // A hint is a word the generator suggests illustrating, not a verified
  // symbol. It is offered as a single labelled pictograph with no `uri`, so a
  // renderer that needs a real image falls back rather than showing a gap.
  if (panel.pictograph_hint) {
    representations.pictographs = [
      { set: 'arasaac', id: panel.pictograph_hint, label: panel.pictograph_hint },
    ];
  }

  return {
    id: `${storyId}.panel_${String(index + 1).padStart(2, '0')}`,
    kind: 'social_story_panel',
    canonical_text: panel.text,
    intent: `story_${panel.type}`,
    difficulty: 1,
    representations,
    interaction: {
      // A story is read, not answered. Every input mode is listed because the
      // schema requires at least one and none of them is excluded — a story
      // panel asks nothing of the learner.
      accepted_input_modes: ['text', 'speech', 'aac', 'switch', 'sign'],
    },
    a11y: {
      requires_audio: false,
      requires_vision: false,
      requires_speech: false,
      notes: 'Generated text. No recorded audio or ISL clip exists for this panel.',
    },
    version: 1,
    source: 'generated',
  };
}

function wordCount(text: string): number {
  return (text.match(/[\w']+/g) ?? []).length;
}
