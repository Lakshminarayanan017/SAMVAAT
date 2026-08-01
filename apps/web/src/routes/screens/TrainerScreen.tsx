/**
 * Route screen: My learners.
 *
 * Role-gated in the navigation only. The API refuses this data on the token's
 * own claim, so reaching the route directly shows an error rather than data —
 * which is the correct place for the boundary to live.
 */
import { TrainerDashboard } from '@/features/trainer/TrainerDashboard';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';

export default function TrainerScreen() {
  const { session } = useSession();
  return (
    <AppRoute title="My learners">
      <TrainerDashboard token={session.token} />
    </AppRoute>
  );
}
