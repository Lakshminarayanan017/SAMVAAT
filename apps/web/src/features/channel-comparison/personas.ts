/**
 * The five personas as runnable Communication Ability Profiles.
 *
 * These mirror docs/PERSONAS.md exactly. They are used by the comparison view
 * and by the persona walkthrough suite, so there is one definition rather than
 * a demo copy that drifts from the tested one.
 */
import type { CommunicationAbilityProfile } from '@samvaad/contracts';

export interface Persona {
  id: string;
  name: string;
  disability: string;
  profile: CommunicationAbilityProfile;
}

export const PERSONAS: Persona[] = [
  {
    id: 'P1',
    name: 'Ravi',
    disability: 'Low vision (~10% residual)',
    profile: {
      user_id: 'persona-p1',
      version: 1,
      input_channels: ['speech', 'text'],
      output_channels: ['audio', 'captioned_text'],
      text_complexity: 'standard',
      speech_status: 'typical',
      presentation: { contrast_theme: 'high_contrast', target_size_px: 56, audio_rate: 1.0 },
    } as CommunicationAbilityProfile,
  },
  {
    id: 'P2',
    name: 'Meena',
    disability: 'Profoundly Deaf, ISL first language',
    profile: {
      user_id: 'persona-p2',
      version: 1,
      input_channels: ['text', 'sign'],
      output_channels: ['isl', 'captioned_text'],
      text_complexity: 'standard',
      speech_status: 'nonverbal',
      presentation: { captions_enabled: true },
    } as CommunicationAbilityProfile,
  },
  {
    id: 'P3',
    name: 'Arjun',
    disability: 'Cerebral palsy — dysarthric speech, limited motor control',
    profile: {
      user_id: 'persona-p3',
      version: 1,
      input_channels: ['speech', 'switch', 'text'],
      output_channels: ['audio', 'captioned_text'],
      text_complexity: 'standard',
      speech_status: 'atypical',
      presentation: { contrast_theme: 'high_contrast', target_size_px: 88, motion_reduced: true },
      interaction: {
        switch_scanning: { enabled: true, switch_count: 2, dwell_ms: 1800, scan_mode: 'row_column' },
      },
    } as CommunicationAbilityProfile,
  },
  {
    id: 'P4',
    name: 'Fatima',
    disability: 'Intellectual disability (mild)',
    profile: {
      user_id: 'persona-p4',
      version: 1,
      input_channels: ['aac', 'speech'],
      output_channels: ['easy_read', 'pictograph', 'audio'],
      text_complexity: 'easy_read',
      speech_status: 'typical',
      presentation: { audio_rate: 0.8, target_size_px: 64, one_step_per_screen: true },
    } as CommunicationAbilityProfile,
  },
  {
    id: 'P5',
    name: 'Karthik',
    disability: 'Stammer (moderate–severe)',
    profile: {
      user_id: 'persona-p5',
      version: 1,
      input_channels: ['speech', 'text'],
      output_channels: ['captioned_text', 'audio'],
      text_complexity: 'standard',
      speech_status: 'atypical',
      // Fluency is down-weighted and intelligibility raised, so a stammer cannot
      // depress the score (ADR-0003). Visible to the learner, never hidden.
      scoring_weights: {
        intelligibility: 0.4,
        pronunciation: 0.15,
        pace: 0.05,
        fluency: 0.05,
        confidence: 0.35,
      },
    } as CommunicationAbilityProfile,
  },
];
