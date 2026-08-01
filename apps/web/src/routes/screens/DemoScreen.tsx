/**
 * Route screen: How this works.
 *
 * Moved out of the learner navigation (Blueprint A8). One block rendered
 * through five channels with a persona switcher is a superb pitch artefact and
 * not a thing a learner needs in their nav.
 */
import { ChannelComparison } from '@/features/channel-comparison/ChannelComparison';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';

export default function DemoScreen() {
  const { blocks } = useSession();
  return (
    <AppRoute title="How this works">
      <ChannelComparison blocks={blocks} embedded />
    </AppRoute>
  );
}
