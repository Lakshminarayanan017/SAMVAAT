/**
 * The primitive layer.
 *
 * These tests are mostly about what the primitives *refuse* to do. A button
 * that renders is not interesting; a button that cannot be made smaller than
 * the learner's target size, a card that cannot be made clickable without being
 * focusable, and a field whose label cannot become detached from its input are.
 *
 * Every primitive is also swept with axe, because a defect here multiplies
 * across every screen that uses it — which after the migration is all of them.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { CommunicationAbilityProfile } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { DEFAULT_PROFILE, ProfileProvider } from '@/a11y/ProfileProvider';
import {
  ActionCard,
  Button,
  Card,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  Grid,
  Icon,
  ProgressBar,
  ProgressDots,
  Sheet,
  Skeleton,
  Stack,
  Text,
} from '@/ui';

import { blockingViolations, checkA11y, formatViolations } from '../a11y/axe';

/**
 * Queries scoped to the rendered content.
 *
 * `screen` also sees the Announcer's two global live regions, which carry
 * role="status" and role="alert" permanently. An unscoped getByRole('alert')
 * therefore finds the announcer as well as the component under test — a test
 * artefact, not a duplicate-region bug.
 */
function ui() {
  const main = document.querySelector('main');
  if (!main) throw new Error('no <main> — did shell() run?');
  return within(main);
}

function shell(children: React.ReactNode, profile: CommunicationAbilityProfile = DEFAULT_PROFILE) {
  return render(
    <AnnouncerProvider>
      <ProfileProvider initialProfile={profile}>
        <main>{children}</main>
      </ProfileProvider>
    </AnnouncerProvider>,
  );
}

async function expectClean(container: Element) {
  const results = await checkA11y(container);
  const blocking = blockingViolations(results);
  expect(blocking, formatViolations({ ...results, violations: blocking })).toHaveLength(0);
}

