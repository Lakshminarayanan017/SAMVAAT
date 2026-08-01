/**
 * Social stories, on screen.
 *
 * The generator's own tests cover the Carol Gray ratio and the panel structure.
 * What is tested here is what only the client can get wrong: whether a learner
 * is told a computer wrote this, whether they are ever hurried, and whether a
 * generated story gets the same accessibility treatment as authored content.
 *
 * That last one is the point of the whole feature. A social story generated for
 * a learner who reads pictographs, and delivered as prose they cannot read, is
 * worse than no story — it looks like provision.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ProfileProvider, DEFAULT_PROFILE } from '@/a11y/ProfileProvider';
import { SocialStory } from '@/features/stories/SocialStory';
import { panelToBlock, type Story, type StoryPanel } from '@/features/stories/toBlock';
import { page } from '../helpers';

function panel(text: string, type: StoryPanel['type'] = 'descriptive'): StoryPanel {
  return { text, type, pictograph_hint: 'work' };
}

function story(overrides: Partial<Story> = {}): Story {
  return {
    title: 'When my supervisor asks me to do it again',
    panels: [
      panel('I work in a stockroom.'),
      panel('Sometimes my supervisor asks me to do a task again.'),
      panel('This usually means the task was not finished.', 'descriptive'),
      panel('I can feel worried when this happens.', 'perspective'),
      panel('Most people are asked to redo work sometimes.', 'affirmative'),
      panel('I can ask what to change.', 'directive'),
    ],
    status: 'published',
    generated: true,
    validation: {
      valid: true,
      problems: [],
      directive_count: 1,
      non_directive_count: 5,
      ratio: 5,
    },
    notice: null,
    ...overrides,
  };
}

function stubApi(body: Story, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ ok, status: ok ? 200 : 503, json: async () => body })),
  );
}

function setup(profile = DEFAULT_PROFILE) {
  render(
    <AnnouncerProvider>
      <ProfileProvider initialProfile={profile}>
        <SocialStory
          token="learner-token"
          jobContext="a supermarket stockroom"
          situation="my supervisor asks me to redo a task"
        />
      </ProfileProvider>
    </AnnouncerProvider>,
  );
}

async function open() {
  await userEvent.click(page().getByRole('button', { name: /make my story/i }));
  await waitFor(() => expect(page().getByRole('heading', { level: 2 })).toBeInTheDocument());
}

beforeEach(() => stubApi(story()));
afterEach(() => vi.unstubAllGlobals());

describe('reading a story', () => {
  it('shows one panel at a time, not the whole story at once', async () => {
    setup();
    await open();

    expect(page().getByText('I work in a stockroom.')).toBeInTheDocument();
    // The second panel is not on screen yet.
    expect(page().queryByText(/asks me to do a task again/i)).not.toBeInTheDocument();
  });

  it('moves forward only when the learner asks', async () => {
    setup();
    await open();

    await userEvent.click(page().getByRole('button', { name: 'Next' }));

    expect(page().getByText(/asks me to do a task again/i)).toBeInTheDocument();
  });

  it('lets the learner go back', async () => {
    setup();
    await open();

    await userEvent.click(page().getByRole('button', { name: 'Next' }));
    await userEvent.click(page().getByRole('button', { name: 'Back' }));

    expect(page().getByText('I work in a stockroom.')).toBeInTheDocument();
  });

  it('says where the learner is, so the story has a shape', async () => {
    setup();
    await open();

    expect(page().getByText(/page 1 of 6/i)).toBeInTheDocument();
  });

  it('cannot be paged past either end', async () => {
    setup();
    await open();

    expect(page().getByRole('button', { name: 'Back' })).toBeDisabled();

    for (let i = 0; i < 5; i += 1) {
      await userEvent.click(page().getByRole('button', { name: /next|this is the end/i }));
    }
    expect(page().getByRole('button', { name: /this is the end/i })).toBeDisabled();
  });
});

describe('nothing hurries the learner', () => {
  it('has no timer, countdown or speed language anywhere (Ethics E6)', async () => {
    setup();
    await open();

    const text = document.querySelector('[data-samvaad-content]')?.textContent ?? '';
    for (const banned of [/seconds? left/i, /time remaining/i, /hurry/i, /too slow/i, /countdown/i]) {
      expect(text).not.toMatch(banned);
    }
  });

  it('tells the learner they can re-read it', async () => {
    setup();
    await open();
    expect(page().getByText(/as many times as you like/i)).toBeInTheDocument();
  });

  it('promises no test at the end before the learner commits', async () => {
    setup();
    expect(page().getByText(/no test at the end/i)).toBeInTheDocument();
  });
});

describe('provenance (Ethics E5)', () => {
  it('says a computer wrote it', async () => {
    setup();
    await open();
    expect(screen.getByTestId('story-provenance')).toHaveTextContent(/written by a computer/i);
  });

  it('admits it can be wrong', async () => {
    setup();
    await open();
    expect(screen.getByTestId('story-provenance')).toHaveTextContent(/can be wrong/i);
  });

  it('repeats the label on every page, not just the first', async () => {
    /* A label the learner saw once on page one is not a label they are reading
       on page four. */
    setup();
    await open();

    await userEvent.click(page().getByRole('button', { name: 'Next' }));
    await userEvent.click(page().getByRole('button', { name: 'Next' }));

    expect(screen.getByTestId('story-provenance')).toHaveTextContent(/written by a computer/i);
  });

  it('offers no way to dismiss the label', async () => {
    setup();
    await open();

    const buttons = page()
      .getAllByRole('button')
      .map((element) => element.textContent ?? '');
    expect(buttons.join(' ')).not.toMatch(/dismiss|hide|got it|close/i);
  });

  it('says when a trainer has not reviewed it yet', async () => {
    stubApi(story({ status: 'draft' }));
    setup();
    await open();

    expect(screen.getByTestId('story-provenance')).toHaveTextContent(/not read this yet/i);
  });

  it('shows no provenance banner for a reviewed, human-published story', async () => {
    stubApi(story({ generated: false, status: 'published' }));
    setup();
    await open();

    expect(screen.queryByTestId('story-provenance')).not.toBeInTheDocument();
  });
});

