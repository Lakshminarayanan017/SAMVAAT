/**
 * The level runner (Blueprint §5.2, G2).
 *
 * The session shape, in one component:
 *
 *   INTRO ── what you will practise · how many missions
 *     ↓      skippable, never shown twice for the same level
 *   MISSION 1 ─┐
 *   MISSION 2  │  progress dots visible throughout —
 *   MISSION 3 ─┘  the end is always in sight
 *     ↓
 *   CELEBRATION ── stars land · XP counts · one sentence, announced once
 *
 * FOUR RULES THIS COMPONENT EXISTS TO HOLD
 * ----------------------------------------
 * 1. **The end is always visible.** `<ProgressDots>` on every mission, stating
 *    "3 of 5 missions done" in words. A learner who cannot answer "how much is
 *    left?" is a learner deciding whether to stop.
 *
 * 2. **Nothing is timed.** No countdown, no bonus, no "you took a while".
 *    Ethics E6, and there is a test that greps this file's rendered output.
 *
 * 3. **Unlimited retries at no cost.** No hearts, no lives, no progress lost.
 *    A wrong answer shows coaching and the mission stays open.
 *
 * 4. **A scaffold is always one press away**, and asking for it lowers the
 *    FSRS grade (genuine partial recall) while never touching XP (which is for
 *    effort). Both of those are enforced in the API by function signature, so
 *    this component simply reports what happened.
 *
 * The answer itself goes to `POST /practice/review` — the existing loop that
 * already owns FSRS, XP and grading. A second scoring path would disagree with
 * the first within a month.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ContentBlock } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { ModalityRouter } from '@/modality';
import { Button, Card, ProgressDots, Stack, Text } from '@/ui';

import { Celebration, type CelebrationLevel } from './Celebration';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export interface Mission {
  id: string;
  type: string;
  block_id: string;
  prompt: string;
  options: string[];
  scaffold: string;
}

export interface MissionPlan {
  level_id: string;
  title: string;
  world_title: string;
  sensitive: boolean;
  total: number;
  missions: Mission[];
}

type Phase = 'intro' | 'running' | 'finished';

export interface LevelRunnerProps {
  plan: MissionPlan;
  blocks: ContentBlock[];
  token: string;
  celebrationLevel: CelebrationLevel;
  onLeave: () => void;
  /** "One more" — the runner does not choose the next level itself. */
  onNext: () => void;
}