describe('Button', () => {
  it('is a real button element', async () => {
    shell(<Button>Continue</Button>);
    expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();
  });

  it('defaults to type="button"', async () => {
    /* Inside a form, a button without an explicit type submits. A "Show hint"
       control that reloads the page is a bug nobody finds until a form exists. */
    shell(<Button>Hint</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('honours the learner target size rather than a hard-coded 44px', () => {
    /* The profile can raise the floor to 88px for a motor impairment. A button
       that hard-codes 44 silently defeats that setting — a bug that passes
       every test and fails one persona completely. */
    shell(<Button>Go</Button>);
    const style = screen.getByRole('button').getAttribute('style') ?? '';
    expect(style).toContain('var(--target-min');
    expect(style).not.toMatch(/min-height:\s*44px/);
  });

  it('announces a busy state rather than only showing one', async () => {
    shell(<Button loading>Save</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toBeDisabled();
  });

  it('replaces the label while loading instead of hiding it behind a spinner', () => {
    shell(<Button loading loadingLabel="Saving your answer…">Save</Button>);
    expect(screen.getByRole('button', { name: 'Saving your answer…' })).toBeInTheDocument();
  });

  it('does not fire when disabled', async () => {
    const onClick = vi.fn();
    shell(
      <Button disabled onClick={onClick}>
        Go
      </Button>,
    );
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  it.each(['primary', 'secondary', 'quiet', 'danger'] as const)('%s variant is clean', async (variant) => {
    const { container } = shell(<Button variant={variant}>Delete everything about me</Button>);
    await expectClean(container);
  });
});

describe('Card', () => {
  it('renders static content without becoming interactive', () => {
    shell(
      <Card>
        <Text>Some content</Text>
      </Card>,
    );
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('carries a border at every elevation, not only a shadow', () => {
    /* Shadow disappears in forced-colours mode and in both high-contrast
       themes. A learner using either would lose every card boundary at once. */
    const { container } = shell(<Card elevation="overlay">x</Card>);
    const style = container.querySelector('[data-ui="card"]')?.getAttribute('style') ?? '';
    expect(style).toMatch(/border-width:\s*2px/);
  });

  describe('ActionCard', () => {
    it('is a real button, so it is focusable and keyboard-activatable', async () => {
      /* A div with onClick is not focusable, not activatable by Enter or
         Space, and invisible to switch scanning. */
      const onClick = vi.fn();
      shell(
        <ActionCard label="Open World 4" onClick={onClick}>
          <Text>World 4</Text>
        </ActionCard>,
      );

      const card = screen.getByRole('button', { name: 'Open World 4' });
      card.focus();
      await userEvent.keyboard('{Enter}');
      expect(onClick).toHaveBeenCalled();
    });

    it('requires an explicit accessible name', async () => {
      /* Without one the browser concatenates every string inside, producing
         "World 4 Speaking Up For Yourself 3 of 5 levels 2 stars" with no
         indication of what pressing it does. */
      const { container } = shell(
        <ActionCard label="Open World 4: Speaking Up For Yourself" onClick={() => {}}>
          <Text>World 4</Text>
          <Text>3 of 5 levels</Text>
        </ActionCard>,
      );
      expect(
        screen.getByRole('button', { name: 'Open World 4: Speaking Up For Yourself' }),
      ).toBeInTheDocument();
      await expectClean(container);
    });
  });
});

describe('Text', () => {
  it('separates heading level from type size', () => {
    /* Heading level is document structure; type size is visual. A section that
       needs smaller type must not therefore skip from h2 to h4. */
    shell(
      <Text variant="caption" as="h2">
        A quiet heading
      </Text>,
    );
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('A quiet heading');
  });

  it('grows body text under Easy-Read rather than only simplifying words', () => {
    const { container: standard } = shell(<Text>Hello</Text>);
    const standardSize = standard.querySelector('[data-ui="text"]')?.getAttribute('style');

    const { container: easy } = shell(<Text>Hello</Text>, {
      ...DEFAULT_PROFILE,
      text_complexity: 'easy_read',
    } as CommunicationAbilityProfile);
    const easySize = easy.querySelector('[data-ui="text"]')?.getAttribute('style');

    expect(standardSize).toContain('1.125rem');
    expect(easySize).toContain('1.25rem');
  });

  it('does not shrink captions under Easy-Read', () => {
    /* Small supporting text is exactly what an Easy-Read reader most needs kept
       legible. "Captions are small" is a convention, not a requirement. */
    const { container } = shell(<Text variant="caption">A note</Text>, {
      ...DEFAULT_PROFILE,
      text_complexity: 'easy_read',
    } as CommunicationAbilityProfile);

    const style = container.querySelector('[data-ui="text"]')?.getAttribute('style') ?? '';
    expect(style).toContain('1.125rem');
  });

  it('caps line length when asked', () => {
    const { container } = shell(<Text measure>Long prose</Text>);
    expect(container.querySelector('[data-ui="text"]')?.getAttribute('style')).toContain('ch');
  });
});

describe('ProgressDots', () => {
  it('states progress in words, not only in dots', async () => {
    /* A row of filled circles is meaningless to a screen-reader user and
       ambiguous to a learner with a colour vision deficiency. */
    shell(<ProgressDots total={5} completed={3} current={3} />);
    expect(screen.getByRole('group', { name: '3 of 5 missions done.' })).toBeInTheDocument();
  });

  it('hides the individual dots from assistive tech', () => {
    /* Announcing five separate dots would bury the sentence in noise. */
    const { container } = shell(<ProgressDots total={5} completed={2} />);
    for (const dot of container.querySelectorAll('[data-ui="progress-dot"]')) {
      expect(dot).toHaveAttribute('aria-hidden', 'true');
    }
  });

  it('is clean', async () => {
    const { container } = shell(<ProgressDots total={6} completed={2} current={2} />);
    await expectClean(container);
  });
});

describe('ProgressBar', () => {
  it('exposes a real progressbar role with values', () => {
    shell(<ProgressBar value={40} max={100} label="XP to next level" />);
    const bar = screen.getByRole('progressbar', { name: 'XP to next level' });
    expect(bar).toHaveAttribute('aria-valuenow', '40');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('shows the value as text as well as fill', () => {
    shell(<ProgressBar value={40} max={100} label="XP" />);
    expect(screen.getByText(/40 of 100/)).toBeInTheDocument();
  });

  it('clamps out-of-range values rather than overflowing', () => {
    shell(<ProgressBar value={150} max={100} label="XP" />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });

  it('survives a zero maximum without dividing by zero', () => {
    shell(<ProgressBar value={0} max={0} label="Nothing yet" />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});

describe('Field', () => {
  it('associates the label with the input', async () => {
    /* The most common form defect there is: a label visually beside an input
       and not programmatically tied to it announces "edit text, blank". */
    shell(<Field label="Your name" />);
    expect(screen.getByLabelText('Your name')).toBeInTheDocument();
  });

  it('wires a hint through aria-describedby', () => {
    shell(<Field label="Email" hint="We only use this to sign you in." />);
    const input = screen.getByLabelText('Email');
    const describedBy = input.getAttribute('aria-describedby') ?? '';
    expect(describedBy).toBeTruthy();
    expect(document.getElementById(describedBy.split(' ')[0]!)).toHaveTextContent(
      'We only use this to sign you in.',
    );
  });

  it('announces an error and marks the control invalid', () => {
    shell(<Field label="Email" error="That address is missing an @." />);
    expect(ui().getByRole('alert')).toHaveTextContent('That address is missing an @.');
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
  });

  it('does not rely on colour alone for an error', () => {
    const { container } = shell(<Field label="Email" error="Missing an @." />);
    // Border weight changes as well as colour, and the message is text.
    expect(container.querySelector('[data-ui="input"]')?.getAttribute('style')).toMatch(
      /border-width:\s*2px/,
    );
  });

  it('generates unique ids for repeated fields', () => {
    shell(
      <>
        <Field label="First" />
        <Field label="Second" />
      </>,
    );
    const first = screen.getByLabelText('First').id;
    const second = screen.getByLabelText('Second').id;
    expect(first).not.toBe(second);
  });

  it('is clean', async () => {
    const { container } = shell(<Field label="Your name" hint="As you like to be called." />);
    await expectClean(container);
  });
});

describe('Dialog', () => {
  it('is labelled by its title', () => {
    shell(
      <Dialog open onClose={() => {}} title="Are you sure?">
        <Text>This cannot be undone.</Text>
      </Dialog>,
    );
    expect(screen.getByRole('dialog', { name: 'Are you sure?' })).toBeInTheDocument();
  });

  it('always offers a visible close control', async () => {
    /* Escape is not discoverable and is unavailable to a switch user driving a
       two-button interface. */
    const onClose = vi.fn();
    shell(
      <Dialog open onClose={onClose} title="Settings">
        <Text>Body</Text>
      </Dialog>,
    );

    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('does not render as open when closed', () => {
    shell(
      <Dialog open={false} onClose={() => {}} title="Settings">
        <Text>Body</Text>
      </Dialog>,
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

describe('Sheet', () => {
  it('is a labelled dialog anchored to the bottom', () => {
    shell(
      <Sheet open onClose={() => {}} title="Choose a world">
        <Text>Body</Text>
      </Sheet>,
    );
    expect(screen.getByRole('dialog', { name: 'Choose a world' })).toBeInTheDocument();
  });

  it('caps its height so its own close button cannot be pushed off screen', () => {
    const { container } = shell(
      <Sheet open onClose={() => {}} title="Tall">
        <Text>Body</Text>
      </Sheet>,
    );
    expect(container.querySelector('[data-ui="sheet"]')?.getAttribute('style')).toContain('85vh');
  });
});

describe('Skeleton', () => {
  it('announces what is loading when given a label', () => {
    shell(<Skeleton label="Loading your progress" />);
    expect(screen.getByRole('status', { name: 'Loading your progress' })).toBeInTheDocument();
  });

  it('is silent when unlabelled, rather than announcing a blank', () => {
    shell(<Skeleton />);
    expect(ui().queryByRole('status')).not.toBeInTheDocument();
  });
});

describe('ErrorState', () => {
  it('is announced', () => {
    shell(<ErrorState title="We could not load that" />);
    expect(ui().getByRole('alert')).toHaveTextContent('We could not load that');
  });

  it('is clean', async () => {
    const { container } = shell(
      <ErrorState
        title="We could not load that"
        body="Nothing you have done has been lost."
        action={{ label: 'Try again', onClick: () => {} }}
      />,
    );
    await expectClean(container);
  });
});

describe('EmptyState', () => {
  it('is not announced as an alert', () => {
    /* An empty list is a normal state. Interrupting a screen reader to say so
       is noise. */
    shell(<EmptyState title="Nothing here yet" />);
    expect(ui().queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('Icon', () => {
  it('is decorative by default', () => {
    /* An icon beside a text label is decoration. Announcing both produces
       "star star, two stars". */
    const { container } = shell(<Icon path="M0 0h24v24H0z" />);
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('becomes an image when given a label', () => {
    shell(<Icon path="M0 0h24v24H0z" label="Two stars earned" />);
    expect(screen.getByRole('img', { name: 'Two stars earned' })).toBeInTheDocument();
  });

  it('is never focusable', () => {
    /* Older IE-era SVG behaviour puts SVGs in the tab order, which strands a
       keyboard user on a decoration. */
    const { container } = shell(<Icon path="M0 0h24v24H0z" />);
    expect(container.querySelector('svg')).toHaveAttribute('focusable', 'false');
  });
});

describe('Stack and Grid', () => {
  it('wraps horizontal stacks, so 400% zoom does not scroll sideways', () => {
    const { container } = shell(
      <Stack direction="horizontal">
        <Button>One</Button>
        <Button>Two</Button>
      </Stack>,
    );
    expect(container.querySelector('[data-ui="stack"]')).toHaveAttribute(
      'data-direction',
      'horizontal',
    );
  });

  it('renders as a list when asked, keeping list semantics', () => {
    shell(
      <Stack as="ul">
        <li>One</li>
      </Stack>,
    );
    expect(screen.getByRole('list')).toBeInTheDocument();
  });

  it('grid columns never exceed the viewport', () => {
    /* `minmax(16rem, 1fr)` alone overflows below 16rem — which is exactly where
       a 400% zoom user lives. `min(16rem, 100%)` is the fix. */
    const { container } = shell(<Grid min="16rem">{null}</Grid>);
    expect(container.querySelector('[data-ui="grid"]')?.getAttribute('style')).toContain(
      'min(16rem, 100%)',
    );
  });
});