describe('generated panels get the same accessibility treatment as authored ones', () => {
  it('renders through the Modality Router rather than as raw prose', async () => {
    /* Proven by profile: a pictograph learner must not receive a paragraph.
       If this screen ever printed panel.text directly, this test would still
       pass on the default profile — so it is asserted on a symbol profile. */
    setup({
      ...DEFAULT_PROFILE,
      output_channels: ['pictograph', 'easy_read'],
      text_complexity: 'easy_read',
    });
    await open();

    // The router reached the pictograph renderer, and the panel's hint became
    // a real symbol strip — not a paragraph with a symbol-shaped name.
    expect(page().getByRole('img', { name: /symbols: work/i })).toBeInTheDocument();
  });

  it('claims only the representations a generated panel actually has', () => {
    /* Copying the text into `easy_read` and calling it a paraphrase would be a
       lie the renderer trusts. A long panel simply has no easy_read. */
    const long = panel(
      'I work in a stockroom and sometimes my supervisor will come over to ask me whether the ' +
        'task I finished earlier was completed to the standard that the shift requires.',
    );
    const block = panelToBlock(long, 0, 'story.test');

    expect(block.representations.easy_read).toBeUndefined();
    expect(block.representations.caption).toBe(long.text);
    // Never invented.
    expect(block.representations.audio_native).toBeUndefined();
    expect(block.representations.isl_clip).toBeUndefined();
  });

  it('marks a short panel as Easy-Read, because it provably is', () => {
    const block = panelToBlock(panel('I work in a stockroom.'), 0, 'story.test');
    expect(block.representations.easy_read).toBe('I work in a stockroom.');
  });

  it('labels every block as generated, which is what the AI notice derives from', () => {
    const block = panelToBlock(panel('I work here.'), 0, 'story.test');
    expect(block.source).toBe('generated');
  });

  it('asks nothing of the learner — a story is read, not answered', () => {
    const block = panelToBlock(panel('I work here.'), 0, 'story.test');
    expect(block.interaction.target_response).toBeUndefined();
    // No input mode is excluded, so no persona is locked out of the panel.
    expect(block.interaction.accepted_input_modes).toContain('aac');
    expect(block.interaction.accepted_input_modes).toContain('switch');
  });

  it('requires no channel a learner might not have', () => {
    const block = panelToBlock(panel('I work here.'), 0, 'story.test');
    expect(block.a11y.requires_audio).toBe(false);
    expect(block.a11y.requires_vision).toBe(false);
    expect(block.a11y.requires_speech).toBe(false);
  });

  it('gives every panel a distinct, ordered id', () => {
    const ids = story().panels.map((p, i) => panelToBlock(p, i, 'story.x').id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids[0]).toBe('story.x.panel_01');
  });
});

describe('when the story cannot be made', () => {
  it('says so without blaming the learner, and offers a retry', async () => {
    stubApi(story(), false);
    setup();

    await userEvent.click(page().getByRole('button', { name: /make my story/i }));

    await waitFor(() =>
      expect(screen.getByTestId('story-error')).toHaveTextContent(/nothing is lost/i),
    );
    expect(page().getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });
});
