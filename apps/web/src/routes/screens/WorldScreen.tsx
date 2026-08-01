/**
 * Route screen: one world.
 *
 * Exists so a world is linkable. That is the whole reason the router arrived:
 * a trainer assigning work to a learner needs to be able to send them a URL,
 * and "open the app, press Home, scroll to World 5" is not a link.
 *
 * The map component already renders one world expanded and the rest collapsed,
 * so this route is the same map opened at a different place rather than a
 * second implementation of the same list.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { useProfile } from '@/a11y/ProfileProvider';
import { resolveMotion } from '@/design-system/motion';
import { WorldMap, type Journey } from '@/game/WorldMap';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';
import { ErrorState, Skeleton, Stack } from '@/ui';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export default function WorldScreen() {
  const { worldId } = useParams<{ worldId: string }>();
  const { session } = useSession();
  const { profile } = useProfile();
  const navigate = useNavigate();

  const [journey, setJourney] = useState<Journey | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    setFailed(false);
    const response = await fetch(`${BASE_URL}/journey`, {
      headers: { Authorization: `Bearer ${session.token}` },
    }).catch(() => null);
    if (!response?.ok) {
      setFailed(true);
      return;
    }
    setJourney((await response.json()) as Journey);
  }, [session.token]);

  useEffect(() => {
    void load();
  }, [load]);

  const world = journey?.worlds.find((candidate) => candidate.world_id === worldId);

  return (
    <AppRoute title={world?.title ?? 'World'}>
      {failed && (
        <ErrorState
          title="We could not load this world"
          body="This is our problem, not yours. Nothing you have done has been lost."
          action={{ label: 'Try again', onClick: () => void load() }}
        />
      )}

      {!failed && !journey && (
        <Stack gap="md">
          <Skeleton label="Loading this world" height="3rem" />
          <Skeleton height="8rem" />
        </Stack>
      )}

      {journey && !world && (
        <ErrorState
          title="We could not find that world"
          body="The link may be out of date. Your map still has everything in it."
          action={{ label: 'Go to my map', onClick: () => navigate('/') }}
        />
      )}

      {journey && world && (
        <WorldMap
          journey={{ ...journey, worlds: [world] }}
          onOpenLevel={(levelId) => navigate(`/level/${encodeURIComponent(levelId)}`)}
          motion={resolveMotion(profile.presentation?.motion_reduced)}
          easyRead={profile.text_complexity === 'easy_read'}
          dark={document.documentElement.dataset['colourScheme'] === 'dark'}
        />
      )}
    </AppRoute>
  );
}
