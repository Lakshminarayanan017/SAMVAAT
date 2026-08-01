/**
 * Route screen: how this app talks to me.
 *
 * WHY THIS IS ITS OWN ROUTE AND NOT A DIALOG
 * ------------------------------------------
 * The charter requires a learner to be able to change how the app speaks to
 * them from anywhere, in at most two actions. A settings *dialog* satisfies
 * that on paper and fails it in practice: it can only be opened from wherever
 * its trigger lives, and a learner who has ended up somewhere the trigger is
 * not — a chromeless mission, a story — has no route to it at all.
 *
 * A URL is reachable from everywhere, including from the browser's own history
 * and from a trainer's message.
 *
 * EVERY CHANGE APPLIES IMMEDIATELY
 * --------------------------------
 * There is no Save button. A learner who cannot read the current contrast well
 * enough to find Save cannot save the setting that would let them read it —
 * which is exactly the population this screen exists for. Changes take effect
 * on selection and persist in the background; a failed save says so without
 * reverting what the learner can already see working.
 */
import { useCallback, useState } from 'react';
import type { CommunicationAbilityProfile } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { useProfile } from '@/a11y/ProfileProvider';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';
import { Card, Stack, Text } from '@/ui';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export default function SettingsScreen() {
  const { session } = useSession();
  const { profile, updateProfile } = useProfile();
  const announce = useAnnounce();
  const [failed, setFailed] = useState(false);

  const change = useCallback(
    (patch: Partial<CommunicationAbilityProfile>, spoken: string) => {
      // Applied locally first, so the learner sees the change even if the
      // network is slow or absent. That is the whole point of the setting.
      updateProfile(patch);
      announce(spoken);
      setFailed(false);

      void fetch(`${BASE_URL}/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.token}`,
        },
        body: JSON.stringify({ ...profile, ...patch }),
      })
        .then((response) => {
          if (!response.ok) setFailed(true);
        })
        .catch(() => setFailed(true));
    },
    [announce, profile, session.token, updateProfile],
  );

  const presentation = profile.presentation ?? {};

  return (
    <AppRoute title="How this app talks to me">
      <Stack gap="lg">
        <Text variant="title" as="h1">
          How this app talks to me
        </Text>
        <Text variant="body" tone="secondary" measure>
          Every change happens straight away. You can change any of these as often as you like.
        </Text>

        {failed && (
          <Card padding="md">
            <Text variant="body" measure>
              Your change is working now, but we could not save it for next time. We will keep
              trying.
            </Text>
          </Card>
        )}

        <Choice
          legend="Text size and wording"
          hint="Easy-Read uses shorter sentences and bigger text."
          options={[
            { value: 'standard', label: 'Standard' },
            { value: 'easy_read', label: 'Easy-Read' },
          ]}
          value={profile.text_complexity ?? 'standard'}
          onChange={(value) =>
            change(
              { text_complexity: value as CommunicationAbilityProfile['text_complexity'] },
              value === 'easy_read' ? 'Easy-Read on.' : 'Standard text on.',
            )
          }
        />

        <Choice
          legend="Contrast"
          hint="High contrast uses pure black and white with strong outlines."
          options={[
            { value: 'standard', label: 'Standard' },
            { value: 'high_contrast', label: 'High contrast' },
          ]}
          value={presentation.contrast_theme ?? 'standard'}
          onChange={(value) =>
            change(
              {
                presentation: {
                  ...presentation,
                  contrast_theme: value as 'standard' | 'high_contrast',
                },
              },
              value === 'high_contrast' ? 'High contrast on.' : 'Standard contrast on.',
            )
          }
        />

        <Choice
          legend="Light or dark"
          options={[
            { value: 'system', label: 'Match my device' },
            { value: 'light', label: 'Light' },
            { value: 'dark', label: 'Dark' },
          ]}
          value={presentation.colour_scheme ?? 'system'}
          onChange={(value) =>
            change(
              {
                presentation: {
                  ...presentation,
                  colour_scheme: value as 'light' | 'dark' | 'system',
                },
              },
              `Colours set to ${value === 'system' ? 'match your device' : value}.`,
            )
          }
        />

        <Choice
          legend="Movement"
          hint="Turning movement off keeps everything working. Nothing is shown only by moving."
          options={[
            { value: 'on', label: 'Allow movement' },
            { value: 'off', label: 'No movement' },
          ]}
          value={presentation.motion_reduced ? 'off' : 'on'}
          onChange={(value) =>
            change(
              { presentation: { ...presentation, motion_reduced: value === 'off' } },
              value === 'off' ? 'Movement off.' : 'Movement on.',
            )
          }
        />

        <Choice
          legend="Button size"
          hint="Bigger buttons are easier to hit."
          options={[
            { value: '44', label: 'Standard' },
            { value: '64', label: 'Large' },
            { value: '88', label: 'Largest' },
          ]}
          value={String(presentation.target_size_px ?? 44)}
          onChange={(value) =>
            change(
              { presentation: { ...presentation, target_size_px: Number(value) } },
              'Button size changed.',
            )
          }
        />
      </Stack>
    </AppRoute>
  );
}

/**
 * A group of choices.
 *
 * Real `<fieldset>`, real `<legend>`, real radio inputs. A screen reader
 * announces "Contrast, High contrast, radio button, 2 of 2" — the whole
 * question and the whole answer in one utterance. No ARIA pattern reproduces
 * that as reliably, and arrow-key navigation within the group comes free.
 *
 * The input is visually hidden and its sibling `<span>` is the visible target,
 * because a 44px radio dot is not a 44px target and the label has to be part
 * of the target for a learner with a motor impairment. Styling lives in
 * `ui.css` keyed on `:checked` and `:focus-visible`, so the visible state
 * always follows the real control rather than a copy of it.
 *
 * Deliberately NOT a <Button> inside the label: nesting an interactive element
 * inside another is an axe violation and gives a keyboard user every option
 * twice.
 */
function Choice({
  legend,
  hint,
  options,
  value,
  onChange,
}: {
  legend: string;
  hint?: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}) {
  const name = legend.replace(/\W+/g, '-').toLowerCase();

  return (
    <fieldset data-ui="choice-group">
      <Text variant="heading" as="legend">
        {legend}
      </Text>

      <Stack gap="sm" style={{ marginBlockStart: 'var(--space-sm, 0.5rem)' }}>
        {hint && (
          <Text variant="caption" tone="secondary" measure>
            {hint}
          </Text>
        )}

        <Stack direction="horizontal" gap="sm">
          {options.map((option) => (
            <label key={option.value} data-ui="choice">
              <input
                type="radio"
                name={name}
                value={option.value}
                checked={value === option.value}
                onChange={() => onChange(option.value)}
                className="visually-hidden"
              />
              <span data-ui="choice-face">{option.label}</span>
            </label>
          ))}
        </Stack>
      </Stack>
    </fieldset>
  );
}
