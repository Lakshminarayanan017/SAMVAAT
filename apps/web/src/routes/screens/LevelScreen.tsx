/**
 * Route screen: one level. Chromeless.
 *
 * Two bodies, one frame. With `game_loop` on the learner gets the mission
 * runner; with it off they get the existing practice loop scoped to this
 * level's phrases. Both are real, working sessions — the flag's off-state is
 * the current behaviour rather than a degraded one, which is the property the
 * whole rollout plan rests on.
 *
 * The sensitive-chapter exit is here rather than in Phase 2 because it is not a
 * gameplay feature. A learner rehearsing disclosure is rehearsing something
 * that can cost them a job, and the way out has to exist the first time that
 * screen can be reached.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { PracticeSession } from '@/features/practice/PracticeSession';
import { useProfile } from '@/a11y/ProfileProvider';
import { resolveMotion } from '@/design-system/motion';
import { resolveCelebration } from '@/game/Celebration';
import { LevelRunner, type MissionPlan } from '@/game/LevelRunner';
import { AppRoute } from '@/routes/AppRoute';
import { useFlag, useSession } from '@/services/SessionProvider';
import { Button, Card, ErrorState, Skeleton, Stack, Text } from '@/ui';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

interface LevelPhrase {
  block_id: string;
  canonical_text: string;
  difficulty: number;
  is_new: boolean;
}

interface LevelDetail {
  level_id: string;
  title: string;
  world_id: string;
  world_title: string;
  missions: string[];
  effort: number;
  sensitive: boolean;
  phrases: LevelPhrase[];
}

export default function LevelScreen() {
  const { levelId } = useParams<{ levelId: string }>();
  const { session, blocks } = useSession();
  const { profile } = useProfile();
  const navigate = useNavigate();
  const gameLoop = useFlag('game_loop');

  const [level, setLevel] = useState<LevelDetail | null>(null);
  const [plan, setPlan] = useState<MissionPlan | null>(null);
  const [failed, setFailed] = useState<'network' | 'missing' | null>(null);

  const load = useCallback(async () => {
    if (!levelId) return;
    setFailed(null);

    const response = await fetch(`${BASE_URL}/journey/level/${encodeURIComponent(levelId)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    }).catch(() => null);

    if (response?.status === 404) {
      setFailed('missing');
      return;
    }
    if (!response?.ok) {
      setFailed('network');
      return;
    }
    setLevel((await response.json()) as LevelDetail);

    if (gameLoop) {
      const missions = await fetch(
        `${BASE_URL}/missions/level/${encodeURIComponent(levelId)}`,
        { headers: { Authorization: `Bearer ${session.token}` } },
      ).catch(() => null);

      // Missions failing to load is not fatal: the level still runs through the
      // practice loop below. A learner who came here to practise should not be
      // sent away because one of two requests failed.
      if (missions?.ok) setPlan((await missions.json()) as MissionPlan);
    }
  }, [gameLoop, levelId, session.token]);

  useEffect(() => {
    void load();
  }, [load]);

  // Only this level's phrases reach the practice loop, so a level link opens a
  // level rather than "the daily session, entered from a level".
  const levelBlocks = level
    ? blocks.filter((block) => level.phrases.some((phrase) => phrase.block_id === block.id))
    : [];

  return (
    <AppRoute title={level ? level.title : 'Level'} chromeless>
      <Stack
        gap="md"
        style={{ padding: 'var(--space-md, 1rem)', maxInlineSize: '48rem', marginInline: 'auto' }}
      >
        {/* Chromeless means no navigation, not no way back. A learner who
            cannot leave a screen is trapped in it. */}
        <div>
          <Button variant="quiet" onClick={() => navigate('/')}>
            Back to my map
          </Button>
        </div>

        {failed === 'network' && (
          <ErrorState
            title="We could not load this level"
            body="This is our problem, not yours. Nothing you have done has been lost."
            action={{ label: 'Try again', onClick: () => void load() }}
          />
        )}

        {failed === 'missing' && (
          <ErrorState
            title="We could not find that level"
            body="The link may be out of date. Your map still has everything in it."
            action={{ label: 'Go to my map', onClick: () => navigate('/') }}
          />
        )}

        {!failed && !level && <Skeleton label="Loading this level" height="6rem" />}

        {level && (
          <>
            <Stack gap="xs">
              <Text variant="caption" tone="secondary">
                {level.world_title}
              </Text>
              <Text variant="title" as="h1">
                {level.title}
              </Text>
            </Stack>

            {level.sensitive && <SensitiveNotice onLeave={() => navigate('/')} />}

            {plan ? (
              <LevelRunner
                plan={plan}
                blocks={levelBlocks}
                token={session.token}
                celebrationLevel={resolveCelebration(
                  undefined,
                  resolveMotion(profile.presentation?.motion_reduced),
                )}
                onLeave={() => navigate('/')}
                onNext={() => navigate('/')}
              />
            ) : (
              <PracticeSession token={session.token} blocks={levelBlocks} />
            )}
          </>
        )}
      </Stack>
    </AppRoute>
  );
}

/**
 * The exit from a sensitive chapter.
 *
 * Shown *before* the practice starts, not after. A learner about to rehearse
 * telling an employer they are disabled is about to rehearse something with
 * real consequences, and being told the way out only once they are upset is
 * being told too late.
 *
 * Not a modal: a dialog demanding dismissal before a difficult topic is one
 * more obstacle in front of the difficult topic. This sits in the flow and
 * stays there.
 */
function SensitiveNotice({ onLeave }: { onLeave: () => void }) {
  return (
    <Card elevation="raised" padding="md">
      <Stack gap="sm">
        <Text variant="heading" as="h2">
          This one can be hard
        </Text>
        <Text variant="body" measure>
          You can stop at any time. Nothing is saved as a failure, and nobody is told you left.
        </Text>
        <div>
          <Button variant="secondary" onRaised onClick={onLeave}>
            Leave this for now
          </Button>
        </div>
      </Stack>
    </Card>
  );
}
