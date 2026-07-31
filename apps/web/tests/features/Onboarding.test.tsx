/**
 * Onboarding.
 *
 * The four-door screen has to work for someone we know nothing about — who may
 * not see it, hear it, read it well, or use a mouse. These tests check the
 * properties that make that possible, not the pixels.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { DOORS, FourDoorScreen, SPOKEN_INTRO } from '@/features/onboarding/FourDoorScreen';
import { DOOR_PROFILE, OnboardingFlow, detectPreferences } from '@/features/onboarding/OnboardingFlow';

function renderFlow(onComplete = vi.fn()) {
  render(
    <AnnouncerProvider>
      <OnboardingFlow onComplete={onComplete} />
    </AnnouncerProvider>,
  );
  return { onComplete, user: userEvent.setup() };
}

describe('the four-door screen', () => {
  beforeEach(() => {
    vi.stubGlobal('speechSynthesis', { speak: vi.fn(), cancel: vi.fn() });
    vi.stubGlobal(
      'SpeechSynthesisUtterance',
      class {
        constructor(public text: string) {}
        rate = 1;
        onend: (() => void) | null = null;
        onerror: (() => void) | null = null;
      },
    );
  });

  it('offers exactly four ways in', () => {
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={vi.fn()} />
      </AnnouncerProvider>,
    );

    const list = screen.getByRole('list');
    expect(within(list).getAllByRole('button')).toHaveLength(4);
  });

  it('uses real buttons, so keyboard, switch and voice control all work', () => {
    /**
     * A styled div would need keyboard handling, focus management, ARIA and
     * voice-control naming rebuilt by hand — and one of them would be missed.
     */
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={vi.fn()} />
      </AnnouncerProvider>,
    );

    for (const door of DOORS) {
      expect(screen.getByRole('button', { name: new RegExp(door.label, 'i') })).toBeInTheDocument();
    }
  });

  it('carries each choice as text, not only as a symbol', () => {
    /** The emoji is decorative; assistive tech must get the words. */
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={vi.fn()} />
      </AnnouncerProvider>,
    );

    const list = screen.getByRole('list');
    for (const door of DOORS) {
      expect(within(list).getByText(door.label)).toBeInTheDocument();
      expect(within(list).getByText(door.hint)).toBeInTheDocument();
    }
  });

  it('tells a screen-reader user their position in the set', () => {
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={vi.fn()} />
      </AnnouncerProvider>,
    );

    expect(screen.getByText('Choice 1 of 4')).toBeInTheDocument();
    expect(screen.getByText('Choice 4 of 4')).toBeInTheDocument();
  });

  it('offers to read itself aloud on one tap', async () => {
    /**
     * Browsers block audio before a gesture, so autoplay would fail silently on
     * most devices — worst of all for the person who needs it. One button gives
     * everyone the same thing.
     */
    const user = userEvent.setup();
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={vi.fn()} />
      </AnnouncerProvider>,
    );

    await user.click(screen.getByRole('button', { name: /read this aloud/i }));
    expect(speechSynthesis.speak).toHaveBeenCalled();
  });

  it('degrades gracefully when the browser cannot speak', async () => {
    /** jsdom has speechSynthesis stubbed but no utterance constructor - which
     *  is exactly the shape of a browser with partial support. The handler must
     *  not throw and leave the button looking broken. */
    vi.stubGlobal('SpeechSynthesisUtterance', undefined);
    const user = userEvent.setup();
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={vi.fn()} />
      </AnnouncerProvider>,
    );

    await user.click(screen.getByRole('button', { name: /read this aloud/i }));

    // Still on the screen, still choosable.
    expect(screen.getByRole('button', { name: /i will read/i })).toBeInTheDocument();
  });

  it('the spoken introduction names every choice', () => {
    for (const door of DOORS) {
      expect(SPOKEN_INTRO).toContain(door.label);
    }
    expect(SPOKEN_INTRO).toMatch(/change this at any time/i);
  });

  it('reassures rather than pressures the undecided', () => {
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={vi.fn()} />
      </AnnouncerProvider>,
    );

    expect(screen.getByText(/nothing here is permanent/i)).toBeInTheDocument();
  });

  it('reports the chosen door', async () => {
    const onChoose = vi.fn();
    const user = userEvent.setup();
    render(
      <AnnouncerProvider>
        <FourDoorScreen onChoose={onChoose} />
      </AnnouncerProvider>,
    );

    await user.click(screen.getByRole('button', { name: /i use sign language/i }));
    expect(onChoose).toHaveBeenCalledWith('sign');
  });
});

