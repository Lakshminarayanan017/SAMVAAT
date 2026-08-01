/**
 * Route screen: Understand a situation.
 *
 * Thin by design. The blueprint is a re-skin plus an information-architecture
 * change, not a functional rewrite — the feature keeps its logic and its tests,
 * and this wrapper supplies the accessible route contract and the session.
 */
import { StoryChooser } from '@/features/stories/StoryChooser';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';

export default function StoriesScreen() {
  const { session } = useSession();
  return (
    <AppRoute title="Understand a situation">
      <StoryChooser token={session.token} />
    </AppRoute>
  );
}