export function LevelRunner({
  plan,
  blocks,
  token,
  celebrationLevel,
  onLeave,
  onNext,
}: LevelRunnerProps) {
  const announce = useAnnounce();
  const [phase, setPhase] = useState<Phase>('intro');
  const [index, setIndex] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [xp, setXp] = useState(0);

  const mission = plan.missions[index];

  const blockFor = useMemo(() => {
    const byId = new Map(blocks.map((block) => [block.id, block]));
    return (id: string) => byId.get(id);
  }, [blocks]);

  const submit = useCallback(
    async (correct: boolean, usedScaffold: boolean) => {
      if (!mission) return;

      // The existing practice loop scores this. It cannot see how long the
      // learner took, and XP cannot see whether they were right — neither of
      // which is this component's business to change.
      const response = await fetch(`${BASE_URL}/practice/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          block_id: mission.block_id,
          correct,
          hints_used: usedScaffold ? 1 : 0,
        }),
      }).catch(() => null);

      if (response?.ok) {
        const body = (await response.json()) as { xp_awarded?: number };
        setXp((total) => total + (body.xp_awarded ?? 0));
      }

      if (correct) setCorrectCount((count) => count + 1);
    },
    [mission, token],
  );

  const advance = useCallback(() => {
    const next = index + 1;
    if (next >= plan.missions.length) {
      setPhase('finished');
      return;
    }
    setIndex(next);
    announce(`Mission ${next + 1} of ${plan.missions.length}.`);
  }, [announce, index, plan.missions.length]);

  if (phase === 'intro') {
    return (
      <Intro plan={plan} onStart={() => setPhase('running')} onLeave={onLeave} />
    );
  }

  if (phase === 'finished') {
    // Three stars for everything right; two for most; one for finishing. The
    // third star for *retention* is earned by coming back, which the journey
    // engine computes from FSRS stability rather than from this session.
    const stars =
      correctCount === plan.missions.length ? 3 : correctCount >= plan.missions.length / 2 ? 2 : 1;

    return (
      <Celebration
        starsEarned={stars}
        xpEarned={xp}
        level={celebrationLevel}
        onAgain={onNext}
        onDone={onLeave}
      />
    );
  }

  if (!mission) return null;

  return (
    <Stack gap="md">
      <ProgressDots
        total={plan.missions.length}
        completed={index}
        current={index}
        label="missions"
      />

      <MissionCard
        key={mission.id}
        mission={mission}
        block={blockFor(mission.block_id)}
        onAnswered={submit}
        onContinue={advance}
      />

      {/* A way out on every mission. A learner who cannot leave a screen is
          trapped in it, and "finish or lose your progress" is exactly the
          coercion this product refuses. */}
      <div>
        <Button variant="quiet" onClick={onLeave}>
          Stop for now
        </Button>
      </div>
    </Stack>
  );
}

function Intro({
  plan,
  onStart,
  onLeave,
}: {
  plan: MissionPlan;
  onStart: () => void;
  onLeave: () => void;
}) {
  return (
    <Card padding="lg">
      <Stack gap="sm">
        <Text variant="caption" tone="secondary">
          {plan.world_title}
        </Text>
        <Text variant="title" as="h1">
          {plan.title}
        </Text>
        {/* The count, before starting. The end is visible before the beginning. */}
        <Text variant="body" measure>
          {plan.missions.length} things to try. You can stop at any time, and nothing is timed.
        </Text>

        <Stack direction="horizontal" gap="sm">
          <Button variant="primary" onRaised onClick={onStart}>
            Start
          </Button>
          <Button variant="secondary" onRaised onClick={onLeave}>
            Not now
          </Button>
        </Stack>
      </Stack>
    </Card>
  );
}

/**
 * One mission.
 *
 * The phrase itself is rendered through the Modality Router, so a choice
 * arrives as text for one learner, as tappable symbols for another and as ISL
 * for a third with no branching here. That is the whole reason the mission
 * carries a `block_id` rather than a string.
 */
function MissionCard({
  mission,
  block,
  onAnswered,
  onContinue,
}: {
  mission: Mission;
  block: ContentBlock | undefined;
  onAnswered: (correct: boolean, usedScaffold: boolean) => void;
  onContinue: () => void;
}) {
  const announce = useAnnounce();
  const [scaffoldShown, setScaffoldShown] = useState(false);
  const [outcome, setOutcome] = useState<'unanswered' | 'right' | 'not-yet'>('unanswered');

  useEffect(() => {
    setScaffoldShown(false);
    setOutcome('unanswered');
  }, [mission.id]);

  const answer = useCallback(
    (correct: boolean) => {
      onAnswered(correct, scaffoldShown);
      setOutcome(correct ? 'right' : 'not-yet');
      announce(correct ? 'That fits.' : 'Not quite yet.');
    },
    [announce, onAnswered, scaffoldShown],
  );

  return (
    <Card padding="lg">
      <Stack gap="md">
        <Text variant="heading" as="h2">
          {mission.prompt}
        </Text>

        {block && <ModalityRouter block={block} />}

        {mission.options.length > 0 && outcome !== 'right' && (
          <Stack gap="sm" as="ul" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {mission.options.map((option) => (
              <li key={option}>
                <Button
                  block
                  variant="secondary"
                  onRaised
                  onClick={() => answer(option === block?.canonical_text)}
                >
                  {option}
                </Button>
              </li>
            ))}
          </Stack>
        )}

        {mission.options.length === 0 && outcome === 'unanswered' && (
          // Production missions are self-assessed: the learner says whether it
          // landed. Auto-scoring a spoken answer here would put ASR quality
          // between a learner and their own progress (ADR-0002).
          <Stack direction="horizontal" gap="sm">
            <Button variant="primary" onRaised onClick={() => answer(true)}>
              I said it
            </Button>
            <Button variant="secondary" onRaised onClick={() => answer(false)}>
              I need more practice
            </Button>
          </Stack>
        )}

        {outcome === 'not-yet' && (
          <Text variant="body" tone="attention">
            Not quite yet. The one that fits is: {block?.canonical_text}
          </Text>
        )}

        {/* Always available, on every mission, at every point. */}
        {!scaffoldShown && outcome === 'unanswered' && (
          <div>
            <Button variant="quiet" onClick={() => setScaffoldShown(true)}>
              Give me a hint
            </Button>
          </div>
        )}

        {scaffoldShown && (
          <Text variant="body" tone="secondary" measure>
            {mission.scaffold}
          </Text>
        )}

        {outcome !== 'unanswered' && (
          <div>
            <Button variant="primary" onRaised onClick={onContinue}>
              Next
            </Button>
          </div>
        )}
      </Stack>
    </Card>
  );
}