describe('what each door means', () => {
  it('gives a sign-language learner captions alongside', () => {
    /** Our ISL library covers 100 phrases. A Deaf learner meeting an unsigned
     *  one must not hit a blank screen. */
    expect(DOOR_PROFILE.sign.output).toContain('captioned_text');
  });

  it('gives a pictures learner Easy-Read, symbols and audio together', () => {
    expect(DOOR_PROFILE.pictures.output).toEqual(['easy_read', 'pictograph', 'audio']);
    expect(DOOR_PROFILE.pictures.easyRead).toBe(true);
  });

  it('never leaves anyone with no way to answer', () => {
    for (const door of Object.values(DOOR_PROFILE)) {
      expect(door.input.length).toBeGreaterThan(0);
      expect(door.output.length).toBeGreaterThan(0);
    }
  });

  it('never leaves speech as the only way to answer', () => {
    for (const door of Object.values(DOOR_PROFILE)) {
      expect(door.input.some((mode) => mode !== 'speech')).toBe(true);
    }
  });
});

describe('the confirmation stage', () => {
  beforeEach(() => {
    vi.stubGlobal('speechSynthesis', { speak: vi.fn(), cancel: vi.fn() });
  });

  async function reachConfirm(user: ReturnType<typeof userEvent.setup>, door = /i will read/i) {
    await user.click(screen.getByRole('button', { name: door }));
    expect(await screen.findByRole('heading', { name: /a few more questions/i })).toBeInTheDocument();
  }

  it('asks only questions that could change the profile', async () => {
    const { user } = renderFlow();
    await reachConfirm(user, /i will use pictures/i);

    // Someone who chose pictures is not asked whether they will speak.
    expect(screen.queryByText(/will you answer by speaking/i)).not.toBeInTheDocument();
  });

  it('lets a learner go back and change their door', async () => {
    const { user } = renderFlow();
    await reachConfirm(user);

    await user.click(screen.getByRole('button', { name: /go back/i }));
    expect(
      screen.getByRole('heading', { name: /how would you like to use this app/i }),
    ).toBeInTheDocument();
  });

  it('treats silence as "not answered", never as "no"', async () => {
    /** Assuming a no would strip a channel nobody asked us to remove. */
    const { onComplete, user } = renderFlow();
    await reachConfirm(user);

    await user.click(screen.getByRole('button', { name: /start using the app/i }));

    const profile = onComplete.mock.calls[0]![0];
    expect(profile.input_channels).toContain('speech');
    expect(profile.speech_status).toBe('undeclared');
  });

  it('removes speech only when the learner says no', async () => {
    const { onComplete, user } = renderFlow();
    await reachConfirm(user);

    const speaking = screen.getByRole('group', { name: /will you answer by speaking/i });
    await user.click(within(speaking).getByLabelText('No'));
    await user.click(screen.getByRole('button', { name: /start using the app/i }));

    const profile = onComplete.mock.calls[0]![0];
    expect(profile.input_channels).not.toContain('speech');
    expect(profile.speech_status).toBe('nonverbal');
    // And they still have a way to answer.
    expect(profile.input_channels.length).toBeGreaterThan(0);
  });

  it('turns on switch scanning when asked', async () => {
    const { onComplete, user } = renderFlow();
    await reachConfirm(user);

    const switching = screen.getByRole('group', { name: /switch or a button device/i });
    await user.click(within(switching).getByLabelText('Yes'));
    await user.click(screen.getByRole('button', { name: /start using the app/i }));

    const profile = onComplete.mock.calls[0]![0];
    expect(profile.interaction?.switch_scanning?.enabled).toBe(true);
    // Two-switch by default: it has no timer at all.
    expect(profile.interaction?.switch_scanning?.switch_count).toBe(2);
    expect(profile.input_channels).toContain('switch');
  });

  it('raises the target size when bigger buttons would help', async () => {
    const { onComplete, user } = renderFlow();
    await reachConfirm(user);

    const bigger = screen.getByRole('group', { name: /bigger buttons/i });
    await user.click(within(bigger).getByLabelText('Yes'));
    await user.click(screen.getByRole('button', { name: /start using the app/i }));

    expect(onComplete.mock.calls[0]![0].presentation?.target_size_px).toBe(88);
  });

  it('never asks for a diagnosis', async () => {
    /**
     * It asks what someone can USE. That is the only thing the router needs,
     * and the only thing anyone owes us.
     */
    const { user } = renderFlow();
    await reachConfirm(user);

    const page = document.body.textContent?.toLowerCase() ?? '';
    for (const word of ['diagnosis', 'condition', 'disability type', 'impairment', 'disorder']) {
      expect(page).not.toContain(word);
    }
  });
});

describe('stage 0 — what the browser already tells us', () => {
  it('reads the media queries rather than asking', () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('reduced-motion') || query.includes('coarse'),
    }));

    const detected = detectPreferences();

    expect(detected.motion_reduced).toBe(true);
    // A coarse pointer means touch or a switch-driven cursor; bigger targets
    // help both and cost a mouse user nothing.
    expect(detected.target_size_px).toBe(56);
  });

  it('returns nothing rather than failing where matchMedia is absent', () => {
    vi.stubGlobal('matchMedia', undefined);
    expect(detectPreferences()).toEqual({});
  });
});
