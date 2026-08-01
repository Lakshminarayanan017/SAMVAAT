/**
 * Route screen: Home.
 *
 * BEHIND A FLAG, ON PURPOSE
 * -------------------------
 * The world map as home is Blueprint G1, which belongs to Phase 2. Phase 1 is
 * meant to be behaviour-preserving, so the map only appears when `game_loop` is
 * on; with the flag off a learner gets the daily practice session they get
 * today. That is what makes the flag's off-state the *current* behaviour rather
 * than a broken one, which is the property the whole rollout plan rests on.
 *
 * When the map is on, the blueprint's structural change (§5.2) applies:
 * **"Continue" resolves to a specific level**, so there is no decision to make
 * before starting. Choosing stays available and is never required — the third
 * of Duolingo's four mechanics is that the next action is chosen for you, and
 * it is the one that removes friction before a session rather than during it.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useProfile } from '@/a11y/ProfileProvider';
import { resolveMotion } from '@/design-system/motion';
import { WorldMap, type Journey } from '@/game/WorldMap';
import { AppRoute } from '@/routes/AppRoute';
import { PracticeSession } from '@/features/practice/PracticeSession';
import { useFlag, useSession } from '@/services/SessionProvider';
import { Button, Card, ErrorState, Skeleton, Stack, Text } from '@/ui';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export default function HomeScreen() {
  const { session, blocks } = useSession();
  const { profile } = useProfile();
  const navigate = useNavigate();
  const gameLoop = useFlag('game_loop');

  const [journey, setJourney] = useState<Journey | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    if (!gameLoop) return;
    setFailed(false);
    const response = await fetch(`${BASE_URL}/journey`, {
      headers: { Authorization: `Bearer ${session.token}` },
    }).catch(() => null);

    if (!response?.ok) {
      setFailed(true);
      return;
    }
    setJourney((await response.json()) as Journey);
  }, [gameLoop, session.token]);

  useEffect(() => {
    void load();
  }, [load]);

  const openLevel = useCallback(
    (levelId: string) => navigate(`/level/${encodeURIComponent(levelId)}`),
    [navigate],
  );

  if (!gameLoop) {
    return (
      <AppRoute title="Home">
        <PracticeSession token={session.token} blocks={blocks} />
      </AppRoute>
    );
  }

  return (
    <AppRoute title="Home">
      {failed && (
        <ErrorState
          title="We could not load your map"
          body="This is our problem, not yours. Nothing you have done has been lost."
          action={{ label: 'Try again', onClick: () => void load() }}
        />
      )}

      {!failed && !journey && (
        <Stack gap="md">
          <Skeleton label="Loading your map" height="3rem" />
          <Skeleton height="8rem" />
          <Skeleton height="8rem" />
        </Stack>
      )}

      {journey && (
        <Stack gap="lg">
          {/* The largest thing on the screen, and it resolves to a specific
              level — no decision required before starting. */}
          {journey.next_level_id && (
            <Card elevation="raised" padding="lg">
              <Stack gap="sm">
                <Text variant="heading" as="h2">
                  {journey.headline}
                </Text>
                <div>
                  <Button
                    variant="primary"
                    onRaised
                    onClick={() => openLevel(journey.next_level_id as string)}
                  >
                    Continue
                  </Button>
                </div>
              </Stack>
            </Card>
          )}

          <WorldMap
            journey={journey}
            onOpenLevel={openLevel}
            motion={resolveMotion(profile.presentation?.motion_reduced)}
            easyRead={profile.text_complexity === 'easy_read'}
            dark={document.documentElement.dataset['colourScheme'] === 'dark'}
          />
        </Stack>
      )}
    </AppRoute>
  );
}
