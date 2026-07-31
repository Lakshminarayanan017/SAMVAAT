/**
 * The Communication Ability Profile, in React context.
 *
 * Everything downstream reads the profile from here rather than receiving it as
 * a prop. That is deliberate: if the profile were a prop, a developer could
 * forget to pass it, and a screen would silently render in the default modality
 * for a learner who cannot use it. Context makes forgetting impossible.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { CommunicationAbilityProfile } from '@samvaad/contracts';

import { applyTheme, type ColourScheme, type ContrastTheme } from '@/design-system/tokens';

interface ProfileContextValue {
  profile: CommunicationAbilityProfile;
  /** Creates a new profile version rather than mutating — progress data is only comparable within a version. */
  updateProfile: (patch: Partial<CommunicationAbilityProfile>) => void;
}

const ProfileContext = createContext<ProfileContextValue | null>(null);

/**
 * The profile a learner gets before onboarding has run.
 *
 * Chosen so the first screen is usable by the widest possible range of people:
 * captions plus audio, standard text, every input mode accepted. Onboarding
 * (M1) narrows it; it must never be *widened* silently at runtime.
 */
export const DEFAULT_PROFILE: CommunicationAbilityProfile = {
  user_id: 'guest',
  version: 1,
  input_channels: ['text', 'speech', 'aac', 'switch'],
  output_channels: ['captioned_text', 'audio'],
  text_complexity: 'standard',
  speech_status: 'undeclared',
  primary_language: 'en-IN',
  presentation: {
    audio_rate: 1.0,
    contrast_theme: 'standard',
    colour_scheme: 'system',
    motion_reduced: false,
    target_size_px: 44,
    captions_enabled: true,
    one_step_per_screen: false,
  },
};

export function ProfileProvider({
  children,
  initialProfile = DEFAULT_PROFILE,
}: {
  children: ReactNode;
  initialProfile?: CommunicationAbilityProfile;
}) {
  const [profile, setProfile] = useState(initialProfile);

  const updateProfile = useCallback((patch: Partial<CommunicationAbilityProfile>) => {
    setProfile((current) => ({
      ...current,
      ...patch,
      // A profile change is a new version, never an edit in place.
      version: current.version + 1,
    }));
  }, []);

  // Keep the rendered theme in step with the profile, so a learner switching to
  // high contrast mid-session sees it immediately rather than on next reload.
  useEffect(() => {
    applyTheme({
      colourScheme: resolveColourScheme(profile.presentation?.colour_scheme),
      contrastTheme: (profile.presentation?.contrast_theme ?? 'standard') as ContrastTheme,
      targetSizePx: profile.presentation?.target_size_px ?? 44,
      motionReduced: profile.presentation?.motion_reduced ?? false,
    });
  }, [profile]);

  const value = useMemo(() => ({ profile, updateProfile }), [profile, updateProfile]);

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile(): ProfileContextValue {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error(
      'useProfile must be used inside <ProfileProvider>. Rendering learning content ' +
        'without a Communication Ability Profile is never correct — there would be no ' +
        'way to know which modality the learner can use.',
    );
  }
  return context;
}

/** 'system' follows the OS setting; anything else is the learner's explicit choice. */
function resolveColourScheme(preference: string | undefined | null): ColourScheme {
  if (preference === 'light' || preference === 'dark') return preference;
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
